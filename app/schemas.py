from pydantic import BaseModel, Field, ConfigDict
from typing import Dict, Any
from datetime import datetime

class MetricInput(BaseModel):
    game_id: str = Field(..., min_length=1, max_length=64)
    player_id: str = Field(..., min_length=1, max_length=64)
    event_type: str = Field(..., min_length=2, max_length=50)
    payload: Dict[str, Any] = Field(default_factory=dict)

class MetricResponse(BaseModel):
    id: int
    game_id: str
    event_type: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
