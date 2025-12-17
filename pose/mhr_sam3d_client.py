"""
SAM-3D MHR Client

Subprocess client to call the external sam-3d-body repo for MHR-70 joint extraction.
Supports both single-image and batch processing modes.
"""

import subprocess
import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

# Paths to the SAM-3D repo and Python environment
SAM3D_PYTHON = Path(r"C:\Projekt\sam-3d-body\.venv\Scripts\python.exe")
SAM3D_REPO = Path(r"C:\Projekt\sam-3d-body")
SAM3D_SCRIPT = SAM3D_REPO / "sam3d_export_joints.py"
SAM3D_BATCH_SCRIPT = SAM3D_REPO / "sam3d_export_batch.py"

# Increased timeouts for model loading
SINGLE_IMAGE_TIMEOUT = 180  # 3 minutes for single image (includes model load)
BATCH_TIMEOUT = 300  # 5 minutes for batch (model loads once)


def run_sam3d_on_image(image_path: Path, output_dir: Path) -> Dict[str, Optional[np.ndarray]]:
    """
    Call the external sam-3d-body repo on a single image.
    
    Args:
        image_path: Path to the input image (PNG or JPG)
        output_dir: Directory to store output files
        
    Returns:
        Dictionary with:
        - 'joints3d': np.ndarray of shape (70, 3) or None if failed
        - 'joints2d': np.ndarray of shape (70, 2) or None if failed
        - 'error': Optional error message string
    """
    result: Dict[str, Optional[np.ndarray]] = {
        "joints3d": None,
        "joints2d": None,
        "error": None
    }
    
    # Validate inputs
    if not image_path.exists():
        result["error"] = f"Input image not found: {image_path}"
        logger.error(result["error"])
        return result
    
    if not SAM3D_PYTHON.exists():
        result["error"] = f"SAM3D Python not found: {SAM3D_PYTHON}"
        logger.error(result["error"])
        return result
        
    if not SAM3D_SCRIPT.exists():
        result["error"] = f"SAM3D script not found: {SAM3D_SCRIPT}"
        logger.error(result["error"])
        return result
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = [
        str(SAM3D_PYTHON),
        str(SAM3D_SCRIPT),
        "--image_path", str(image_path.absolute()),
        "--output_dir", str(output_dir.absolute())
    ]
    
    logger.info(f"[MHR] Running SAM-3D: {' '.join(cmd)}")
    
    try:
        # Run subprocess with increased timeout
        proc = subprocess.run(
            cmd,
            cwd=str(SAM3D_REPO),
            capture_output=True,
            text=True,
            timeout=SINGLE_IMAGE_TIMEOUT
        )
        
        if proc.returncode != 0:
            result["error"] = f"SAM3D subprocess failed (code {proc.returncode}): {proc.stderr[:500]}"
            logger.error(result["error"])
            return result
        
        # Load outputs
        joints3d_path = output_dir / "joints_mhr70.npy"
        joints2d_path = output_dir / "joints_mhr70_2d.npy"
        
        if joints3d_path.exists():
            result["joints3d"] = np.load(str(joints3d_path))
            logger.info(f"[MHR] Loaded 3D joints: {result['joints3d'].shape}")
        else:
            logger.warning(f"[MHR] 3D joints file not found: {joints3d_path}")
        
        if joints2d_path.exists():
            result["joints2d"] = np.load(str(joints2d_path))
            logger.info(f"[MHR] Loaded 2D joints: {result['joints2d'].shape}")
        else:
            logger.warning(f"[MHR] 2D joints file not found: {joints2d_path}")
        
        return result
        
    except subprocess.TimeoutExpired:
        result["error"] = f"SAM3D subprocess timed out after {SINGLE_IMAGE_TIMEOUT} seconds"
        logger.error(result["error"])
        return result
    except Exception as e:
        result["error"] = f"SAM3D subprocess exception: {str(e)}"
        logger.error(result["error"])
        return result


def run_sam3d_batch(
    image_dict: Dict[str, Path],
    output_dir: Path
) -> Dict[str, Dict[str, Any]]:
    """
    Call SAM-3D on multiple images in a single subprocess (batch mode).
    
    This is much more efficient than calling run_sam3d_on_image multiple times
    because the model only loads once.
    
    Args:
        image_dict: Dictionary mapping phase names to image paths
                   e.g., {"address": Path("addr.png"), "top": Path("top.png"), ...}
        output_dir: Base directory for outputs
        
    Returns:
        Dictionary with results for each phase:
        {
            "address": {"joints3d": np.ndarray, "joints2d": np.ndarray, "error": str|None},
            "top": {...},
            ...
        }
    """
    results: Dict[str, Dict[str, Any]] = {}
    
    # Initialize all results with None
    for phase_name in image_dict:
        results[phase_name] = {
            "joints3d": None,
            "joints2d": None,
            "error": None
        }
    
    # Validate batch script exists
    if not SAM3D_BATCH_SCRIPT.exists():
        error_msg = f"SAM3D batch script not found: {SAM3D_BATCH_SCRIPT}"
        logger.error(error_msg)
        for phase_name in results:
            results[phase_name]["error"] = error_msg
        return results
    
    if not SAM3D_PYTHON.exists():
        error_msg = f"SAM3D Python not found: {SAM3D_PYTHON}"
        logger.error(error_msg)
        for phase_name in results:
            results[phase_name]["error"] = error_msg
        return results
    
    # Create output directory
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write image list JSON
    image_list_path = output_dir / "image_list.json"
    image_list_data = {name: str(path.absolute()) for name, path in image_dict.items()}
    
    with open(image_list_path, "w") as f:
        json.dump(image_list_data, f)
    
    # Build command
    cmd = [
        str(SAM3D_PYTHON),
        str(SAM3D_BATCH_SCRIPT),
        "--image_list", str(image_list_path),
        "--output_dir", str(output_dir.absolute())
    ]
    
    logger.info(f"[MHR] Running SAM-3D batch: processing {len(image_dict)} images")
    
    # Create log files in output directory (not temp) to avoid cleanup issues
    stdout_log = output_dir / "sam3d_stdout.log"
    stderr_log = output_dir / "sam3d_stderr.log"
    
    # Build command as string for shell execution
    # Use -u for unbuffered Python output to avoid subprocess hangs
    cmd_str = f'"{SAM3D_PYTHON}" -u "{SAM3D_BATCH_SCRIPT}" --image_list "{image_list_path}" --output_dir "{output_dir.absolute()}"'
    logger.info(f"[MHR] Command: {cmd_str}")
    
    proc = None
    stdout_f = None
    stderr_f = None
    
    try:
        # Open log files
        stdout_f = open(stdout_log, "w")
        stderr_f = open(stderr_log, "w")
        
        # Use Popen for better control over the process
        import os
        env = os.environ.copy()
        
        # Use synchronous CUDA calls to avoid race conditions in subprocess
        # This may be slightly slower but more stable
        env["CUDA_LAUNCH_BLOCKING"] = "1"
        
        proc = subprocess.Popen(
            cmd_str,
            shell=True,  # Required for string command on Windows
            cwd=str(SAM3D_REPO),
            stdout=stdout_f,
            stderr=stderr_f,
            env=env,
        )
        
        # Wait with timeout
        try:
            proc.wait(timeout=BATCH_TIMEOUT)
        except subprocess.TimeoutExpired:
            logger.error(f"[MHR] SAM3D timed out, killing process...")
            proc.kill()
            proc.wait(timeout=5)  # Wait for kill to complete
            
            # Close files before reading
            stdout_f.close()
            stderr_f.close()
            stdout_f = None
            stderr_f = None
            
            # Read stderr
            stderr_content = ""
            if stderr_log.exists():
                stderr_content = stderr_log.read_text()[:500]
                if stderr_content:
                    logger.error(f"[MHR] Last stderr: {stderr_content}")
            
            for phase_name in results:
                results[phase_name]["error"] = f"SAM3D batch subprocess timed out after {BATCH_TIMEOUT} seconds"
            return results
        
        # Close files before reading
        stdout_f.close()
        stderr_f.close()
        stdout_f = None
        stderr_f = None
        
        # Read stderr for error reporting
        stderr_content = ""
        if stderr_log.exists():
            stderr_content = stderr_log.read_text()[:1000]
        
        # Try to read results
        batch_results_path = output_dir / "batch_results.json"
        
        if batch_results_path.exists():
            with open(batch_results_path, "r") as f:
                batch_results = json.load(f)
        else:
            batch_results = {}
        
        # Load numpy files for each phase
        for phase_name in image_dict:
            phase_output_dir = output_dir / phase_name
            joints3d_path = phase_output_dir / "joints_mhr70.npy"
            joints2d_path = phase_output_dir / "joints_mhr70_2d.npy"
            
            if joints3d_path.exists():
                results[phase_name]["joints3d"] = np.load(str(joints3d_path))
                logger.info(f"[MHR] ✓ {phase_name}: joints3d shape {results[phase_name]['joints3d'].shape}")
            
            if joints2d_path.exists():
                results[phase_name]["joints2d"] = np.load(str(joints2d_path))
            
            # Check for errors in batch results
            if phase_name in batch_results:
                if "error" in batch_results[phase_name]:
                    results[phase_name]["error"] = batch_results[phase_name]["error"]
                    logger.warning(f"[MHR] ✗ {phase_name}: {results[phase_name]['error']}")
        
        if proc.returncode != 0:
            logger.warning(f"[MHR] Batch process exited with code {proc.returncode}")
            if stderr_content:
                logger.warning(f"[MHR] stderr: {stderr_content[:500]}")
        
        return results
        
    except Exception as e:
        error_msg = f"SAM3D batch subprocess exception: {str(e)}"
        logger.error(error_msg)
        for phase_name in results:
            results[phase_name]["error"] = error_msg
        return results
    
    finally:
        # Ensure files are closed
        if stdout_f and not stdout_f.closed:
            stdout_f.close()
        if stderr_f and not stderr_f.closed:
            stderr_f.close()
        # Ensure process is terminated
        if proc and proc.poll() is None:
            proc.kill()


def is_sam3d_available() -> bool:
    """Check if SAM-3D is available (paths exist)."""
    return SAM3D_PYTHON.exists() and (SAM3D_SCRIPT.exists() or SAM3D_BATCH_SCRIPT.exists())


def is_batch_available() -> bool:
    """Check if batch processing script is available."""
    return SAM3D_PYTHON.exists() and SAM3D_BATCH_SCRIPT.exists()
