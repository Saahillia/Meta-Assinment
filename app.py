from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from supportops_openenv.environment import SupportOpsEnv


app = FastAPI(title="SupportOps OpenEnv", version="0.1.0")
_ENV = SupportOpsEnv(task_id="refund_routing", seed=7)


class ResetRequest(BaseModel):
    seed: int = 7
    task_id: str = "refund_routing"


class StepRequest(BaseModel):
    action: dict = Field(default_factory=dict)


@app.get("/")
def root() -> PlainTextResponse:
    return PlainTextResponse("SupportOps OpenEnv is running.")


@app.post("/reset")
def reset_env(request: ResetRequest = ResetRequest()) -> JSONResponse:
    observation = _ENV.reset(seed=request.seed, task_id=request.task_id)
    return JSONResponse(content=observation.model_dump(mode="json"))


@app.post("/step")
def step_env(request: StepRequest) -> JSONResponse:
    try:
        observation, reward, done, info = _ENV.step(request.action)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return JSONResponse(
        content={
            "observation": observation.model_dump(mode="json"),
            "reward": reward.model_dump(mode="json"),
            "done": done,
            "info": info,
        }
    )


@app.get("/state")
def state_env() -> JSONResponse:
    return JSONResponse(content=_ENV.state().model_dump(mode="json"))


def main() -> None:
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
