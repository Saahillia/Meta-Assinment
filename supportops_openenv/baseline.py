from __future__ import annotations

import argparse
import json
import os
from statistics import mean
from typing import Any

from openai import OpenAI

from .environment import SupportOpsEnv


SYSTEM_PROMPT = (
    "You are operating a support-operations agent. Return a single JSON object with exactly one action. "
    "Use action_type values from: classify, set_priority, assign, draft_response, add_note, escalate, set_followup, close. "
    "Do not include markdown, explanations, or extra keys."
)


def _scripted_policy(task_id: str) -> list[dict[str, Any]]:
    if task_id == "refund_routing":
        return [
            {"action_type": "classify", "classification": "billing_refund"},
            {"action_type": "set_priority", "priority": "high"},
            {"action_type": "assign", "assignee": "billing-team"},
            {"action_type": "add_note", "note": "Order id 77841 flagged for refund review."},
            {
                "action_type": "draft_response",
                "response_text": "Sorry for the trouble. We have initiated the refund and you should see it in 24-48 hours.",
            },
            {"action_type": "close", "close_reason": "refund_initiated"},
        ]
    if task_id == "outage_coordination":
        return [
            {"action_type": "classify", "classification": "incident_status"},
            {"action_type": "set_priority", "priority": "urgent"},
            {"action_type": "assign", "assignee": "oncall-sre"},
            {"action_type": "escalate", "escalated_to": "incident-manager"},
            {"action_type": "set_followup", "followup_days": 1},
            {"action_type": "add_note", "note": "APAC customers affected after 02:10 UTC deploy."},
            {
                "action_type": "draft_response",
                "response_text": "We have identified an active incident affecting APAC users. The team is working on a workaround and will share the ETA shortly.",
            },
            {"action_type": "close", "close_reason": "incident_briefed"},
        ]
    return [
        {"action_type": "classify", "classification": "account_access"},
        {"action_type": "set_priority", "priority": "medium"},
        {"action_type": "assign", "assignee": "security-review"},
        {"action_type": "add_note", "note": "Do not disclose PII; request verification before restoring access."},
        {"action_type": "set_followup", "followup_days": 2},
        {
            "action_type": "draft_response",
            "response_text": "Please verify your identity with the security team and we will restore access after review.",
        },
    ]


def _build_messages(observation_json: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                "Given the environment observation below, choose the best next action. "
                "Output only valid JSON.\n\n"
                f"Observation:\n{observation_json}"
            ),
        },
    ]


def _parse_action(raw_text: str) -> dict[str, Any]:
    raw_text = raw_text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`")
    return json.loads(raw_text)


def _call_model(client: OpenAI, model: str, observation_json: str) -> dict[str, Any]:
    response = client.responses.create(
        model=model,
        input=_build_messages(observation_json),
        temperature=0,
        max_output_tokens=300,
    )
    text = response.output_text
    if not text:
        raise RuntimeError("Model returned an empty response.")
    return _parse_action(text)


def run_episode(task_id: str, seed: int, mode: str, client: OpenAI | None = None, model: str | None = None) -> dict[str, Any]:
    env = SupportOpsEnv(task_id=task_id, seed=seed)
    observation = env.reset(seed=seed, task_id=task_id)
    rewards: list[float] = []
    done = False
    step_info: dict[str, Any] = {"task_id": task_id, "seed": seed}

    for action_index in range(6):
        if mode == "openai":
            assert client is not None and model is not None
            observation_json = json.dumps(observation.model_dump(mode="json"), sort_keys=True)
            action = _call_model(client, model, observation_json)
        else:
            scripted_actions = _scripted_policy(task_id)
            if action_index >= len(scripted_actions):
                break
            action = scripted_actions[action_index]
            observation, reward, done, step_info = env.step(action)
        rewards.append(reward.value)
        if done:
            break

    final_state = env.state()
    return {
        "task_id": task_id,
        "seed": seed,
        "final_score": final_state.hidden_score,
        "reward_sum": sum(rewards),
        "steps": final_state.step_count,
        "done": done,
        "step_info": step_info,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the OpenAI baseline for SupportOps OpenEnv.")
    parser.add_argument("--model", default=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))
    parser.add_argument("--mode", choices=["openai", "scripted"], default="openai")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    client = None
    if args.mode == "openai":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY is required to run the OpenAI baseline.")

        client = OpenAI(api_key=api_key)

    tasks = ["refund_routing", "outage_coordination", "access_review"]
    results = [run_episode(task_id, args.seed, args.mode, client=client, model=args.model) for task_id in tasks]
    summary = {
        "mode": args.mode,
        "model": args.model,
        "seed": args.seed,
        "results": results,
        "average_score": mean(result["final_score"] for result in results),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
