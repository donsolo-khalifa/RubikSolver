"""Stages shared by the Beginner and Intermediate methods (daisy to middle layer),
plus the goal checks every layer-by-layer stage uses.

All checks assume the orientation after the opening ``z2``: white centre on the
bottom (D), yellow centre on top (U). Later stages only add ``y`` rotations, so
that stays true. Colours are read from the centres, never assumed.
"""
from __future__ import annotations

from ..algorithms import CORNER_INSERT, EDGE_LEFT, EDGE_RIGHT
from ..base import SolveError
from ..cube_model import FACE_TURNS, apply
from ..search import AUF, Y_ROTATIONS, find_setup, iddfs
from ..stage_engine import Builder, StageDef

State = tuple[str, ...]

U_C, R_C, F_C, D_C, L_C, B_C = 4, 13, 22, 31, 40, 49

# (top sticker, side sticker, side centre)
TOP_EDGES = [(7, 19, F_C), (5, 10, R_C), (1, 46, B_C), (3, 37, L_C)]
# (bottom sticker, side sticker, side centre)
BOTTOM_EDGES = [(28, 25, F_C), (32, 16, R_C), (34, 52, B_C), (30, 43, L_C)]
# (sticker, centre, sticker, centre)
MIDDLE_EDGES = [(23, F_C, 12, R_C), (21, F_C, 41, L_C), (50, B_C, 39, L_C), (48, B_C, 14, R_C)]
# (bottom sticker, side a, centre a, side b, centre b); DFR first
BOTTOM_CORNERS = [
    (29, 26, F_C, 15, R_C),
    (27, 44, L_C, 24, F_C),
    (33, 53, B_C, 42, L_C),
    (35, 17, R_C, 51, B_C),
]
# (top sticker, side a, centre a, side b, centre b); URF first
TOP_CORNERS = [
    (8, 9, R_C, 20, F_C),
    (6, 18, F_C, 38, L_C),
    (0, 36, L_C, 47, B_C),
    (2, 45, B_C, 11, R_C),
]


# --- goal checks --------------------------------------------------------------
def petals(s: State) -> int:
    return sum(s[t] == s[D_C] for t, _, _ in TOP_EDGES)


def cross_done(s: State) -> bool:
    return all(s[d] == s[D_C] and s[x] == s[c] for d, x, c in BOTTOM_EDGES)


def bottom_corner_ok(s: State, k: int) -> bool:
    d, a, ca, b, cb = BOTTOM_CORNERS[k]
    return s[d] == s[D_C] and s[a] == s[ca] and s[b] == s[cb]


def first_layer_done(s: State) -> bool:
    return cross_done(s) and all(bottom_corner_ok(s, k) for k in range(4))


def middle_edge_ok(s: State, k: int) -> bool:
    a, ca, b, cb = MIDDLE_EDGES[k]
    return s[a] == s[ca] and s[b] == s[cb]


def f2l_done(s: State) -> bool:
    return first_layer_done(s) and all(middle_edge_ok(s, k) for k in range(4))


def top_cross(s: State) -> bool:
    return all(s[t] == s[U_C] for t, _, _ in TOP_EDGES)


def yellow_cross_done(s: State) -> bool:
    return f2l_done(s) and top_cross(s)


def top_edges_matched(s: State) -> bool:
    return all(s[x] == s[c] for _, x, c in TOP_EDGES)


def top_face_done(s: State) -> bool:
    return f2l_done(s) and all(s[i] == s[U_C] for i in range(9))


def top_corners_placed(s: State) -> bool:
    """Each top corner sits in its own spot (it may still be twisted)."""
    return all(
        {s[t], s[a], s[b]} == {s[U_C], s[ca], s[cb]} for t, a, ca, b, cb in TOP_CORNERS
    )


# --- shared stages ------------------------------------------------------------
def _daisy(b: Builder) -> None:
    b.setup("z2")
    if cross_done(b.state):
        return  # the cross is already there: nothing to do in this stage or the next
    for k in range(1, 5):
        # One petal at a time keeps the search shallow.
        path = iddfs(b.state, lambda s, k=k: petals(s) >= k, FACE_TURNS, 6)
        if path is None:
            raise SolveError("daisy search failed")
        b.setup(path)


def _white_cross(b: Builder) -> None:
    faces = {F_C: "F", R_C: "R", B_C: "B", L_C: "L"}
    if cross_done(b.state):
        return
    for _ in range(4):
        s = b.state
        for auf in AUF:
            s2 = apply(s, auf)
            match = next(
                (c for t, x, c in TOP_EDGES if s2[t] == s2[D_C] and s2[x] == s2[c]), None
            )
            if match is not None:
                b.setup(auf)
                b.setup(faces[match] + "2")
                break
        else:
            raise SolveError("no petal could be matched")


def _reps_to_insert(s: State) -> int:
    for n in range(6):
        if bottom_corner_ok(s, 0):
            return n
        s = apply(s, CORNER_INSERT.moves)
    return 6


def _white_corners(b: Builder) -> None:
    for _ in range(12):
        s = b.state
        if first_layer_done(s):
            return
        white = s[D_C]

        def above_slot(s: State) -> bool:
            # URF holds the white corner that belongs in DFR
            return {s[8], s[9], s[20]} == {white, s[F_C], s[R_C]}

        # Of the corners that can go in now, take the one needing the fewest repetitions.
        best: tuple[int, str] | None = None
        for rot in Y_ROTATIONS:
            for auf in AUF:
                setup = f"{rot} {auf}"
                s2 = apply(s, setup)
                if above_slot(s2):
                    reps = _reps_to_insert(s2)
                    if best is None or reps < best[0]:
                        best = (reps, setup)
        if best is not None:
            b.setup(best[1])
            b.repeat(CORNER_INSERT, lambda s: bottom_corner_ok(s, 0), 6)
        else:
            # A white corner is stuck in the bottom layer: lift it out once.
            rot = find_setup(s, Y_ROTATIONS, lambda s: not bottom_corner_ok(s, 0))
            b.setup(rot)
            b.alg(CORNER_INSERT)
    raise SolveError("white corners did not finish")


def _middle_layer(b: Builder) -> None:
    for _ in range(12):
        s = b.state
        if f2l_done(s):
            return
        yellow = s[U_C]

        def at_front(s: State) -> bool:
            # UF edge without yellow, its front colour matching the front centre
            return s[19] == s[F_C] and s[7] != yellow and s[19] != yellow

        setup = next(
            (rot + " " + auf for rot in Y_ROTATIONS for auf in AUF
             if at_front(apply(s, rot + " " + auf))),
            None,
        )
        if setup is not None:
            b.setup(setup)
            s = b.state
            if s[7] == s[R_C]:
                b.alg(EDGE_RIGHT)
            elif s[7] == s[L_C]:
                b.alg(EDGE_LEFT)
            else:
                raise SolveError("middle edge colours do not match any slot")
        else:
            # An edge is stuck in the middle layer the wrong way: pop it out.
            rot = find_setup(s, Y_ROTATIONS, lambda s: not middle_edge_ok(s, 0))
            b.setup(rot)
            b.alg(EDGE_RIGHT)
    raise SolveError("middle layer did not finish")


DAISY = StageDef(
    name="Daisy",
    goal="Put the 4 {first} edge pieces around the {last} centre on top, like petals of a flower",
    explanation=(
        "First, turn the whole cube upside down so {last} is on top and {first} on the bottom. "
        "Then bring each {first} edge piece up so its {first} sticker faces up next to the {last} centre. "
        "Before you bring up a new petal, turn the top so an empty spot is above it, so you don't knock "
        "an existing petal off."
    ),
    run=_daisy,
    check=lambda s: petals(s) == 4 or cross_done(s),
    tips=["Only the edge pieces matter here (the ones with two colours).",
          "It's fine if the rest of the cube gets messier."],
)

WHITE_CROSS = StageDef(
    name="{First} cross",
    goal="Make a {first} plus sign on the bottom, with each edge matching the side centre",
    explanation=(
        "Look at a petal's side sticker. Turn the top until that sticker sits above the centre of "
        "the same colour, then turn that side twice so the petal flips down to the bottom."
    ),
    run=_white_cross,
    check=cross_done,
    tips=["Each side's two-colour edge should now line up with its centre, like a T."],
)

WHITE_CORNERS = StageDef(
    name="{First} corners",
    goal="Complete the whole {first} layer on the bottom",
    explanation=(
        "Find a corner with {first} on top. Turn the whole cube so the slot it belongs in is at the "
        "front-right bottom, turn the top so the corner is right above that slot, then repeat "
        "R U R' U' until it drops in with {first} facing down (1, 3 or 5 times)."
    ),
    run=_white_corners,
    check=first_layer_done,
    algorithm=CORNER_INSERT.name,
    tips=["If a {first} corner is stuck in the bottom in the wrong place, do R U R' U' once to lift it out."],
)

MIDDLE_LAYER = StageDef(
    name="Middle layer",
    goal="Fill in the 4 edges of the middle layer",
    explanation=(
        "Find a top edge with no {last} on it. Turn the cube and the top so its front sticker "
        "matches the front centre, making an upside-down T. If its top sticker matches the right "
        "centre, use the right algorithm; if it matches the left, use the left one."
    ),
    run=_middle_layer,
    check=f2l_done,
    algorithm=f"{EDGE_RIGHT.name} / {EDGE_LEFT.name}",
    tips=["If an edge is in the middle layer but flipped or in the wrong slot, put it at front-right "
          "and do the right algorithm once to take it out."],
)

FIRST_TWO_LAYERS = [DAISY, WHITE_CROSS, WHITE_CORNERS, MIDDLE_LAYER]
