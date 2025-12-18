
import os
from pathlib import Path

content = """---
description: Overview of the GolfAnalyzer project structure and key files
globs: **/*
alwaysApply: true
---
# Project Structure

This document outlines the directory structure and key components of the GolfAnalyzer application.

## Root Directory
- `app/`: FastAPI backend application
- `frontend/`: SvelteKit frontend application
- `pose/`: Core pose estimation and analysis logic
- `hybrik_repo/`: HybrIK 3D pose estimation library (submodule)
- `videos/`: Storage for uploaded videos, processed outputs, and keyframe images
- `golf_analyzer.db`: SQLite database for session data
- `requirements.txt`: Python dependencies

## Backend (`app/`)
The backend is built with FastAPI and handles API requests, database interactions, and orchestrates the analysis pipeline.

- `main.py`: Application entry point and startup logic
- `api/`: API route definitions
    - `routes_analyze.py`: Main analysis endpoints (upload, process, metrics)
    - `routes_auth.py`: Authentication endpoints
    - `routes_sessions.py`: Session management
- `core/`: Core configuration
    - `config.py`: Settings and environment variables
    - `security.py`: JWT authentication logic
- `models/`: SQLAlchemy database models
    - `db.py`: Database connection and model definitions (`User`, `SwingSession`, `SwingMetric`)
- `schemas.py`: Pydantic models for API request/response validation
- `services/`: Business logic services
    - `video_storage.py`: Video file management
    - `feedback.py`: AI feedback generation
    - `skill_assessment.py`: User skill tracking

## Frontend (`frontend/`)
The frontend is a SvelteKit application using TailwindCSS for styling.

- `src/routes/`: Application routes (pages)
    - `+page.svelte`: Landing/Upload page
    - `dashboard/`: User dashboard
    - `sessions/[id]/`: Analysis results page
    - `sessions/[id]/pose-editor/`: 3D pose correction tool
- `src/lib/`: Shared components and utilities
    - `components/`: Reusable UI components (`SkeletonViewer`, `VideoPlayer`, `FeedbackPanel`)
    - `api.ts`: Backend API client
    - `stores.ts`: Global state management
    - `smplBotLoader.ts`: 3D SMPL character loading logic
    - `smplPoseApplier.ts`: Logic for applying poses to the 3D character

## Pose Analysis (`pose/`)
This module contains the core computer vision and biomechanics logic.

- `legacy_mediapipe.py`: (Legacy) MediaPipe wrapper; the app mainly uses the MediaPipe *landmark format* without requiring the `mediapipe` package
- `types.py`: Shared pose data structures (FramePose, Point3D)
- `smpl_extractor.py`: HybrIK integration for 3D SMPL pose extraction
- `metrics.py`: Calculation of golf swing metrics (tempo, rotation, angles)
- `kinematics.py`: Forward Kinematics engine for SMPL skeleton
- `swing_detection.py`: Logic to detect swing phases (Address, Top, Impact, Finish)
- `presets/`: Pose presets and blending logic
    - `address_pose.json`: Reference address pose
    - `address_blend.py`: Logic to blend detected pose with reference address pose

## Key Workflows
1.  **Upload & Analysis**: `app/api/routes_analyze.py` -> `analyze_swing`
    -   Extracts poses (`pose/smpl_extractor.py`)
    -   Blends address pose (`pose/presets/address_blend.py`)
    -   Updates joints via FK (`pose/kinematics.py`)
    -   Detects phases (`pose/swing_detection.py`)
    -   Computes metrics (`pose/metrics.py`)
    -   Generates feedback (`app/services/feedback.py`)
    -   Saves to DB and `videos/`

2.  **Pose Correction**: `frontend/src/routes/sessions/[id]/pose-editor/`
    -   User adjusts joints in 3D
    -   Saves to `videos/{id}_poses_corrected.json`
    -   Backend reloads corrected poses for visualization
"""

path = Path(".agent/rules/project-structure.md")
try:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Created {path.absolute()}")
except Exception as e:
    print(f"Error creating file: {e}")
