from dotenv import load_dotenv
load_dotenv(override=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import routes_analyze, routes_auth, routes_analytics, routes_drills, routes_admin, routes_jobs, routes_storage
from app.core.database import Base, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Golf Swing Analyzer API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(routes_analyze.router, prefix="/api/v1", tags=["analysis"])
app.include_router(routes_jobs.router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(routes_analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(routes_drills.router, prefix="/api/v1/drills", tags=["drills"])
app.include_router(routes_admin.router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(routes_storage.router, prefix="/api/v1", tags=["storage"])


@app.on_event("startup")
async def startup_event():
    """Initialize database and start background worker."""
    logger.info("🚀 Starting Golf Swing Analyzer API...")
    
    # Create database tables (including new AnalysisJob table)
    from app.models.job import AnalysisJob  # Import to register model
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database tables created")
    
    # Initialize job queue
    from app.services.job_queue import init_job_queue
    init_job_queue()
    logger.info("✅ Job queue initialized")
    
    # Start background worker
    from app.workers.analysis_worker import start_worker
    start_worker()
    logger.info("✅ Background worker started")
    
    logger.info("🎯 API ready to accept requests!")


@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully stop background worker."""
    logger.info("Shutting down...")
    
    from app.workers.analysis_worker import stop_worker
    stop_worker()
    
    logger.info("Shutdown complete")


@app.get("/")
def read_root():
    return {"message": "Golf Swing Analyzer API is running"}


@app.get("/health")
def health_check():
    """Health check endpoint with system status."""
    from app.services.job_queue import get_queue
    from app.workers.analysis_worker import get_worker
    
    queue = get_queue()
    worker = get_worker()
    
    # Check HybrIK status
    hybrik_status = "unavailable"
    try:
        from pose.smpl_extractor import HYBRIK_AVAILABLE, get_hybrik_extractor
        if HYBRIK_AVAILABLE:
            extractor = get_hybrik_extractor()
            if extractor and extractor._loaded:
                hybrik_status = "loaded"
            else:
                hybrik_status = "available"
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "worker_running": worker.is_running(),
        "queue_size": queue.size(),
        "hybrik": hybrik_status,
        "pose_estimation": "3D (HybrIK)" if hybrik_status == "loaded" else "2D (MediaPipe landmark-format)"
    }


@app.get("/debug/pose-test")
def debug_pose_test(pose: str = "left_elbow"):
    """
    Deterministic SMPL test poses for frontend retargeting.
    - pose=identity: all joints are identity (A-pose).
    - pose=left_elbow: SMPL index 18 (l_elbow) rotated 45 deg around +X.
    """
    import math

    def make_identity():
        return [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]

    smpl_pose_identity = [make_identity() for _ in range(24)]
    pose_name = "identity"
    smpl_pose = [make_identity() for _ in range(24)]

    if pose != "identity":
        pose_name = "left_elbow"
        theta = math.radians(45)
        c = math.cos(theta)
        s = math.sin(theta)
        rot_x_45 = [
            [1.0, 0.0, 0.0],
            [0.0, c, -s],
            [0.0, s, c]
        ]
        # SMPL index 18 is l_elbow in pose/smpl_extractor.py
        smpl_pose = [make_identity() for _ in range(24)]
        smpl_pose[18] = rot_x_45

    # Dummy landmarks to keep consumer code happy; values just define a loose bbox.
    landmarks = []
    for i in range(33):
        landmarks.append({"x": 0.5, "y": 0.5, "z": 0.0, "visibility": 1.0})

    landmarks[23] = {"x": 0.4, "y": 0.6, "z": 0.0, "visibility": 1.0} # L Hip
    landmarks[24] = {"x": 0.6, "y": 0.6, "z": 0.0, "visibility": 1.0} # R Hip
    landmarks[11] = {"x": 0.4, "y": 0.2, "z": 0.0, "visibility": 1.0} # L Shoulder
    landmarks[12] = {"x": 0.6, "y": 0.2, "z": 0.0, "visibility": 1.0} # R Shoulder

    return {
        "pose_name": pose_name,
        "smpl_pose": smpl_pose_identity if pose_name == "identity" else smpl_pose,
        "landmarks": landmarks
    }
