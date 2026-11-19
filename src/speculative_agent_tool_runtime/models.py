from typing import Any, Dict, Optional, Literal
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class ToolSafetyLevel(str, Enum):
    SAFE_READ_ONLY = "SAFE_READ_ONLY"
    SANDBOXED_TRANSACTIONAL = "SANDBOXED_TRANSACTIONAL"
    MUTATING_SIDE_EFFECT = "MUTATING_SIDE_EFFECT"

class SpeculativeTask(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str
    arguments: Dict[str, Any]
    safety_level: ToolSafetyLevel
    status: Literal["PENDING", "EXECUTING", "COMPLETED", "PURGED"] = "PENDING"
    result: Optional[Any] = None

class TrajectoryNode(BaseModel):
    prefix: str
    predicted_tool: str
    confidence: float
    hit_count: int = 0