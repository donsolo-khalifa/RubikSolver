"""Solver entry point: ``solve(facelets, method)`` with a safety check on every solution."""
from __future__ import annotations

import logging

from .. import config
from .base import METHODS, Method, Solution, SolveError
from .cube_model import apply, is_solved
from .methods import advanced, beginner, intermediate

log = logging.getLogger(__name__)

_SOLVERS = {
    "beginner": beginner.solve,
    "intermediate": intermediate.solve,
    "advanced": advanced.solve,
}


_COLOR_NAMES = {"W": "white", "Y": "yellow", "R": "red", "O": "orange", "G": "green", "B": "blue"}


def _fill_colours(solution: Solution, scheme: dict[str, str]) -> None:
    """Replace {first}/{last}/{front} in stage texts with this cube's colour names.

    first = the top colour in the scan hold (the layer-by-layer methods solve it first, on
    the bottom); last = the colour opposite it; front = the colour facing the camera.
    """
    names = {"first": scheme["U"], "last": scheme["D"], "front": scheme["F"]}
    words = {k: _COLOR_NAMES[c] for k, c in names.items()}
    words |= {k.capitalize(): v.capitalize() for k, v in words.items()}
    for st in solution.stages:
        st.name = st.name.format_map(words)
        st.goal = st.goal.format_map(words)
        st.explanation = st.explanation.format_map(words)
        st.tips = [t.format_map(words) for t in st.tips]


def solve(facelets: str, method: Method = "beginner", scheme: dict[str, str] | None = None) -> Solution:
    """Solve a 54-character URFDLB facelet string. Raises SolveError rather than return a wrong solution."""
    if method not in METHODS:
        raise SolveError(f"unknown method {method!r}")
    if len(facelets) != 54:
        raise SolveError("facelet string must have 54 characters")
    state = tuple(facelets)
    try:
        solution = _SOLVERS[method](state)
    except SolveError:
        log.error("solver %s failed on %s", method, facelets)
        raise
    # Safety check: never hand the user a solution that doesn't solve the cube.
    if not is_solved(apply(state, solution.notation())):
        log.error("solver %s produced a wrong solution for %s", method, facelets)
        raise SolveError("internal error: the solution did not solve the cube")
    _fill_colours(solution, scheme or config.COLOR_SCHEME)
    return solution


__all__ = ["solve", "Solution", "SolveError", "METHODS", "Method"]
