"""Facelet-level cube model: a 54-sticker state plus a permutation for every move.

State layout is the Kociemba facelet order ``U R F D L B``, each face read left to
right, top to bottom (see PLAN.md 6.1). A state is a tuple of 54 single-character
strings; which characters are used does not matter (face letters or colours).

Move permutations are built from geometry rather than typed by hand: every facelet
gets a 3D position and outward normal, and a move rotates the ones in its layers.
Axes: +x = R, +y = U, +z = F.
"""
from __future__ import annotations

import random
from functools import lru_cache
from operator import itemgetter
from typing import Iterable, Sequence

FACES = "URFDLB"
SOLVED: tuple[str, ...] = tuple(f for f in FACES for _ in range(9))

# Index of each face's centre sticker.
CENTRE = {f: 9 * i + 4 for i, f in enumerate(FACES)}

Vec = tuple[int, int, int]


def _geometry(face: str, r: int, c: int) -> tuple[Vec, Vec]:
    """3D cubie position and outward normal of facelet (r, c) on ``face``."""
    if face == "U":
        return (c - 1, 1, r - 1), (0, 1, 0)
    if face == "R":
        return (1, 1 - r, 1 - c), (1, 0, 0)
    if face == "F":
        return (c - 1, 1 - r, 1), (0, 0, 1)
    if face == "D":
        return (c - 1, -1, 1 - r), (0, -1, 0)
    if face == "L":
        return (-1, 1 - r, c - 1), (-1, 0, 0)
    if face == "B":
        return (1 - c, 1 - r, -1), (0, 0, -1)
    raise ValueError(face)


GEOMETRY: list[tuple[Vec, Vec]] = [
    _geometry(f, i // 3, i % 3) for f in FACES for i in range(9)
]
_INDEX_OF = {g: i for i, g in enumerate(GEOMETRY)}

AXIS = {"x": 0, "y": 1, "z": 2}

# name -> (axis, layers, quarter turns for the clockwise move; -1 = -90 degrees)
BASE_MOVES: dict[str, tuple[int, tuple[int, ...], int]] = {
    "U": (1, (1,), -1),
    "D": (1, (-1,), 1),
    "R": (0, (1,), -1),
    "L": (0, (-1,), 1),
    "F": (2, (1,), -1),
    "B": (2, (-1,), 1),
    "M": (0, (0,), 1),
    "E": (1, (0,), 1),
    "S": (2, (0,), -1),
    "r": (0, (0, 1), -1),
    "l": (0, (-1, 0), 1),
    "u": (1, (0, 1), -1),
    "d": (1, (-1, 0), 1),
    "f": (2, (0, 1), -1),
    "b": (2, (-1, 0), 1),
    "x": (0, (-1, 0, 1), -1),
    "y": (1, (-1, 0, 1), -1),
    "z": (2, (-1, 0, 1), -1),
}

FACE_TURNS = [f + s for f in "URFDLB" for s in ("", "'", "2")]


def _rotate(v: Vec, axis: int, q: int) -> Vec:
    """Rotate integer vector ``v`` by ``q`` quarter turns (counter-clockwise, right-hand rule)."""
    q %= 4
    cos = (1, 0, -1, 0)[q]
    sin = (0, 1, 0, -1)[q]
    x, y, z = v
    if axis == 0:
        return (x, y * cos - z * sin, y * sin + z * cos)
    if axis == 1:
        return (x * cos + z * sin, y, -x * sin + z * cos)
    return (x * cos - y * sin, x * sin + y * cos, z)


def split_move(move: str) -> tuple[str, int]:
    """``"R2"`` -> ``("R", 2)``; ``"U'"`` -> ``("U", 3)``. Amount is in clockwise quarter turns."""
    if not move or move[0] not in BASE_MOVES:
        raise ValueError(f"unknown move {move!r}")
    suffix = move[1:]
    amount = {"": 1, "'": 3, "2": 2, "2'": 2, "'2": 2}.get(suffix)
    if amount is None:
        raise ValueError(f"unknown move {move!r}")
    return move[0], amount


def join_move(base: str, amount: int) -> str | None:
    amount %= 4
    return {0: None, 1: base, 2: base + "2", 3: base + "'"}[amount]


@lru_cache(maxsize=None)
def permutation(move: str) -> tuple[int, ...]:
    """perm such that ``new[j] = old[perm[j]]``."""
    base, amount = split_move(move)
    axis, layers, q = BASE_MOVES[base]
    q *= amount
    perm = list(range(54))
    for i, (pos, normal) in enumerate(GEOMETRY):
        if pos[axis] in layers:
            j = _INDEX_OF[(_rotate(pos, axis, q), _rotate(normal, axis, q))]
            perm[j] = i
    return tuple(perm)


@lru_cache(maxsize=None)
def _getter(move: str) -> itemgetter:
    return itemgetter(*permutation(move))


def parse(alg: str | Iterable[str]) -> list[str]:
    """Split an algorithm string into validated move tokens."""
    tokens = alg.split() if isinstance(alg, str) else list(alg)
    for t in tokens:
        split_move(t)
    return tokens


def apply(state: Sequence[str], moves: str | Iterable[str]) -> tuple[str, ...]:
    s = tuple(state)
    for m in parse(moves):
        s = _getter(m)(s)
    return s


def invert(moves: str | Iterable[str]) -> list[str]:
    out = []
    for m in reversed(parse(moves)):
        base, amount = split_move(m)
        out.append(join_move(base, -amount))
    return out


def is_solved(state: Sequence[str]) -> bool:
    """Every face a single colour (whatever the cube's orientation)."""
    return all(len(set(state[9 * i : 9 * i + 9])) == 1 for i in range(6))


def to_string(state: Sequence[str]) -> str:
    return "".join(state)


def random_scramble(length: int = 25, rng: random.Random | None = None) -> list[str]:
    rng = rng or random
    moves: list[str] = []
    last = ""
    for _ in range(length):
        face = rng.choice([f for f in "URFDLB" if f != last])
        moves.append(face + rng.choice(["", "'", "2"]))
        last = face
    return moves


def simplify(moves: Iterable[str]) -> list[str]:
    """Merge adjacent moves of the same base (``U U`` -> ``U2``, ``U U'`` -> nothing)."""
    out: list[tuple[str, int]] = []
    for m in moves:
        base, amount = split_move(m)
        if out and out[-1][0] == base:
            total = (out[-1][1] + amount) % 4
            out.pop()
            if total:
                out.append((base, total))
        else:
            out.append((base, amount))
    return [join_move(b, a) for b, a in out]  # type: ignore[misc]


# Pieces in Kociemba order. Each tuple lists facelet indices; the first is the U/D sticker.
def _idx(name: str) -> int:
    return 9 * FACES.index(name[0]) + int(name[1]) - 1


CORNERS: list[tuple[int, int, int]] = [
    tuple(_idx(n) for n in c)  # type: ignore[misc]
    for c in (
        ("U9", "R1", "F3"),
        ("U7", "F1", "L3"),
        ("U1", "L1", "B3"),
        ("U3", "B1", "R3"),
        ("D3", "F9", "R7"),
        ("D1", "L9", "F7"),
        ("D7", "B9", "L7"),
        ("D9", "R9", "B7"),
    )
]
CORNER_NAMES = ["URF", "UFL", "ULB", "UBR", "DFR", "DLF", "DBL", "DRB"]

EDGES: list[tuple[int, int]] = [
    tuple(_idx(n) for n in e)  # type: ignore[misc]
    for e in (
        ("U6", "R2"),
        ("U8", "F2"),
        ("U4", "L2"),
        ("U2", "B2"),
        ("D6", "R8"),
        ("D2", "F8"),
        ("D4", "L8"),
        ("D8", "B8"),
        ("F6", "R4"),
        ("F4", "L6"),
        ("B6", "L4"),
        ("B4", "R6"),
    )
]
EDGE_NAMES = ["UR", "UF", "UL", "UB", "DR", "DF", "DL", "DB", "FR", "FL", "BL", "BR"]
