# SupportOps OpenEnv

SupportOps OpenEnv is a real-world support-operations environment for training agents on ticket triage, incident escalation, access reviews, and compliant customer communication.

The environment follows a simple agent loop: call `reset()` to start a task, use `step(action)` to make structured changes, and inspect `state()` at any point for the full internal state. It is designed for realistic workflow automation rather than games or toy puzzles. The Space serves HTTP endpoints.

## Motivation

Human support teams repeatedly perform structured but judgment-heavy work: classify tickets, assign ownership, draft responses, route incidents, and avoid exposing sensitive data. This benchmark turns that kind of work into a reproducible environment with deterministic grading.

## Tasks

The environment includes three tasks with increasing difficulty:

1. `refund_routing` - easy. Triage a refund request, route to billing, and draft a polite response.
2. `outage_coordination` - medium. Escalate an outage, assign SRE ownership, and produce a customer-facing incident update.
3. `access_review` - hard. Handle an access request, require verification, and avoid leaking sensitive identifiers.

## API

`reset(seed=None, task_id=None)` returns the initial observation.

`step(action)` returns `(observation, reward, done, info)` where `reward` is a typed `Reward` model.

`state()` returns the current typed `SupportState`.

## Action space

Actions are structured JSON objects parsed into `SupportAction`.

Supported `action_type` values:

- `classify`
- `set_priority`
- `assign`
- `draft_response`
- `add_note`
- `escalate`
- `set_followup`
- `close`

## Observation space

The observation exposes the ticket snapshot, current classification, priority, assignee, response draft, notes, escalation target, follow-up window, recent actions, and current score estimate.

## Reward design

Reward is incremental and shaped over the full trajectory. The environment computes a task score in the range `0.0` to `1.0`, then returns the positive delta as per-step reward. Invalid or clearly undesirable actions receive penalties, including early closure before the rubric is satisfied.

## Baseline scores

The baseline script uses the OpenAI API client and runs with `OPENAI_API_KEY` by default. It also includes a scripted reference mode for reproducible local scoring without an API key.

Run it with:

```bash
python -m supportops_openenv.baseline --seed 7
```

The output includes a per-task final score and an average score. Because the score depends on the selected model, keep the model fixed with `OPENAI_MODEL` for reproducible comparisons across runs.

Reference scripted scores with `--mode scripted --seed 7`:

| Task | Score |
| --- | --- |
| `refund_routing` | `1.0` |
| `outage_coordination` | `0.85` |
| `access_review` | `1.0` |
| Average | `0.95` |

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Round 1 Checklist

The platform guide describes this flow for Round 1:

1. Confirm your local toolchain: Python 3.10+, Git, Hugging Face CLI, OpenEnv, and Docker.
2. If you are starting from scratch, scaffold with `openenv init my_env`.
3. Build and run the environment locally, then verify the submission path with `uv run server`.
4. Deploy to Hugging Face Spaces and push with `openenv push --repo-id your-username/my-env`.
5. Submit the Hugging Face Space URL in the application form.

This repository is already scaffolded, so you can work directly in the existing project instead of re-running initialization.

## Usage

Run the environment demo locally:

```bash
uv run server
```

Run the baseline:

```bash
export OPENAI_API_KEY=...
export OPENAI_MODEL=gpt-4.1-mini
python -m supportops_openenv.baseline --seed 7
```

For the fully reproducible local reference run:

```bash
python -m supportops_openenv.baseline --mode scripted --seed 7
```

## Submission inference script

The required submission entrypoint is [inference.py](inference.py). It uses the OpenAI client with these environment variables:

- `API_BASE_URL`
- `MODEL_NAME`
- `HF_TOKEN`
- `LOCAL_IMAGE_NAME` if you are running from a Docker image

The script emits only the required `[START]`, `[STEP]`, and `[END]` log lines and runs all three tasks sequentially.

## Hugging Face Spaces and Docker

This repository is container-ready and can be deployed as a Docker Hugging Face Space tagged with `openenv`.

To build and run locally:

```bash
docker build -t supportops-openenv .
docker run -p 7860:7860 supportops-openenv
```

## Project files

- `openenv.yaml` - environment metadata and task registry
- `supportops_openenv/environment.py` - `reset()`, `step()`, and `state()` implementation
- `supportops_openenv/models.py` - typed Pydantic models
- `supportops_openenv/grading.py` - deterministic task graders
- `supportops_openenv/baseline.py` - OpenAI API baseline runner
- `inference.py` - submission entrypoint and structured stdout logger
- `app.py` - FastAPI server for Hugging Face Spaces
