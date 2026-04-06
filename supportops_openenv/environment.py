from __future__ import annotations

import copy
import json
import random
from dataclasses import dataclass
from typing import Any, Callable

from .grading import score_access_review, score_outage_coordination, score_refund_routing
from .models import Reward, SupportAction, SupportObservation, SupportState, SupportTaskSpec
from .tasks import get_task_specs


ScoreFn = Callable[[SupportState, SupportTaskSpec], float]


@dataclass(frozen=True)
class TaskRuntime:
    spec: SupportTaskSpec
    scorer: ScoreFn


class SupportOpsEnv:
    """A deterministic support-operations environment with step/reset/state semantics."""

    def __init__(self, task_id: str | None = None, seed: int = 0):
        self._rng = random.Random(seed)
        self._seed = seed
        self._task_id = task_id
        self._tasks = self._build_runtime_tasks()
        self._current_task: TaskRuntime | None = None
        self._state: SupportState | None = None
        self._previous_score = 0.0

    @staticmethod
    def _build_runtime_tasks() -> dict[str, TaskRuntime]:
        tasks = get_task_specs()
        return {
            "refund_routing": TaskRuntime(tasks["refund_routing"], score_refund_routing),
            "outage_coordination": TaskRuntime(tasks["outage_coordination"], score_outage_coordination),
            "access_review": TaskRuntime(tasks["access_review"], score_access_review),
        }

    def _choose_task(self, task_id: str | None = None) -> TaskRuntime:
        selected = task_id or self._task_id
        if selected is None:
            selected = self._rng.choice(list(self._tasks))
        if selected not in self._tasks:
            raise KeyError(f"Unknown task_id: {selected}")
        return self._tasks[selected]

    def _build_observation(self) -> SupportObservation:
        assert self._state is not None
        return SupportObservation(
            episode_id=self._state.episode_id,
            task_id=self._state.task_id,
            task_name=self._state.task_name,
            difficulty=self._state.difficulty,
            ticket=self._state.ticket,
            status=self._state.status,
            classification=self._state.classification,
            priority=self._state.priority,
            assignee=self._state.assignee,
            response_draft=self._state.response_draft,
            notes=list(self._state.notes),
            escalated_to=self._state.escalated_to,
            followup_days=self._state.followup_days,
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            recent_actions=self._state.action_log[-3:],
            score_estimate=self._state.hidden_score,
        )

    def _serialize_action(self, action: SupportAction) -> str:
        return json.dumps(action.model_dump(exclude_none=True), sort_keys=True)

    def _apply_action(self, action: SupportAction) -> bool:
        assert self._state is not None
        invalid_action = False
        action_type = action.action_type
        if action_type == "classify" and action.classification:
            self._state.classification = action.classification
            self._state.status = "in_progress"
        elif action_type == "set_priority" and action.priority:
            self._state.priority = action.priority
        elif action_type == "assign" and action.assignee:
            self._state.assignee = action.assignee
        elif action_type == "draft_response" and action.response_text:
            self._state.response_draft = action.response_text.strip()
        elif action_type == "add_note" and action.note:
            self._state.notes.append(action.note.strip())
        elif action_type == "escalate" and action.escalated_to:
            self._state.escalated_to = action.escalated_to
        elif action_type == "set_followup" and action.followup_days is not None:
            self._state.followup_days = action.followup_days
        elif action_type == "close":
            self._state.status = "resolved"
            self._state.close_reason = action.close_reason or "agent_closed"
        else:
            self._state.action_log.append("invalid_action_payload")
            invalid_action = True

        self._state.action_log.append(self._serialize_action(action))
        if self._state.classification and self._state.assignee and self._state.priority:
            self._state.status = "in_progress"
        if self._state.status != "resolved" and self._state.followup_days is not None:
            self._state.status = "waiting_on_customer"
        return invalid_action

    def _compute_score(self) -> float:
        assert self._state is not None and self._current_task is not None
        score = self._current_task.scorer(self._state, self._current_task.spec)
        self._state.hidden_score = score
        return score

    def reset(self, seed: int | None = None, task_id: str | None = None) -> SupportObservation:
        if seed is not None:
            self._rng.seed(seed)
            self._seed = seed
        runtime = self._choose_task(task_id)
        self._current_task = runtime
        episode_id = f"episode-{self._seed}-{runtime.spec.task_id}-{self._rng.randint(1000, 9999)}"
        self._state = SupportState(
            episode_id=episode_id,
            task_id=runtime.spec.task_id,
            task_name=runtime.spec.name,
            difficulty=runtime.spec.difficulty,
            ticket=copy.deepcopy(runtime.spec.ticket),
            max_steps=6,
        )
        self._previous_score = 0.0
        self._compute_score()
        return self._build_observation()

    def state(self) -> SupportState:
        if self._state is None:
            raise RuntimeError("Environment has not been reset yet.")
        return self._state.model_copy(deep=True)

    def step(self, action: SupportAction | dict[str, Any]) -> tuple[SupportObservation, Reward, bool, dict[str, Any]]:
        if self._state is None or self._current_task is None:
            raise RuntimeError("Call reset() before step().")
        parsed_action = action if isinstance(action, SupportAction) else SupportAction.model_validate(action)
        invalid_action = self._apply_action(parsed_action)
        self._state.step_count += 1
        current_score = self._compute_score()
        delta = current_score - self._previous_score
        penalty = 0.0
        if invalid_action:
            penalty -= 0.10
        if parsed_action.action_type == "close" and current_score < 0.85:
            penalty -= 0.20
        reward_value = delta + penalty
        self._previous_score = current_score
        done = self._is_done()
        reward = Reward(
            value=reward_value,
            delta=delta,
            task_score=current_score,
            penalty=penalty,
            components={"incremental_progress": max(0.0, delta), "behavior_penalty": penalty},
            done=done,
            reason=self._done_reason() if done else "in_progress",
        )
        info = {
            "score": current_score,
            "task_id": self._state.task_id,
            "difficulty": self._state.difficulty.value,
            "seed": self._seed,
        }
        return self._build_observation(), reward, done, info

    def _is_done(self) -> bool:
        assert self._state is not None and self._current_task is not None
        if self._state.step_count >= self._state.max_steps:
            return True
        if self._state.hidden_score >= 0.999:
            return True
        if self._state.status == "resolved" and self._state.hidden_score >= 0.90:
            return True
        return False

    def _done_reason(self) -> str:
        assert self._state is not None
        if self._state.step_count >= self._state.max_steps:
            return "max_steps"
        if self._state.hidden_score >= 0.999:
            return "task_complete"
        if self._state.status == "resolved" and self._state.hidden_score >= 0.90:
            return "resolved"
        return "in_progress"

    def close(self) -> None:
        return None
