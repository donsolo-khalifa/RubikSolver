"""Solver entry point: ``solve(facelets, method)`` with a safety check on every solution."""
from __future__ import annotations

import logging

from .base import METHODS, Method, Solution, SolveError
from .cube_model import apply, is_solved
from .methods import advanced, beginner, intermediate

log = logging.getLogger(__name__)

_SOLVERS = {
    "beginner": beginner.solve,
    "intermediate": intermediate.solve,
    "advanced": advanced.solve,
}


def solve(facelets: str, method: Method = "beginner") -> Solution:
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
    return solution


__all__ = ["solve", "Solution", "SolveError", "METHODS", "Method"]
