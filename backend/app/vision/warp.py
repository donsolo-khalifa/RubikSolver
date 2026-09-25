"""Homography from the fitted grid, and the flat 300x300 face (PLAN.md 5.4)."""
from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .lattice import GridFit

WARP_SIZE = 300
CELL = WARP_SIZE // 3
WARP_CORNERS = np.float32([[0, 0], [WARP_SIZE, 0], [WARP_SIZE, WARP_SIZE], [0, WARP_SIZE]]).reshape(-1, 1, 2)


def cell_center(r: int, c: int) -> tuple[float, float]:
    return (CELL / 2 + CELL * c, CELL / 2 + CELL * r)


@dataclass
class Warp:
    H: np.ndarray        # image -> warp
    face: np.ndarray     # 300x300 BGR
    outline: np.ndarray  # 4x2 face corners in image pixels
    cell_points: np.ndarray  # 9x2 predicted sticker centres in image pixels (row-major)


def compute_homography(fit: GridFit) -> np.ndarray | None:
    keys = sorted(fit.cells)
    img_pts = np.float32([fit.cells[k].center for k in keys])
    warp_pts = np.float32([cell_center(r, c) for r, c in keys])
    if len(keys) < 4:
        return None
    H, _ = cv2.findHomography(img_pts, warp_pts, cv2.RANSAC, 5.0 * (fit.spacing / CELL))
    if H is None:
        return None
    return H


def warp_face(frame: np.ndarray, fit: GridFit) -> Warp | None:
    H = compute_homography(fit)
    if H is None:
        return None
    try:
        Hinv = np.linalg.inv(H)
    except np.linalg.LinAlgError:
        return None
    face = cv2.warpPerspective(frame, H, (WARP_SIZE, WARP_SIZE))
    outline = cv2.perspectiveTransform(WARP_CORNERS, Hinv).reshape(4, 2)
    centres = np.float32([cell_center(i // 3, i % 3) for i in range(9)]).reshape(-1, 1, 2)
    cell_points = cv2.perspectiveTransform(centres, Hinv).reshape(9, 2)
    return Warp(H, face, outline, cell_points)
