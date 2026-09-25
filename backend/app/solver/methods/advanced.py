"""Advanced method: Kociemba's two-phase algorithm, about 20 moves (PLAN.md 7.6)."""
from __future__ import annotations

from ..base import Move, Solution, SolveError, Stage
from ..cube_model import is_solved, parse, to_string
from ..describe import describe

State = tuple[str, ...]


def _kociemba(facelets: str) -> str:
    try:
        import kociemba
    except ImportError:  # pragma: no cover - fallback for Windows without MSVC build tools
        try:
            import twophase.solver as sv  # RubikTwoPhase
        except ImportError as e:
            raise SolveError("Neither 'kociemba' nor 'RubikTwoPhase' is installed") from e
        out = sv.solve(facelets, 20, 2)
        # RubikTwoPhase writes "R1 U3 (19f)"; convert to standard notation.
        tokens = [t for t in out.split() if not t.startswith("(")]
        return " ".join(t[0] + {"1": "", "2": "2", "3": "'"}[t[1]] for t in tokens)
    try:
        return kociemba.solve(facelets)
    except ValueError as e:
        raise SolveError(f"Kociemba could not solve this cube: {e}") from e


def solve(state: State) -> Solution:
    moves = [] if is_solved(state) else parse(_kociemba(to_string(state)))
    stage = Stage(
        name="Solve",
        goal="Solve the cube",
        explanation=(
            "This is the computer's shortest-ish solution. It doesn't follow human steps, "
            "so just follow each move carefully."
        ),
        tips=["Keep the cube with {first} on top and {front} facing you the whole time."],
        moves=[Move(m, describe(m)) for m in moves],
    )
    return Solution("advanced", [stage])
