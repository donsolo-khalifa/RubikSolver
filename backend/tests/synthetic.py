"""Render synthetic camera frames of a cube face, for end-to-end tests without a real cube."""
from __future__ import annotations

import cv2
import numpy as np

from app.vision.color import load_references, DEFAULT_COLORS_FILE


def lab_to_bgr(lab) -> tuple[int, int, int]:
    px = np.uint8([[np.clip(lab, 0, 255)]])
    return tuple(int(v) for v in cv2.cvtColor(px, cv2.COLOR_LAB2BGR)[0, 0])


def render_face(colors: list[str], angle: float = 5.0, size: int = 300, rng: np.random.Generator | None = None,
                frame: tuple[int, int] = (1280, 720), center: tuple[int, int] | None = None) -> np.ndarray:
    """A face of 9 stickers on a black body over a textured light background."""
    rng = rng or np.random.default_rng(0)
    refs = load_references(DEFAULT_COLORS_FILE)
    w, h = frame
    img = np.full((h, w, 3), (150, 170, 190), np.uint8)
    # Wood-grain-ish stripes, so the detector has background clutter to reject.
    for x in range(0, w, 23):
        cv2.line(img, (x, 0), (x + 60, h), (120, 140, 165), 2)
    cx, cy = center or (w // 2, h // 2)
    body = cv2.boxPoints(((cx, cy), (size, size), angle))
    cv2.fillConvexPoly(img, np.int32(body), (20, 20, 22))
    t = np.deg2rad(angle)
    u, v = np.array([np.cos(t), np.sin(t)]), np.array([-np.sin(t), np.cos(t)])
    cell = size / 3
    for i, c in enumerate(colors):
        r, k = divmod(i, 3)
        p = np.array([cx, cy]) + cell * ((k - 1) * u + (r - 1) * v)
        box = cv2.boxPoints(((p[0], p[1]), (cell * 0.86, cell * 0.86), angle))
        cv2.fillConvexPoly(img, np.int32(box), lab_to_bgr(refs[c] + rng.normal(0, 3, 3)))
    noise = rng.normal(0, 3, img.shape)
    return np.clip(img + noise, 0, 255).astype(np.uint8)
