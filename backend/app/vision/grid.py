"""Sample the 9 cells of the warped face (PLAN.md 5.5)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .. import config
from .warp import CELL


@dataclass
class CellSample:
    lab: np.ndarray  # median LAB (OpenCV 8-bit scale: L 0..255, a/b offset by 128)
    glare: bool


def sample_cells(face: np.ndarray) -> list[CellSample]:
    hsv = cv2.cvtColor(face, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(face, cv2.COLOR_BGR2LAB)
    inner = CELL // 4  # sample the inner ~50% of each cell
    out: list[CellSample] = []
    for i in range(9):
        r, c = divmod(i, 3)
        y0, x0 = r * CELL + inner, c * CELL + inner
        sl = (slice(y0, y0 + CELL - 2 * inner), slice(x0, x0 + CELL - 2 * inner))
        h = hsv[sl].reshape(-1, 3).astype(int)
        px = lab[sl].reshape(-1, 3)
        v_med = np.median(h[:, 2])
        # Glare: much brighter than the rest of the sticker and nearly colourless.
        # (A white sticker is bright everywhere, so it is not confused with glare.)
        glare_mask = (h[:, 1] < 60) & (h[:, 2] > 200) & (h[:, 2] > v_med + 25)
        frac = glare_mask.mean()
        keep = px[~glare_mask] if frac < 0.95 else px
        out.append(CellSample(np.median(keep, axis=0), bool(frac > config.GLARE_FRACTION)))
    return out


def sharpness(face: np.ndarray) -> float:
    gray = cv2.cvtColor(face, cv2.COLOR_BGR2GRAY)
    return float(cv2.Laplacian(gray, cv2.CV_64F).var())
