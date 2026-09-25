"""Runs a method (an ordered list of stages) and records the moves of each stage."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Sequence

from .algorithms import Algorithm
from .base import Method, Move, Solution, SolveError, Stage
from .cube_model import apply, parse, simplify
from .describe import describe

State = tuple[str, ...]


class Builder:
    """Accumulates the moves of one stage while tracking the cube state."""

    def __init__(self, state: State):
        self.state = state
        self.moves: list[Move] = []

    def setup(self, moves: str | Sequence[str]) -> None:
        """Moves that are not part of a named algorithm (setup turns, rotations)."""
        for m in parse(moves):
            self.moves.append(Move(m, describe(m)))
            self.state = apply(self.state, (m,))

    def alg(self, alg: Algorithm, rep: int | None = None, reps: int | None = None) -> None:
        tokens = parse(alg.moves)
        for i, m in enumerate(tokens):
            self.moves.append(Move(m, describe(m), alg.name, i + 1, len(tokens), rep, reps))
        self.state = apply(self.state, tokens)

    def repeat(self, alg: Algorithm, until: Callable[[State], bool], max_reps: int) -> int:
        """Apply ``alg`` until ``until`` holds; the moves record "repetition i of n"."""
        s, n = self.state, 0
        while not until(s):
            if n == max_reps:
                raise SolveError(f"{alg.name} did not reach its goal in {max_reps} repetitions")
            s = apply(s, alg.moves)
            n += 1
        for i in range(n):
            self.alg(alg, i + 1, n)
        return n


def tidy(moves: list[Move]) -> list[Move]:
    """Merge neighbouring setup moves (``U U`` -> ``U2``); algorithm moves stay as written."""
    out: list[Move] = []
    run: list[str] = []

    def flush() -> None:
        out.extend(Move(m, describe(m)) for m in simplify(run))
        run.clear()

    for m in moves:
        if m.algorithm is None:
            run.append(m.notation)
        else:
            flush()
            out.append(m)
    flush()
    return out


@dataclass
class StageDef:
    name: str
    goal: str
    explanation: str
    run: Callable[[Builder], None]
    check: Callable[[State], bool]
    algorithm: str | None = None
    tips: list[str] = field(default_factory=list)


def run_method(state: State, method: Method, stages: Sequence[StageDef]) -> Solution:
    out: list[Stage] = []
    for sd in stages:
        b = Builder(state)
        sd.run(b)
        if not sd.check(b.state):
            raise SolveError(f"stage {sd.name!r} did not reach its goal")
        out.append(Stage(sd.name, sd.goal, sd.explanation, sd.algorithm, list(sd.tips), tidy(b.moves)))
        state = b.state
    return Solution(method, out)
