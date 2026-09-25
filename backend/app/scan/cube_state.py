"""Facelet strings from scanned faces, and checks that the scan is a real cube (PLAN.md 6.4)."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from itertools import product

from ..solver.cube_model import CORNERS, EDGES, FACES

COLORS = "WYROGB"
COLOR_NAMES = {"W": "white", "Y": "yellow", "R": "red", "O": "orange", "G": "green", "B": "blue"}
# Standard colour scheme with the cube held white on top, green facing the camera.
SCHEME = {"U": "W", "R": "R", "F": "G", "D": "Y", "L": "O", "B": "B"}
FACE_NAMES = {"U": "top", "R": "right", "F": "front", "D": "bottom", "L": "left", "B": "back"}


def rotate_face(colors: list[str], quarter_turns: int) -> list[str]:
    """Rotate a 3x3 face (row-major) clockwise by ``quarter_turns``."""
    out = list(colors)
    for _ in range(quarter_turns % 4):
        out = [out[6 - 3 * (i % 3) + i // 3] for i in range(9)]
    return out


def faces_to_facelets(faces: dict[str, list[str]]) -> str:
    """Colour letters per face -> URFDLB facelet string (faces named by centre colour)."""
    centre_face = {faces[f][4]: f for f in FACES}
    return "".join(centre_face.get(c, "?") for f in FACES for c in faces[f])


def facelets_to_colors(facelets: str, faces: dict[str, list[str]] | None = None) -> str:
    scheme = {f: faces[f][4] for f in FACES} if faces else SCHEME
    return "".join(scheme[c] for c in facelets)


def _desc(facelets: str, idx: tuple[int, ...]) -> str:
    return ", ".join(COLOR_NAMES.get(SCHEME.get(facelets[i], "?"), "?") for i in idx)


def _where(idx: tuple[int, ...]) -> str:
    return " / ".join(FACE_NAMES[FACES[i // 9]] for i in idx)


def validate(facelets: str) -> list[str]:
    """Return a list of human-readable problems; empty means the cube is solvable."""
    errors: list[str] = []
    if len(facelets) != 54:
        return ["The scan does not have 54 stickers."]
    counts = Counter(facelets)
    centres = [facelets[9 * i + 4] for i in range(6)]
    if len(set(centres)) != 6:
        return ["Two faces have the same centre colour. Rescan the faces."]
    for f in FACES:
        n = counts.get(f, 0)
        if n != 9:
            name = COLOR_NAMES[SCHEME[f]]
            errors.append(f"There are {n} {name} stickers instead of 9.")
    if "?" in facelets:
        errors.append("Some stickers were not recognised.")
    if errors:
        return errors

    opposite = {"U": "D", "D": "U", "R": "L", "L": "R", "F": "B", "B": "F"}
    corner_pieces = [(FACES[c[0] // 9], FACES[c[1] // 9], FACES[c[2] // 9]) for c in CORNERS]
    edge_pieces = [(FACES[e[0] // 9], FACES[e[1] // 9]) for e in EDGES]

    cp, co, ep, eo = [], [], [], []
    for pos, idx in enumerate(CORNERS):
        cols = tuple(facelets[i] for i in idx)
        ori = next((k for k in range(3) if cols[k] in "UD"), None)
        found = None
        if ori is not None:
            c1, c2 = cols[(ori + 1) % 3], cols[(ori + 2) % 3]
            found = next((j for j, p in enumerate(corner_pieces) if p[1] == c1 and p[2] == c2), None)
        if found is None:
            errors.append(
                f"The corner on the {_where(idx)} faces ({_desc(facelets, idx)}) "
                "is not a real corner. Check those faces."
            )
            continue
        cp.append(found)
        co.append(ori)
    for pos, idx in enumerate(EDGES):
        a, b = facelets[idx[0]], facelets[idx[1]]
        if a == b or opposite[a] == b:
            errors.append(
                f"The edge on the {_where(idx)} faces ({_desc(facelets, idx)}) "
                "is not a real edge. Check those faces."
            )
            continue
        if (a, b) in edge_pieces:
            ep.append(edge_pieces.index((a, b)))
            eo.append(0)
        else:
            ep.append(edge_pieces.index((b, a)))
            eo.append(1)
    if errors:
        return errors
    if len(set(cp)) != 8:
        errors.append("The same corner appears twice. A face was probably scanned wrongly.")
    if len(set(ep)) != 12:
        errors.append("The same edge appears twice. A face was probably scanned wrongly.")
    if errors:
        return errors
    if sum(co) % 3:
        errors.append("One corner is twisted. Check the colours near the corners, or rescan the top and bottom.")
    if sum(eo) % 2:
        errors.append("One edge is flipped. Check the edge stickers, or rescan the top and bottom.")
    if _parity(cp) != _parity(ep):
        errors.append("Two pieces are swapped. A face was probably held at the wrong angle; rescan it.")
    return errors


def _parity(perm: list[int]) -> int:
    p, seen = 0, [False] * len(perm)
    for i in range(len(perm)):
        if not seen[i]:
            j, n = i, 0
            while not seen[j]:
                seen[j] = True
                j = perm[j]
                n += 1
            p += n - 1
    return p % 2


@dataclass
class ScanResult:
    facelets: str
    errors: list[str]
    faces: dict[str, list[str]]
    note: str | None = None
    valid: bool = field(init=False)

    def __post_init__(self) -> None:
        self.valid = not self.errors


def check_scan(faces: dict[str, list[str]]) -> ScanResult:
    """Validate; if invalid, try the other rotations of the U and D scans (most often held wrong)."""
    facelets = faces_to_facelets(faces)
    errors = validate(facelets)
    if not errors:
        return ScanResult(facelets, [], faces)
    for ru, rd in product(range(4), range(4)):
        if ru == rd == 0:
            continue
        trial = dict(faces, U=rotate_face(faces["U"], ru), D=rotate_face(faces["D"], rd))
        f2 = faces_to_facelets(trial)
        if not validate(f2):
            which = [n for n, r in (("top", ru), ("bottom", rd)) if r]
            note = f"The {' and '.join(which)} scan was held at a different angle; corrected automatically."
            return ScanResult(f2, [], trial, note)
    return ScanResult(facelets, errors, faces)
