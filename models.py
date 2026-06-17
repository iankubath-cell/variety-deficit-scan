# models.py
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime
import uuid

class PromptData(BaseModel):
    id: str
    category: str
    text: str
    rationale: Optional[str] = None
    predictions: Optional[dict] = None

class LLMResponse(BaseModel):
    raw_content: str
    parsed_decision: Optional[Literal["ALLOW", "BLOCK"]] = None
    parsed_confidence: Optional[int] = None
    parsed_reason: Optional[str] = None
    is_parsed: bool = False

class TestRunResult(BaseModel):
    run_id: str
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    prompt_id: str
    category: str
    prompt_text: str
    mode: Literal["single_call", "isolated_call", "hybrid_call"]
    
    l1_output: str
    l2_decision: str
    l2_confidence: int
    l2_reason: str
    final_output: str
    
    # Metadata
    latency_ms: int
    tokens_used_l1: int = 0
    tokens_used_l2: int = 0
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class BatchSummary(BaseModel):
    total_prompts: int
    total_modes: int
    start_time: str
    end_time: str
    error_count: int
