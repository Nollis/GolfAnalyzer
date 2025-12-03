# GolfAnalyzer Setup Guide

## Prerequisites

- **Python 3.9+** (Python 3.10 recommended)
- **Node.js 18+** and npm
- **OpenAI API Key** (optional, for AI feedback - app works without it)
- **GPU with CUDA** (optional, for HybrIK 3D pose estimation - falls back to MediaPipe if unavailable)

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

**Note**: If you have a GPU and want to use HybrIK for better accuracy:
- PyTorch will be installed automatically
- Make sure you have CUDA installed if using GPU
- The app will automatically detect and use HybrIK if available, otherwise falls back to MediaPipe

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

# Use YOLO instead of HybrIK (faster but less accurate)
DISABLE_HYBRIK=false

# Process every Nth frame with HybrIK (default: 2 for speed)
# Set to 1 for all frames (slower but more accurate)
HYBRIK_FRAME_STEP=2
```

**Important**: The `SECRET_KEY` is used for JWT token signing. Use a strong random string in production.

#### Step 4: (Optional) Copy HybrIK Repository

For improved 3D pose estimation accuracy, copy the HybrIK repository:

```bash
# Copy from golf-swing-analyzer to GolfAnalyzer
# Copy the entire folder:
# golf-swing-analyzer/backend/hybrik_repo -> GolfAnalyzer/hybrik_repo
```

The `hybrik_repo` folder should contain:
- `configs/` - Configuration files
- `pretrained_models/hybrik_hrnet.pth` - Pre-trained model (~500MB)
- `hybrik/` - HybrIK source code
- `model_files/` - Model data files

**Note**: If HybrIK is not available, the app will automatically use MediaPipe (2D pose estimation) which works fine but is less accurate.

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
- [ ] All Python dependencies installed (`pip list` shows fastapi, uvicorn, mediapipe, etc.)
- [ ] `.env` file exists with `SECRET_KEY` set
- [ ] (Optional) `hybrik_repo` folder exists if using HybrIK
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
- Check if `hybrik_repo` folder exists
- Check if PyTorch is installed: `python -c "import torch; print(torch.__version__)"`
- App will fall back to MediaPipe automatically if HybrIK fails

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

✅ **Without HybrIK (MediaPipe only):**
- 2D pose estimation
- All 10 core metrics
- AI feedback
- Skeleton visualization
- Session tracking

✅ **With HybrIK:**
- 3D SMPL pose estimation (more accurate)
- Better occlusion handling
- Same features as above, but with improved accuracy

---

## Next Steps

1. **Register/Login**: Create an account at http://localhost:5173/register
2. **Upload Video**: Upload a golf swing video (MP4 format recommended)
3. **View Analysis**: See detailed metrics, scores, and AI feedback
4. **Track Progress**: Use the Dashboard to see your improvement over time

Enjoy analyzing your golf swings! 🏌️‍♂️



