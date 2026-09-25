"""Plain-language descriptions of moves ("R'" -> "Turn the right face anticlockwise")."""
from __future__ import annotations

from .cube_model import split_move

FACE_NAME = {"U": "top", "D": "bottom", "R": "right", "L": "left", "F": "front", "B": "back"}

SLICE = {
    "M": ("middle layer (between left and right)", "L", {1: "down", 3: "up"}),
    "E": ("middle horizontal layer", "D", {1: "to the right", 3: "to the left"}),
    "S": ("middle layer (between front and back)", "F", {1: "clockwise", 3: "anticlockwise"}),
}

ROTATION = {
    "x": {
        1: "Tip the whole cube back, so the front face goes to the top",
        3: "Tip the whole cube forward, so the top face comes to the front",
        2: "Flip the whole cube over, top away from you",
    },
    "y": {
        1: "Turn the whole cube to the left, so the right face comes to the front",
        3: "Turn the whole cube to the right, so the left face comes to the front",
        2: "Turn the whole cube around, so the back face comes to the front",
    },
    "z": {
        1: "Tilt the whole cube to the right (clockwise as seen from the front)",
        3: "Tilt the whole cube to the left (anticlockwise as seen from the front)",
        2: "Turn the whole cube upside down, keeping the front facing you",
    },
}


def _direction(amount: int) -> str:
    return {1: "clockwise", 3: "anticlockwise", 2: "twice (a half turn)"}[amount]


def describe(move: str) -> str:
    base, amount = split_move(move)
    if base in FACE_NAME:
        return f"Turn the {FACE_NAME[base]} face {_direction(amount)} ({move})"
    if base.upper() in FACE_NAME:
        return f"Turn the {FACE_NAME[base.upper()]} two layers {_direction(amount)} ({move})"
    if base in SLICE:
        layer, like, dirs = SLICE[base]
        if amount == 2:
            return f"Turn the {layer} twice ({move})"
        like_move = like if amount == 1 else like + "'"
        return f"Turn the {layer} {dirs[amount]}, the same way as {like_move} ({move})"
    return f"{ROTATION[base][amount]} ({move})"
