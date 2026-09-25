"""One call per frame: stickers -> grid -> warp -> colours, plus the overlay drawing."""
from __future__ import annotations

from dataclasses import dataclass, field

import cv2
import numpy as np

from .. import config
from .color import classify, load_references
from .grid import sample_cells, sharpness
from .lattice import GridFit, fit_grid
from .sticker_detector import detect_stickers
from .warp import Warp, warp_face

# BGR colours for drawing each sticker colour on the overlay
DRAW = {
    "W": (255, 255, 255), "Y": (0, 230, 255), "R": (40, 40, 230),
    "O": (0, 140, 255), "G": (60, 200, 60), "B": (230, 120, 20),
}


@dataclass
class Detection:
    found: bool
    fit: GridFit | None = None
    warp: Warp | None = None
    labs: np.ndarray | None = None               # 9x3 LAB
    colors: list[str | None] = field(default_factory=lambda: [None] * 9)
    glare: list[bool] = field(default_factory=lambda: [False] * 9)
    sharpness: float = 0.0
    hint: str | None = None


class Pipeline:
    def __init__(self, refs: dict[str, np.ndarray] | None = None):
        self.refs = refs or load_references()

    def process(self, frame: np.ndarray) -> Detection:
        stickers = detect_stickers(frame)
        fit = fit_grid(stickers.candidates)
        if fit is None:
            return Detection(False)
        warp = warp_face(frame, fit)
        if warp is None:
            return Detection(False)
        samples = sample_cells(warp.face)
        labs = np.array([s.lab for s in samples])
        colors = classify(labs, self.refs)
        det = Detection(
            found=True, fit=fit, warp=warp, labs=labs, colors=colors,
            glare=[s.glare for s in samples], sharpness=sharpness(warp.face),
        )
        det.hint = _hint(det, frame.shape[1])
        return det


def _hint(det: Detection, width: int) -> str | None:
    assert det.fit is not None
    if det.fit.spacing < config.TOO_FAR_FRAC * width:
        return "too_far"
    if det.fit.spacing > config.TOO_CLOSE_FRAC * width:
        return "too_close"
    if any(det.glare):
        return "glare"
    if any(c is None for c in det.colors):
        return "occluded"
    return None


def annotate(frame: np.ndarray, det: Detection, stable: bool = False, target: str | None = None) -> np.ndarray:
    """Face outline, the 9 sample points coloured by classification, the centre highlighted."""
    out = frame.copy()
    if not det.found or det.warp is None:
        return out
    outline = np.int32(det.warp.outline)
    colour = (80, 220, 80) if stable else (0, 200, 255)
    cv2.polylines(out, [outline], True, colour, 3, cv2.LINE_AA)
    # Corner accents, in the style of cvzone.cornerRect, following the tilted outline.
    for i in range(4):
        p, a, b = outline[i], outline[(i + 1) % 4], outline[(i - 1) % 4]
        for q in (a, b):
            d = (q - p) * 0.18
            cv2.line(out, tuple(p), tuple(np.int32(p + d)), colour, 8, cv2.LINE_AA)
    r = max(6, int(det.fit.spacing * 0.12)) if det.fit else 8
    for i, (pt, c) in enumerate(zip(det.warp.cell_points, det.colors)):
        center = tuple(int(v) for v in pt)
        fill = DRAW.get(c or "", (60, 60, 60))
        cv2.circle(out, center, r, fill, -1, cv2.LINE_AA)
        cv2.circle(out, center, r, (0, 0, 0), 2, cv2.LINE_AA)
        if c is None:
            cv2.putText(out, "?", (center[0] - 6, center[1] + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if i == 4:
            ring = (255, 0, 255) if target and c != target else (255, 255, 255)
            cv2.circle(out, center, int(r * 1.9), ring, 3, cv2.LINE_AA)
    return out
