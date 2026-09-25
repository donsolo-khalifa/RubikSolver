"""Multi-frame smoothing and the "held steady" test (PLAN.md 5.7)."""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass

import numpy as np

from .. import config
from .pipeline import Detection


@dataclass
class Stability:
    stable: bool
    hint: str | None
    labs: np.ndarray | None        # per-sticker median LAB over the stable window (9x3)
    colors: list[str | None] | None


class Stabilizer:
    def __init__(self, n: int = config.STABLE_FRAMES):
        self.window: deque[Detection] = deque(maxlen=n)

    def reset(self) -> None:
        self.window.clear()

    def update(self, det: Detection) -> Stability:
        if not det.found:
            self.window.clear()
            return Stability(False, det.hint, None, None)
        self.window.append(det)
        hint = det.hint
        if hint in ("too_far", "too_close", "occluded", "glare"):
            return Stability(False, hint, None, det.colors)
        if det.sharpness < config.MIN_SHARPNESS:
            return Stability(False, "hold_still", None, det.colors)
        if len(self.window) < self.window.maxlen:
            return Stability(False, None, None, det.colors)

        origins = np.array([d.fit.origin for d in self.window])
        spacing = float(np.median([d.fit.spacing for d in self.window]))
        moved = float(np.max(np.linalg.norm(origins - origins.mean(axis=0), axis=1)))
        if moved > config.MAX_CENTRE_MOVE * spacing:
            return Stability(False, "hold_still", None, det.colors)
        if any(d.colors != det.colors for d in self.window):
            return Stability(False, "hold_still", None, det.colors)
        labs = np.median(np.array([d.labs for d in self.window]), axis=0)
        return Stability(True, None, labs, det.colors)
