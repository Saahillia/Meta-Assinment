from __future__ import annotations

from .models import SupportState, SupportTaskSpec


_SCORE_EPSILON = 1e-6


def _normalized_contains(haystack: str, needle: str) -> bool:
    return needle.lower() in haystack.lower()


def _score_coverage(items: list[str], text: str) -> float:
    if not items:
        return 1.0
    hits = sum(1 for item in items if _normalized_contains(text, item))
    return hits / len(items)


def _score_standard_fields(state: SupportState, task: SupportTaskSpec) -> tuple[float, dict[str, float], float]:
    components: dict[str, float] = {}
    score = 0.0
    components["classification"] = 0.25 if state.classification == task.required_classification else 0.0
    components["priority"] = 0.15 if state.priority == task.required_priority else 0.0
    components["assignee"] = 0.15 if state.assignee == task.required_assignee else 0.0
    components["followup"] = 0.10 if state.followup_days == task.required_followup_days else 0.0
    components["escalation"] = 0.10 if (task.required_escalated_to is None or state.escalated_to == task.required_escalated_to) else 0.0
    components["close_state"] = 0.05 if ((task.closing_required and state.status == "resolved") or (not task.closing_required and state.status == "waiting_on_customer")) else 0.0
    components["response"] = 0.20 * _score_coverage(task.response_must_include, state.response_draft)
    score = sum(components.values())
    forbidden_hits = sum(1 for item in task.response_must_avoid if _normalized_contains(state.response_draft, item))
    penalty = min(0.20, forbidden_hits * 0.10)
    return score, components, penalty


def _score_notes(state: SupportState, task: SupportTaskSpec) -> float:
    note_text = " ".join(state.notes + state.action_log)
    return 0.10 * _score_coverage(task.required_notes, note_text)


def _score_task(state: SupportState, task: SupportTaskSpec) -> float:
    score, components, penalty = _score_standard_fields(state, task)
    score += _score_notes(state, task)
    score -= penalty
    if task.task_id == "outage_coordination" and _normalized_contains(state.response_draft, "apac"):
        score += 0.05
    if task.task_id == "access_review" and any(_normalized_contains(state.response_draft, forbidden) for forbidden in task.response_must_avoid):
        score -= 0.20
    # Phase 2 validation requires each task score to be strictly inside (0, 1).
    return max(_SCORE_EPSILON, min(1.0 - _SCORE_EPSILON, score))


def score_refund_routing(state: SupportState, task: SupportTaskSpec) -> float:
    return _score_task(state, task)


def score_outage_coordination(state: SupportState, task: SupportTaskSpec) -> float:
    return _score_task(state, task)


def score_access_review(state: SupportState, task: SupportTaskSpec) -> float:
    return _score_task(state, task)
