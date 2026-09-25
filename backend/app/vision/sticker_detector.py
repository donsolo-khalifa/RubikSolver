"""Find sticker-shaped contours in a frame (PLAN.md 5.2)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .. import config


@dataclass
class Candidate:
    center: np.ndarray  # (x, y) in full-resolution pixels
    size: float         # side length in full-resolution pixels
    angle: float        # minAreaRect angle in degrees
    area: float
    box: np.ndarray     # 4x2 rotated-rect corners, full resolution


@dataclass
class StickerResult:
    candidates: list[Candidate]
    scale: float                  # full-res pixels per detection pixel
    debug: dict[str, np.ndarray]  # intermediate images at detection resolution


def _preprocess(small: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 7, 40, 7)
    edges = cv2.Canny(blur, 20, 50)
    edges = cv2.dilate(edges, np.ones((3, 3), np.uint8), iterations=1)
    return gray, edges


def _bright_mask(small: np.ndarray) -> np.ndarray:
    """Pixels clearly brighter than the black cube body."""
    v = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)[:, :, 2]
    mask = (cv2.GaussianBlur(v, (5, 5), 0) > config.BODY_MAX_V).astype(np.uint8) * 255
    return cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))


def detect_stickers(frame: np.ndarray, want_debug: bool = False) -> StickerResult:
    h, w = frame.shape[:2]
    scale = w / config.DETECT_WIDTH
    small = cv2.resize(frame, (config.DETECT_WIDTH, round(h / scale)), interpolation=cv2.INTER_AREA)
    _, edges = _preprocess(small)
    bright = _bright_mask(small)

    # Two sources of sticker outlines: Canny edges (crisp frames), and bright blobs enclosed by
    # the black cube body (still works when motion blur breaks the edges).
    contours = list(cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)[0])
    contours += list(cv2.findContours(bright, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)[0])
    sw = config.DETECT_WIDTH
    min_side, max_side = config.MIN_STICKER_FRAC * sw, config.MAX_STICKER_FRAC * sw
    lo_ar, hi_ar = config.ASPECT_RANGE

    raw: list[Candidate] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_side**2 * 0.8 or area > max_side**2:
            continue
        (cx, cy), (rw, rh), angle = cv2.minAreaRect(cnt)
        if rw == 0 or rh == 0 or not lo_ar <= rw / rh <= hi_ar:
            continue
        if area / (rw * rh) < config.MIN_FILL_RATIO:
            continue
        hull_area = cv2.contourArea(cv2.convexHull(cnt))
        if hull_area == 0 or area / hull_area < 0.93:  # "convex", allowing for pixel noise
            continue
        side = float(np.sqrt(rw * rh))
        if not min_side <= side <= max_side:
            continue
        box = cv2.boxPoints(((cx, cy), (rw, rh), angle))
        raw.append(Candidate(np.array([cx, cy]) * scale, side * scale, angle, area * scale**2, box * scale))

    # Filter by the median area before de-duplicating, so the whole-face outline (which shares
    # its centre with the centre sticker) can't knock the centre sticker out.
    cands = raw
    if cands:
        med = float(np.median([c.area for c in _dedupe(raw)]))
        tol = config.AREA_TOLERANCE
        cands = [c for c in cands if (1 - tol) * med <= c.area <= (1 + tol) * med]
    cands = _dedupe(cands)

    debug: dict[str, np.ndarray] = {}
    if want_debug:
        debug["small"] = small
        debug["edges"] = cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
        debug["bright"] = cv2.cvtColor(bright, cv2.COLOR_GRAY2BGR)
        raw_img = small.copy()
        for c in raw:
            cv2.drawContours(raw_img, [np.int32(c.box / scale)], 0, (255, 0, 255), 1)
        debug["candidates"] = raw_img
        kept = small.copy()
        for c in cands:
            cv2.drawContours(kept, [np.int32(c.box / scale)], 0, (0, 255, 0), 2)
        debug["stickers"] = kept
    return StickerResult(cands, scale, debug)


def _dedupe(cands: list[Candidate]) -> list[Candidate]:
    """Inner and outer edges of one sticker both make contours; keep the larger one of each cluster."""
    out: list[Candidate] = []
    for c in sorted(cands, key=lambda c: -c.area):
        if all(np.linalg.norm(c.center - o.center) > 0.3 * max(c.size, o.size) for o in out):
            out.append(c)
    return out
