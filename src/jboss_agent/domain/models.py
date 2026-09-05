"""Domain models shared by the learning graphs.

STEP 2 introduces a Pydantic model because Gemini's response is untrusted input.
The graph state itself remains a TypedDict so State updates stay lightweight and
visible while learning LangGraph.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


IncidentCategory = Literal[
    "NORMAL",
    "THREAD_POOL",
    "DATASOURCE_POOL",
    "DEPLOYMENT",
    "UNKNOWN",
]


class LogClassification(BaseModel):
    """Structured result produced by Gemini for a block of JBoss-like logs."""

    incident_detected: bool = Field(
        description="Whether the log evidence suggests an operational incident."
    )
    category: IncidentCategory = Field(
        description="The single best category supported by the supplied log lines."
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Confidence in the classification, from 0.0 to 1.0.",
    )
    summary: str = Field(
        min_length=1,
        description="Short explanation grounded only in the supplied log lines.",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Short snippets or observations from the supplied logs.",
    )
