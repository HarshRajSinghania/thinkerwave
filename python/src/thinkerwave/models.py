from __future__ import annotations  # lazy annotations

from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict


class _M(BaseModel):
    model_config = ConfigDict(extra="ignore")


class RunCreated(_M):
    id: str
    status: str
    queue_position: Optional[int] = None


class RunSummary(_M):
    id: str
    problem_preview: str
    status: str
    best_score: float
    rounds_done: int
    created_at: str
    elapsed_seconds: float


class Run(_M):
    id: str
    status: str
    problem: str
    round: int
    max_rounds: int
    best_score: float
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    elapsed_seconds: float
    stop_reason: Optional[str] = None
    error: Optional[str] = None

    @property
    def finished(self) -> bool:
        return self.status in ("completed", "stopped", "failed")


class Finding(_M):
    text: str
    evidence: Optional[Literal["verified", "assumption", "guess"]] = None
    flagged: bool = False


class RoundAnswer(_M):
    answer: str
    confidence: str
    findings: list[Finding]
    text: str


class Answer(RoundAnswer):
    round: int
    score: Optional[float] = None
    final: bool


class ToolCounts(_M):
    python: int = 0
    web_search: int = 0
    pages_read: int = 0


class Round(_M):
    round: int
    score: Optional[float] = None
    change: Optional[str] = None
    answer: Optional[RoundAnswer] = None
    tools: ToolCounts


class File(_M):
    path: str
    size: Optional[int] = None
    type: Optional[str] = None
    kind: str


class Me(_M):
    email: str
    plan: str
    runs_today: int
    runs_per_day: int
    concurrent_runs: int
    max_rounds: int


class _Event(_M):
    id: Optional[int] = None


class RunStarted(_Event):
    max_rounds: Optional[int] = None


class RoundStarted(_Event):
    round: int


class RoundStep(_Event):
    round: int
    step: str


class RoundTool(_Event):
    round: int
    kind: str
    ok: bool


class RoundFinished(_Event):
    round: int
    score: Optional[float] = None
    change: Optional[str] = None
    best_so_far: bool = False


class RunWentBack(_Event):
    round: int
    to_round: int


class RunFinished(_Event):
    status: str
    stop_reason: Optional[str] = None
    best_score: Optional[float] = None


class RunError(_Event):
    message: str


Event = Union[RunStarted, RoundStarted, RoundStep, RoundTool, RoundFinished, RunWentBack, RunFinished, RunError]
_EVENTS = {"run.started": RunStarted, "round.started": RoundStarted, "round.step": RoundStep,
           "round.tool": RoundTool, "round.finished": RoundFinished, "run.went_back": RunWentBack,
           "run.finished": RunFinished, "run.error": RunError}


def parse_event(name: str, data: dict, id: Optional[int]) -> Optional[Event]:
    cls = _EVENTS.get(name)
    return cls.model_validate({**data, "id": id}) if cls else None
