from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class TicketSnapshot(BaseModel):
    ticket_id: str
    subject: str
    customer_name: str
    customer_tier: Literal["free", "pro", "enterprise"]
    channel: Literal["email", "chat", "phone"]
    product: str
    body: str
    account_age_days: int
    sentiment: Literal["neutral", "frustrated", "urgent", "angry"]
    locale: Literal["en-US"] = "en-US"


class SupportAction(BaseModel):
    action_type: Literal[
        "classify",
        "set_priority",
        "assign",
        "draft_response",
        "add_note",
        "escalate",
        "set_followup",
        "close",
    ]
    classification: str | None = None
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignee: str | None = None
    response_text: str | None = None
    note: str | None = None
    escalated_to: str | None = None
    followup_days: int | None = None
    close_reason: str | None = None


class Reward(BaseModel):
    value: float = 0.0
    delta: float = 0.0
    task_score: float = 0.0
    penalty: float = 0.0
    components: dict[str, float] = Field(default_factory=dict)
    done: bool = False
    reason: str = "in_progress"


class SupportState(BaseModel):
    episode_id: str
    task_id: str
    task_name: str
    difficulty: TaskDifficulty
    ticket: TicketSnapshot
    classification: str | None = None
    priority: str | None = None
    assignee: str | None = None
    response_draft: str = ""
    notes: list[str] = Field(default_factory=list)
    escalated_to: str | None = None
    followup_days: int | None = None
    close_reason: str | None = None
    status: Literal["open", "waiting_on_customer", "in_progress", "resolved"] = "open"
    step_count: int = 0
    max_steps: int = 6
    action_log: list[str] = Field(default_factory=list)
    hidden_score: float = 0.0


class SupportObservation(BaseModel):
    episode_id: str
    task_id: str
    task_name: str
    difficulty: TaskDifficulty
    ticket: TicketSnapshot
    status: str
    classification: str | None
    priority: str | None
    assignee: str | None
    response_draft: str
    notes: list[str]
    escalated_to: str | None
    followup_days: int | None
    step_count: int
    max_steps: int
    recent_actions: list[str]
    score_estimate: float


class SupportTaskSpec(BaseModel):
    task_id: str
    name: str
    difficulty: TaskDifficulty
    ticket: TicketSnapshot
    required_classification: str
    required_priority: str
    required_assignee: str
    response_must_include: list[str] = Field(default_factory=list)
    response_must_avoid: list[str] = Field(default_factory=list)
    required_notes: list[str] = Field(default_factory=list)
    required_escalated_to: str | None = None
    required_followup_days: int | None = None
    closing_required: bool = True
