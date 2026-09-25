"""Shared solver types: Move, Stage, Solution."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Method = Literal["beginner", "intermediate", "advanced"]
METHODS: tuple[Method, ...] = ("beginner", "intermediate", "advanced")


class SolveError(Exception):
    """The solver could not produce a verified solution."""


@dataclass
class Move:
    notation: str
    description: str
    # Where this move sits inside a named algorithm, for "Sune: move 4 of 7".
    algorithm: str | None = None
    step: int | None = None
    steps: int | None = None
    # For repeated algorithms: "R U R' U': repetition 2 of 5".
    rep: int | None = None
    reps: int | None = None


@dataclass
class Stage:
    name: str
    goal: str
    explanation: str
    algorithm: str | None = None
    tips: list[str] = field(default_factory=list)
    moves: list[Move] = field(default_factory=list)


@dataclass
class Solution:
    method: Method
    stages: list[Stage]

    @property
    def total_moves(self) -> int:
        """Counts turns the user makes; whole-cube rotations are not counted."""
        return sum(1 for st in self.stages for m in st.moves if m.notation[0] not in "xyz")

    def notation(self) -> list[str]:
        return [m.notation for st in self.stages for m in st.moves]

    def to_dict(self) -> dict:
        return {
            "method": self.method,
            "stages": [asdict(s) for s in self.stages],
            "totalMoves": self.total_moves,
        }
