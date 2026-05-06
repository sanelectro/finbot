"""
Data models for the Guardrails system
"""
from typing import Optional
from dataclasses import dataclass
from collections import deque

@dataclass
class GuardrailResult:
    """Result of a guardrail check"""
    is_safe: bool
    violation_type: Optional[str] = None
    violation_message: Optional[str] = None
    sanitized_input: Optional[str] = None
    confidence_score: Optional[float] = None

@dataclass
class SessionInfo:
    """Session tracking for rate limiting"""
    query_count: int = 0
    last_query_time: float = 0
    query_timestamps: Optional[deque] = None
    
    def __post_init__(self):
        if self.query_timestamps is None:
            self.query_timestamps = deque(maxlen=25)  # Store 25 recent queries for rate limiting
