"""Named algorithms used by the Beginner and Intermediate methods."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Algorithm:
    name: str
    moves: str
    description: str


def _a(name: str, moves: str, description: str) -> Algorithm:
    return Algorithm(name, moves, description)


# --- Beginner -----------------------------------------------------------------
CORNER_INSERT = _a(
    "R U R' U'",
    "R U R' U'",
    "The 'sexy move'. Repeat it with the corner above its slot until the corner drops in, white side down.",
)
EDGE_RIGHT = _a(
    "Middle edge right",
    "U R U' R' U' F' U F",
    "Moves the front-top edge down into the slot on the right.",
)
EDGE_LEFT = _a(
    "Middle edge left",
    "U' L' U L U F U' F'",
    "Moves the front-top edge down into the slot on the left.",
)
YELLOW_CROSS = _a(
    "F R U R' U' F'",
    "F R U R' U' F'",
    "Flips top edges. Dot becomes an L, an L at back-left becomes a line, a flat line becomes the cross.",
)
SUNE = _a(
    "Sune",
    "R U R' U R U2 R'",
    "Swaps top edges around. Hold two correct neighbouring edges at the back and the right.",
)
CORNER_CYCLE = _a(
    "Corner cycle",
    "U R U' L' U R' U' L",
    "Cycles three top corners, leaving the front-right one where it is.",
)
CORNER_TWIST = _a(
    "R' D' R D",
    "R' D' R D",
    "Twists the front-right top corner. Repeat until yellow is on top.",
)

# --- Intermediate: 2-look OLL -------------------------------------------------
OLL_LINE = _a("OLL line", "F R U R' U' F'", "Hold the line horizontally (left to right).")
OLL_L = _a("OLL L-shape", "f R U R' U' f'", "Hold the L at the back and the left.")

OLL_CORNERS = [
    _a("Sune", "R U R' U R U2 R'", "One corner yellow; put it at front-left."),
    _a("Antisune", "R U2 R' U' R U' R'", "One corner yellow; put it at front-right."),
    _a("H", "R U R' U R U' R' U R U2 R'", "No corners yellow, two yellow stickers facing left and right."),
    _a("Pi", "R U2 R2 U' R2 U' R2 U2 R", "No corners yellow, yellow stickers on the left facing out."),
    _a("Headlights", "R2 D R' U2 R D' R' U2 R'", "Two corners yellow at the back; headlights facing you."),
    _a("T", "r U R' U' r' F R F'", "Two corners yellow on the left, sides facing front and back."),
    _a("Bowtie", "F' r U R' U' r' F R", "Two diagonal corners yellow; front-left corner's yellow faces left."),
]

# --- Intermediate: 2-look PLL -------------------------------------------------
PLL_CORNERS = [
    _a("T-perm", "R U R' U' R' F R2 U' R' U' R U R' F'", "Headlights (matching corners) on the left."),
    _a("Y-perm", "F R U' R' U' R U R' F' R U R' U' R' F R F'", "No headlights: diagonal corner swap."),
]
PLL_EDGES = [
    _a("Ua-perm", "R U' R U R U R U' R' U' R2", "Solved side at the back; edges cycle anticlockwise."),
    _a("Ub-perm", "R2 U R U R' U' R' U' R' U R'", "Solved side at the back; edges cycle clockwise."),
    _a("H-perm", "M2 U M2 U2 M2 U M2", "Opposite edges swapped on both axes."),
    _a("Z-perm", "M' U M2 U M2 U M' U2 M2", "Neighbouring edges swapped in pairs."),
]

ALL_ALGORITHMS = [
    CORNER_INSERT, EDGE_RIGHT, EDGE_LEFT, YELLOW_CROSS, SUNE, CORNER_CYCLE, CORNER_TWIST,
    OLL_LINE, OLL_L, *OLL_CORNERS, *PLL_CORNERS, *PLL_EDGES,
]
