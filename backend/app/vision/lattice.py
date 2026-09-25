"""Fit a 3x3 grid to sticker candidates and find the centre sticker (PLAN.md 5.3).

Each candidate is tried as an anchor at each of the 9 cells; the anchor/cell pair that
places the most other candidates on grid points wins. Anchoring at every cell (not only
the centre) keeps the fit working when the centre sticker itself was not detected; the
homography then predicts where it is.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .. import config
from .sticker_detector import Candidate


@dataclass
class GridFit:
    cells: dict[tuple[int, int], Candidate]  # (row, col) in 0..2 -> candidate
    spacing: float                           # sticker size + gap, in pixels
    angle: float                             # grid rotation in degrees, within [-45, 45)
    u: np.ndarray                            # column direction (image right, roughly)
    v: np.ndarray                            # row direction (image down, roughly)
    origin: np.ndarray                       # predicted image position of the centre cell

    @property
    def center(self) -> Candidate | None:
        return self.cells.get((1, 1))

    @property
    def rows(self) -> set[int]:
        return {r for r, _ in self.cells}

    @property
    def cols(self) -> set[int]:
        return {c for _, c in self.cells}


def grid_angle(cands: list[Candidate]) -> float:
    """Dominant rotation of the candidates, modulo 90 degrees, as close to upright as possible."""
    # Average on the 4x-angle circle so 1 degree and 89 degrees count as neighbours.
    a = np.deg2rad([c.angle for c in cands]) * 4
    mean = np.arctan2(np.sin(a).mean(), np.cos(a).mean()) / 4
    deg = float(np.rad2deg(mean))
    return ((deg + 45) % 90) - 45


def fit_grid(cands: list[Candidate], angle: float | None = None) -> GridFit | None:
    if len(cands) < config.MIN_INLIERS:
        return None
    pts = np.array([c.center for c in cands], dtype=float)
    if angle is None:
        angle = grid_angle(cands)
    t = np.deg2rad(angle)
    u = np.array([np.cos(t), np.sin(t)])
    v = np.array([-np.sin(t), np.cos(t)])

    d = np.linalg.norm(pts[:, None] - pts[None], axis=2)
    np.fill_diagonal(d, np.inf)
    spacing = float(np.median(d.min(axis=1)))
    if spacing <= 0:
        return None

    best = None  # (count, -error), anchor index, anchor cell, cells
    for k0 in range(len(cands)):
        rel = pts - pts[k0]
        gi, gj = rel @ v / spacing, rel @ u / spacing
        ri, rj = np.round(gi), np.round(gj)
        err = np.hypot(gi - ri, gj - rj)
        for ar in range(3):
            for ac in range(3):
                cells: dict[tuple[int, int], tuple[float, int]] = {}
                for k in range(len(cands)):
                    r, c = int(ri[k]) + ar, int(rj[k]) + ac
                    if 0 <= r <= 2 and 0 <= c <= 2 and err[k] < config.MAX_ROUNDING_ERROR:
                        if (r, c) not in cells or err[k] < cells[(r, c)][0]:
                            cells[(r, c)] = (err[k], k)
                score = (len(cells), -sum(e for e, _ in cells.values()))
                if best is None or score > best[0]:
                    best = (score, k0, (ar, ac), cells)

    assert best is not None
    (n, _), k0, (ar, ac), cells = best
    origin = pts[k0] + spacing * ((1 - ar) * v + (1 - ac) * u)
    fit = GridFit(
        cells={key: cands[k] for key, (_, k) in cells.items()},
        spacing=spacing,
        angle=angle,
        u=u,
        v=v,
        origin=origin,
    )
    if n < config.MIN_INLIERS or len(fit.rows) < 2 or len(fit.cols) < 2:
        return None
    return fit
