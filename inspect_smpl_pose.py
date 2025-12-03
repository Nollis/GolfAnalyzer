import json
import argparse
import urllib.request
import sys
import math
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Inspect SMPL pose data structure.")
    parser.add_argument("input", nargs="?", help="Path to JSON file or '-' for stdin")
    parser.add_argument("--url", help="URL to fetch JSON from")
    return parser.parse_args()

def load_data(args):
    if args.url:
        print(f"Fetching from URL: {args.url}...", file=sys.stderr)
        with urllib.request.urlopen(args.url) as f:
            return json.loads(f.read().decode())
    elif args.input == "-":
        print("Reading from STDIN...", file=sys.stderr)
        return json.load(sys.stdin)
    elif args.input:
        print(f"Reading from file: {args.input}...", file=sys.stderr)
        with open(args.input, "r") as f:
            return json.load(f)
    else:
        # Try reading from stdin if no args provided and not interactive
        if not sys.stdin.isatty():
            print("Reading from STDIN (implicit)...", file=sys.stderr)
            return json.load(sys.stdin)
        print("Error: No input provided. Use file path, --url, or pipe data via stdin.", file=sys.stderr)
        sys.exit(1)

def mat3_to_quat(m):
    """
    Convert 3x3 rotation matrix to quaternion [x, y, z, w].
    m is a list of 3 lists of 3 numbers.
    """
    m00, m01, m02 = m[0][0], m[0][1], m[0][2]
    m10, m11, m12 = m[1][0], m[1][1], m[1][2]
    m20, m21, m22 = m[2][0], m[2][1], m[2][2]
    
    tr = m00 + m11 + m22
    
    if tr > 0:
        S = math.sqrt(tr + 1.0) * 2
        w = 0.25 * S
        x = (m21 - m12) / S
        y = (m02 - m20) / S
        z = (m10 - m01) / S
    elif (m00 > m11) and (m00 > m22):
        S = math.sqrt(1.0 + m00 - m11 - m22) * 2
        w = (m21 - m12) / S
        x = 0.25 * S
        y = (m01 + m10) / S
        z = (m02 + m20) / S
    elif (m11 > m22):
        S = math.sqrt(1.0 + m11 - m00 - m22) * 2
        w = (m02 - m20) / S
        x = (m01 + m10) / S
        y = 0.25 * S
        z = (m12 + m21) / S
    else:
        S = math.sqrt(1.0 + m22 - m00 - m11) * 2
        w = (m10 - m01) / S
        x = (m02 + m20) / S
        y = (m12 + m21) / S
        z = 0.25 * S
    
    return [x, y, z, w]

def analyze_entry(entry):
    """
    Analyze a single joint entry.
    Returns: (type_str, shape_list, sample_value_or_quat)
    """
    if isinstance(entry, list):
        # Check depth
        if len(entry) == 0:
            return "empty", [0], entry
        
        if isinstance(entry[0], list):
            # Matrix?
            rows = len(entry)
            cols = len(entry[0])
            shape = [rows, cols]
            if rows == 3 and cols == 3:
                # 3x3 Matrix
                quat = mat3_to_quat(entry)
                return "matrix_3x3", shape, quat
            else:
                return "matrix_other", shape, entry
        elif isinstance(entry[0], (int, float)):
            # Vector/Quat
            shape = [len(entry)]
            if len(entry) == 4:
                return "quaternion", shape, entry
            elif len(entry) == 3:
                return "vector_3", shape, entry
            elif len(entry) == 9:
                # Flattened 3x3?
                return "matrix_flat", shape, entry
            else:
                return "vector_other", shape, entry
    
    return "unknown", [], entry

def find_pose_data(data):
    """
    Heuristic to find the actual pose data within a larger JSON structure.
    """
    # If list of frames, take first frame
    if isinstance(data, list):
        if len(data) > 0:
            print(f"Input is a list of {len(data)} items. Analyzing first item.", file=sys.stderr)
            return find_pose_data(data[0])
        else:
            return None, "empty_list"

    if isinstance(data, dict):
        # Check for common keys
        keys = data.keys()
        if "smpl_pose" in keys:
            print("Found 'smpl_pose' key.", file=sys.stderr)
            return data["smpl_pose"], "dict_with_smpl_pose"
        if "pose" in keys:
            print("Found 'pose' key.", file=sys.stderr)
            return data["pose"], "dict_with_pose"
        if "body_pose" in keys:
            print("Found 'body_pose' key.", file=sys.stderr)
            return data["body_pose"], "dict_with_body_pose"
        
        # Maybe the dict IS the pose (name -> value)
        # Check if values look like arrays
        first_val = next(iter(data.values()))
        if isinstance(first_val, list):
             print("Input appears to be a name->value map.", file=sys.stderr)
             return data, "dict_map"
    
    # Fallback: assume data itself is the pose (e.g. list of matrices)
    return data, "raw"

def main():
    args = parse_args()
    raw_data = load_data(args)
    
    pose_data, input_type = find_pose_data(raw_data)
    
    if pose_data is None:
        print("Could not find valid pose data.")
        sys.exit(1)

    print("\n=== INPUT TYPE ===")
    print(f"Detected structure: {input_type}")
    if isinstance(pose_data, list):
        print(f"Type: Array (List)")
        print(f"Length: {len(pose_data)}")
    elif isinstance(pose_data, dict):
        print(f"Type: Dict (Map)")
        print(f"Keys: {len(pose_data)}")
    else:
        print(f"Type: {type(pose_data)}")

    print("\n=== JOINTS ===")
    
    summary = {
        "joint_names": [],
        "joint_types": {},
        "joint_shapes": {},
        "joint_values": {}
    }

    if isinstance(pose_data, list):
        # Array based
        print(f"JOINT_ORDER = [indices 0..{len(pose_data)-1}] (Names missing in data)")
        print("-" * 40)
        for i, entry in enumerate(pose_data):
            name = f"joint_{i}"
            j_type, j_shape, j_val = analyze_entry(entry)
            
            summary["joint_names"].append(name)
            summary["joint_types"][name] = j_type
            summary["joint_shapes"][name] = j_shape
            summary["joint_values"][name] = j_val

            val_str = str(j_val)
            if j_type == "matrix_3x3":
                val_str = f"Quat: {j_val} (converted from 3x3)"
            
            print(f"Index {i:02d}: {j_type:12s} shape={j_shape} | {val_str}")
            
    elif isinstance(pose_data, dict):
        # Dict based
        names = list(pose_data.keys())
        print(f"Joint Names Found: {names}")
        print("-" * 40)
        
        for name in names:
            entry = pose_data[name]
            j_type, j_shape, j_val = analyze_entry(entry)
            
            summary["joint_names"].append(name)
            summary["joint_types"][name] = j_type
            summary["joint_shapes"][name] = j_shape
            summary["joint_values"][name] = j_val
            
            val_str = str(j_val)
            if j_type == "matrix_3x3":
                val_str = f"Quat: {j_val} (converted from 3x3)"
                
            print(f"Name '{name}': {j_type:12s} shape={j_shape} | {val_str}")

    print("\n=== SUMMARY ===")
    print(f"Total Joints: {len(summary['joint_names'])}")
    
    # Check consistency
    types = set(summary["joint_types"].values())
    print(f"Data Types: {types}")
    
    # Save summary
    out_file = "smpl_pose_summary.json"
    with open(out_file, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary saved to {out_file}")

if __name__ == "__main__":
    main()
