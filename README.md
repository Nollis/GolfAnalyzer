# Golf Swing Analyzer

A comprehensive full-stack application to analyze golf swings using computer vision (YOLO/SAM-3D) and AI feedback.

## Features

### Core Analysis
- **Video Upload**: Upload swing videos for detailed biomechanical analysis
- **Pose Estimation**: Extracts 33 body landmarks (**MediaPipe landmark format / indices**, not the `mediapipe` package) using YOLO/SAM-3D
- **Swing Phase Detection**: Automatically identifies Address, Top, Impact, and Finish phases
- **Position Analysis**: 
  - Visual breakdown of key swing phases
  - Auto-zoom for clear visibility
  - **Pro Comparison**: Overlay professional reference skeleton for visual feedback
- **Metric Computation**: Calculates 14+ key biomechanical metrics:
  - Tempo ratio (backswing:downswing)
  - Shoulder and hip rotation
  - Spine tilt at address and impact
  - Head movement (lateral and vertical)
  - Wrist angles (flexion and hinge)
  - Shaft lean at impact
- **Scoring System**: Rates each metric against professional benchmarks (0-100 scale)
- **AI Coaching**: Generates personalized feedback and drill recommendations using OpenAI
- **Real-time Feedback**: Upload progress bar and status updates during analysis

### User Management
- **Authentication**: Secure email/password login with JWT tokens
- **User Profiles**: Track handicap, handedness, and skill level
- **Session History**: Browse, filter, and delete previous swing analyses
- **Personal Best Tracking**: Mark and compare against your best swings

### Progress Tracking
- **Dashboard**: Quick stats showing total swings, average score, and recent sessions
- **Trend Charts**: Visualize improvement over time with interactive Chart.js graphs
- **Session Comparison**: Side-by-side comparison of any two swing sessions
- **Analytics**: Track metrics by club type and date range

### Enhanced Feedback
- **Metric Explainers**: Interactive tooltips explaining each technical metric
- **Visual Diagrams**: SVG diagrams illustrating ideal positions (tempo, rotation angles)
- **Drill Library**: Curated collection of drills filtered by category and difficulty
- **Drill Details**: Video tutorials and target metrics for each drill

### Smart Features
- **Auto-Detection**: 
  - Handedness detection based on backswing direction
  - Club type estimation from swing tempo and duration
- **Skill Assessment**: Automatic skill level categorization (Beginner/Intermediate/Advanced/Pro)

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.9+)
- **Computer Vision**: YOLOv8 (2D Phase) + SAM-3D (3D Joint Support)
- **Database**: SQLite (SQLAlchemy ORM)
- **AI**: OpenAI GPT for feedback generation
- **Authentication**: JWT tokens with bcrypt password hashing

### External (not vendored in this repo)

- **SAM-3D MHR**: The 3D joint reconstruction is performed by an **external** sibling repo `sam-3d-body/` (invoked via subprocess). Configure via `.env` (`SAM3D_REPO`, `SAM3D_PYTHON`).

### Frontend
- **Framework**: SvelteKit with TypeScript
- **Styling**: Tailwind CSS
- **Charts**: Chart.js
- **State Management**: Svelte stores

## Setup

### Prerequisites

- Python 3.9+
- Node.js 18+
- OpenAI API key (optional, for AI feedback)

### Backend Setup

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set environment variables** (create `.env` file):
   ```bash
   OPENAI_API_KEY=sk-your-key-here
   SECRET_KEY=your-secret-key-for-jwt
   ```

4. **Create admin user** (optional):
   ```bash
   python app/core/create_admin.py
   ```

5. **Seed drill data**:
   ```bash
   python app/core/seed_drills.py
   ```

6. **Run the server**:
   ```bash
   uvicorn app.main:app --reload
   ```
   API available at `http://localhost:8000` (docs at `/docs`)

### Frontend Setup

1. **Navigate to frontend**:
   ```bash
   cd frontend
   ```

2. **Install dependencies**:
   ```bash
   npm install
   ```

3. **Run development server**:
   ```bash
   npm run dev
   ```
   UI available at `http://localhost:5173`

## Usage

1. **Register/Login**: Create an account or log in at `http://localhost:5173/login`
2. **Upload Video**: Go to home page and upload a golf swing video (MP4 recommended)
3. **Configure Analysis**: 
   - Select camera view (Face On or Down the Line)
   - Optionally select handedness and club type (or use auto-detect)
4. **View Results**: 
   - See detailed metrics with scores and visual indicators
   - Read AI-generated feedback and drill recommendations
   - Watch your video with phase markers
5. **Track Progress**:
   - Visit Dashboard to see your stats and recent swings
   - Use Progress page to view trend charts
   - Compare sessions to track improvement
6. **Explore Drills**: Browse the drill library for targeted practice exercises

## Project Structure

```
GolfAnalyzer/
├── app/                    # Backend FastAPI application
│   ├── api/               # API routes
│   ├── core/              # Config, database, security
│   ├── models/            # SQLAlchemy models
│   ├── schemas.py         # Pydantic schemas
│   └── services/          # Business logic
├── pose/                  # Pose estimation and analysis

│   ├── types.py
│   ├── swing_detection.py
│   └── metrics.py
├── reference/             # Reference profiles and scoring
├── services/              # AI feedback service
├── frontend/              # SvelteKit application
│   └── src/
│       ├── routes/        # Pages
│       └── lib/           # Components and stores
├── videos/                # Uploaded video storage
└── requirements.txt
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Create account
- `POST /api/v1/auth/login` - Login
- `GET /api/v1/auth/me` - Get current user
- `PUT /api/v1/auth/me` - Update profile

### Analysis
- `POST /api/v1/analyze-swing` - Upload and analyze video
- `GET /api/v1/sessions` - List user's sessions
- `GET /api/v1/sessions/{id}` - Get session details
- `GET /api/v1/sessions/{id}/video` - Stream video

### Analytics
- `GET /api/v1/analytics/trends` - Get metric trends
- `GET /api/v1/analytics/comparison` - Compare two sessions

### Drills
- `GET /api/v1/drills` - List drills (with filters)
- `GET /api/v1/drills/{id}` - Get drill details

## Development

### Running Tests
```bash
python test_auto_detect.py
python test_skill_assessment.py
```

### Database Migrations
The application uses SQLite with SQLAlchemy. Schema changes are applied automatically on startup.

## License

MIT License - See LICENSE file for details

