"""Colour classification (PLAN.md 5.6).

Stickers are compared in a feature space built from LAB where chroma *saturates*: the
hue direction always counts fully, but chroma magnitude only up to ``CHROMA_CAP``. A
sticker washed out by glare keeps its hue but loses chroma, so plain LAB distance calls
it white; here it stays next to its real colour, while true white (almost no chroma)
stays near zero. See the green top-right sticker in the reference photos.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment

from .. import config

COLORS = "WYROGB"
CHROMA_CAP = 30.0
CHROMA_SCALE = 60.0
L_WEIGHT = 0.5

DEFAULT_COLORS_FILE = Path(__file__).with_name("default_colors.json")


def feature(lab: np.ndarray) -> np.ndarray:
    """LAB (OpenCV 8-bit) -> classification feature. Works on (3,) or (N, 3)."""
    lab = np.asarray(lab, dtype=float)
    a, b = lab[..., 1] - 128.0, lab[..., 2] - 128.0
    c = np.hypot(a, b) + 1e-6
    g = CHROMA_SCALE * np.minimum(c, CHROMA_CAP) / CHROMA_CAP
    return np.stack([L_WEIGHT * lab[..., 0], g * a / c, g * b / c], axis=-1)


def distances(labs: np.ndarray, refs: dict[str, np.ndarray]) -> tuple[list[str], np.ndarray]:
    """Distance of each sample to each reference colour: (names, N x len(refs))."""
    names = list(refs)
    f = feature(np.asarray(labs))
    r = feature(np.array([refs[n] for n in names]))
    return names, np.linalg.norm(f[:, None, :] - r[None, :, :], axis=2)


def classify(labs: np.ndarray, refs: dict[str, np.ndarray]) -> list[str | None]:
    """Live, per-face: nearest reference colour, or None when nothing is close (occluded)."""
    names, d = distances(labs, refs)
    out: list[str | None] = []
    for row in d:
        k = int(np.argmin(row))
        out.append(names[k] if row[k] <= config.UNKNOWN_DISTANCE else None)
    return out


def assign_all(labs54: np.ndarray, centre_indices: list[int] | None = None) -> list[int]:
    """Final assignment of all 54 stickers so each centre colour gets exactly 9.

    Returns for each sticker the index (0..5) of the centre it matches, in the order of
    ``centre_indices`` (default: the six centres at 4, 13, 22, ...).
    """
    labs54 = np.asarray(labs54, dtype=float)
    centre_indices = centre_indices or [9 * i + 4 for i in range(6)]
    f = feature(labs54)
    cf = f[centre_indices]
    cost = np.linalg.norm(f[:, None, :] - cf[None, :, :], axis=2)  # 54 x 6
    cost = np.repeat(cost, 9, axis=1)                                 # 54 x 54
    # Centres must keep their own colour.
    for k, ci in enumerate(centre_indices):
        cost[ci, :] = 1e6
        cost[ci, 9 * k : 9 * k + 9] = 0
    rows, cols = linear_sum_assignment(cost)
    out = [0] * len(labs54)
    for r, c in zip(rows, cols):
        out[r] = c // 9
    return out


def load_references(path: Path | None = None) -> dict[str, np.ndarray]:
    """Calibrated colours if available, else the defaults measured on the reference photos."""
    for p in (path or config.COLORS_FILE, DEFAULT_COLORS_FILE):
        if p.exists():
            data = json.loads(p.read_text())
            return {c: np.array(data[c], dtype=float) for c in COLORS if c in data}
    raise FileNotFoundError("no colour references found")


def save_references(refs: dict[str, np.ndarray], path: Path | None = None) -> None:
    p = path or config.COLORS_FILE
    p.write_text(json.dumps({c: [round(float(x), 1) for x in v] for c, v in refs.items()}, indent=2))
