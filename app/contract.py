from pydantic import BaseModel, UUID4, Field
from typing import Dict, Any, Optional
from datetime import datetime

# Input Schema
class AnalysisInput(BaseModel):
    video_fps: Optional[float] = Field(None, description="Frame rate of the input video")
    view: str = Field(..., description="Camera view: 'face_on' or 'down_the_line'")
    club: str = Field(..., description="Club used: 'driver', 'iron', 'wedge'")
    handedness: str = Field("right", description="Player handedness: 'right' or 'left'")

# Output Schema
class AnalysisOutput(BaseModel):
    phases: Dict[str, int] = Field(..., description="Frame indices for Address, Top, Impact, Finish")
    metrics: Dict[str, Any] = Field(..., description="Biomechanical metric values")
    score: int = Field(..., description="Overall swing score (0-100)")
    confidence: float = Field(..., description="System confidence score (0.0-1.0)")
    
# The Master Contract
class AnalysisContract(BaseModel):
    """
    STABLE INTERNAL CONTRACT
    This schema defines the exact shape of a processed swing analysis.
    It separates input metadata, processing output, and cost accounting.
    """
    session_id: str = Field(..., description="Unique Session UUID")
    user_id: str = Field(..., description="User UUID")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    input: AnalysisInput
    output: AnalysisOutput
    
    cost_units: int = Field(1, description="Cost scaling factor for this analysis (1 = standard)")
    model_version: str = Field("v1.0.0", description="Version of the analysis engine used")

    class Config:
        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_12345",
                "input": {
                    "video_fps": 240,
                    "view": "DTL",
                    "club": "7-iron"
                },
                "output": {
                    "phases": {"address": 10, "top": 45, "impact": 60, "finish": 90},
                    "metrics": {"tempo_ratio": 3.0, "spine_angle": 45.0},
                    "score": 72,
                    "confidence": 0.91
                },
                "cost_units": 1,
                "model_version": "v1.0.0"
            }
        }
