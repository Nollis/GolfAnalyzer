# GolfAnalyzer Setup Guide

## Prerequisites

- **Python 3.9+** (Python 3.10 recommended)
- **Node.js 18+** and npm
- **OpenAI API Key** (optional, for AI feedback - app works without it)
- **GPU with CUDA** (Recommended for SAM-3D performance)

## External dependency: `sam-3d-body` (outside this repo)

The 3D MHR pipeline calls an **external** repository via subprocess:
- Expected sibling checkout: `..\sam-3d-body\` (next to this repo), with its own Python environment.
- The integration is implemented in `pose/mhr_sam3d_client.py`.

### Configure via environment variables (recommended)

Add to your `.env` (paths are examples for Windows):

```env
# Path to the external sam-3d-body repo (folder outside this project)
SAM3D_REPO=C:\Projekt\sam-3d-body

# Path to the Python executable inside sam-3d-body's venv
SAM3D_PYTHON=C:\Projekt\sam-3d-body\.venv\Scripts\python.exe
```

If `SAM3D_REPO`/`SAM3D_PYTHON` are not set, the app will try a best-effort default
(a sibling `sam-3d-body/` folder next to this repo).

## Quick Start

### 1. Backend Setup

#### Step 1: Activate Virtual Environment
```bash
# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

#### Step 2: Install Python Dependencies
```bash
pip install -r requirements.txt
```

**Note**: The app uses YOLO + SAM-3D. A CUDA-capable GPU is highly recommended.

#### Step 3: Set Up Environment Variables

Create a `.env` file in the root directory (`C:\Projekt\GolfAnalyzer\.env`):

```env
# Required for JWT authentication (use a strong random string in production)
SECRET_KEY=your-secret-key-change-in-production-min-32-chars

# Optional: OpenAI API key for AI feedback generation
# If not provided, feedback will still work but may be less detailed
OPENAI_API_KEY=sk-your-key-here

# Performance options:
# Skip AI feedback generation (faster analysis)
DISABLE_FEEDBACK=false


```

**Important**: The `SECRET_KEY` is used for JWT token signing. Use a strong random string in production.

#### Step 4: Settings

Configure your `.env` as needed. The app defaults to using YOLO + SAM-3D.

#### Step 5: Initialize Database and Seed Data

The database will be created automatically on first run. To seed drill data:

```bash
python app/core/seed_drills.py
```

#### Step 6: (Optional) Create Admin User

```bash
python create_admin.py
```

#### Step 7: Run Backend Server

```bash
uvicorn app.main:app --reload
```

The API will be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/

---

### 2. Frontend Setup

#### Step 1: Navigate to Frontend Directory
```bash
cd frontend
```

#### Step 2: Install Dependencies
```bash
npm install
```

#### Step 3: Run Development Server
```bash
npm run dev
```

The frontend will be available at:
- **UI**: http://localhost:5173

---

## Running the Application

### Start Both Servers

**Terminal 1 - Backend:**
```bash
# Activate venv first
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac

# Run backend
uvicorn app.main:app --reload
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

### Access the Application

1. Open your browser to: **http://localhost:5173**
2. Register a new account or log in
3. Upload a golf swing video to get started!

---

## Verification Checklist

Before running, verify:

- [ ] Python virtual environment is activated
- [ ] All Python dependencies installed (`pip list` shows fastapi, uvicorn, etc.)
- [ ] `.env` file exists with `SECRET_KEY` set
- [ ] Node.js dependencies installed (`cd frontend && npm list` shows packages)
- [ ] Database file will be created automatically (`golf_analyzer.db`)

---

## Troubleshooting

### Backend Issues

**Port 8000 already in use:**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001
```

**Import errors:**
- Make sure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**HybrIK not working:**
- Check if PyTorch is installed: `python -c "import torch; print(torch.__version__)"`
- App will fall back to the standard 2D landmark pipeline if HybrIK/SMPL features are unavailable

### Frontend Issues

**Port 5173 already in use:**
- Vite will automatically use the next available port
- Check the terminal output for the actual port

**Build errors:**
- Clear node_modules and reinstall: `rm -rf node_modules && npm install`
- Check Node.js version: `node --version` (should be 18+)

### Database Issues

**Database locked:**
- Make sure only one instance of the app is running
- Close any database viewers (DB Browser, etc.)

---

## Production Deployment

For production:

1. **Change SECRET_KEY** to a strong random string (32+ characters)
2. **Set proper CORS origins** in `app/main.py` (replace `["*"]` with your domain)
3. **Use environment variables** for all secrets
4. **Build frontend**: `cd frontend && npm run build`
5. **Use a production ASGI server**: `gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker`
6. **Set up proper database** (PostgreSQL recommended for production)
7. **Configure static file serving** for uploaded videos

---

## Features Available

✅ **Architecture:**
- **2D Pose**: YOLOv8 (Fast, robust phase detection)
- **3D Pose**: SAM-3D MHR (High fidelity 3D joint reconstruction)

---

## Next Steps

1. **Register/Login**: Create an account at http://localhost:5173/register
2. **Upload Video**: Upload a golf swing video (MP4 format recommended)
3. **View Analysis**: See detailed metrics, scores, and AI feedback
4. **Track Progress**: Use the Dashboard to see your improvement over time

Enjoy analyzing your golf swings! 🏌️‍♂️



