"""Search helpers for the stage engine.

* ``iddfs``: iterative deepening over single turns (used for the daisy).
* ``find_blocks``: breadth-first search over "setup + algorithm" blocks. For
  last-layer stages this is case recognition: try each algorithm with each setup
  turn and keep the shortest sequence that reaches the goal.
"""
from __future__ import annotations

from itertools import product
from typing import Callable, Sequence

from .algorithms import Algorithm
from .cube_model import apply, split_move

State = tuple[str, ...]
Goal = Callable[[State], bool]

AUF = ["", "U", "U'", "U2"]
Y_ROTATIONS = ["", "y", "y'", "y2"]
_OPPOSITE = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}


def iddfs(state: State, goal: Goal, moves: Sequence[str], max_depth: int) -> list[str] | None:
    """Shortest move list (up to ``max_depth``) that reaches ``goal``."""
    if goal(state):
        return []
    path: list[str] = []

    def dfs(s: State, depth: int, last: str) -> bool:
        for m in moves:
            base = split_move(m)[0]
            # Skip redundant sequences: same face twice, or opposite faces in both orders.
            if base == last or (_OPPOSITE.get(base) == last and base in "DLB"):
                continue
            s2 = apply(s, (m,))
            path.append(m)
            if depth == 1:
                if goal(s2):
                    return True
            elif dfs(s2, depth - 1, base):
                return True
            path.pop()
        return False

    for depth in range(1, max_depth + 1):
        if dfs(state, depth, ""):
            return path
    return None


Block = tuple[str, Algorithm]


def find_blocks(
    state: State,
    setups: Sequence[str],
    algorithms: Sequence[Algorithm],
    goal: Goal,
    max_blocks: int,
) -> list[Block] | None:
    """Fewest ``(setup, algorithm)`` blocks that reach ``goal``; ties keep list order."""
    if goal(state):
        return []
    blocks = [(setup, alg) for alg in algorithms for setup in setups]
    for n in range(1, max_blocks + 1):
        for combo in product(blocks, repeat=n):
            s = state
            for setup, alg in combo:
                s = apply(apply(s, setup), alg.moves)
            if goal(s):
                return list(combo)
    return None


def find_setup(state: State, setups: Sequence[str], goal: Goal) -> str | None:
    for setup in setups:
        if goal(apply(state, setup)):
            return setup
    return None
