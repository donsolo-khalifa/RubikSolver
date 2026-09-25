"""WebSocket messages (PLAN.md 8). Mirrored by frontend/src/net/protocol.ts: keep them in sync."""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, TypeAdapter

Color = Literal["W", "Y", "R", "O", "G", "B"]
Face = Literal["U", "R", "F", "D", "L", "B"]
Method = Literal["beginner", "intermediate", "advanced"]
Hint = Literal["too_far", "too_close", "hold_still", "glare", "occluded"]


# --- server -> client ---------------------------------------------------------
class DetectionMsg(BaseModel):
    type: Literal["detection"] = "detection"
    found: bool
    stable: bool
    colors: list[Color | None]
    hint: Hint | None = None


class ScanPromptMsg(BaseModel):
    type: Literal["scan_prompt"] = "scan_prompt"
    step: int
    face: Face
    rotation: str | None
    text: str


class FaceCapturedMsg(BaseModel):
    type: Literal["face_captured"] = "face_captured"
    face: Face
    colors: list[Color]


class ScanErrorMsg(BaseModel):
    type: Literal["scan_error"] = "scan_error"
    face: Face
    message: str


class CubeStateMsg(BaseModel):
    type: Literal["cube_state"] = "cube_state"
    facelets: str
    valid: bool
    errors: list[str]
    note: str | None = None


class MoveModel(BaseModel):
    notation: str
    description: str
    algorithm: str | None = None
    step: int | None = None
    steps: int | None = None
    rep: int | None = None
    reps: int | None = None


class StageModel(BaseModel):
    name: str
    goal: str
    explanation: str
    algorithm: str | None = None
    tips: list[str]
    moves: list[MoveModel]


class SolutionMsg(BaseModel):
    type: Literal["solution"] = "solution"
    method: Method
    stages: list[StageModel]
    totalMoves: int
    facelets: str  # the state the solution starts from


class PracticeMsg(BaseModel):
    type: Literal["practice"] = "practice"
    scramble: list[str]
    facelets: str


class StatusMsg(BaseModel):
    type: Literal["status"] = "status"
    camera: bool
    phase: Literal["idle", "scanning", "review", "solving"]


class ErrorMsg(BaseModel):
    type: Literal["error"] = "error"
    message: str


ServerMsg = Union[
    DetectionMsg, ScanPromptMsg, FaceCapturedMsg, ScanErrorMsg, CubeStateMsg,
    SolutionMsg, PracticeMsg, StatusMsg, ErrorMsg,
]


# --- client -> server ---------------------------------------------------------
class StartScan(BaseModel):
    type: Literal["start_scan"]


class Capture(BaseModel):
    type: Literal["capture"]


class Rescan(BaseModel):
    type: Literal["rescan"]
    face: Face


class SetSticker(BaseModel):
    type: Literal["set_sticker"]
    face: Face
    index: int = Field(ge=0, le=8)
    color: Color


class Solve(BaseModel):
    type: Literal["solve"]
    method: Method


class PracticeScramble(BaseModel):
    type: Literal["practice_scramble"]
    method: Method


class Reset(BaseModel):
    type: Literal["reset"]


ClientMsg = Annotated[
    Union[StartScan, Capture, Rescan, SetSticker, Solve, PracticeScramble, Reset],
    Field(discriminator="type"),
]
client_adapter: TypeAdapter[ClientMsg] = TypeAdapter(ClientMsg)
