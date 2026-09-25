import random

import numpy as np

from app import protocol as P
from app.scan.cube_state import SCHEME, check_scan, rotate_face, validate
from app.scan.session import SCAN_STEPS, ScanSession
from app.solver import cube_model as cm
from app.vision.color import load_references, DEFAULT_COLORS_FILE
from app.vision.pipeline import Detection
from app.vision.stabilizer import Stability


def faces_of(facelets: str) -> dict[str, list[str]]:
    return {f: [SCHEME[c] for c in facelets[9 * i: 9 * i + 9]] for i, f in enumerate("URFDLB")}


def scrambled(seed=1) -> str:
    return cm.to_string(cm.apply(cm.SOLVED, cm.random_scramble(25, random.Random(seed))))


def swap(s: str, i: int, j: int) -> str:
    l = list(s)
    l[i], l[j] = l[j], l[i]
    return "".join(l)


# --- validation ---------------------------------------------------------------
def test_good_cube():
    assert validate(scrambled()) == []
    assert validate(cm.to_string(cm.SOLVED)) == []


def test_flipped_edge():
    s = swap(cm.to_string(cm.SOLVED), *cm.EDGES[0])
    assert any("flipped" in e for e in validate(s))


def test_twisted_corner():
    a, b, c = cm.CORNERS[0]
    l = list(cm.to_string(cm.SOLVED))
    l[a], l[b], l[c] = l[b], l[c], l[a]
    assert any("twisted" in e for e in validate("".join(l)))


def test_swapped_pieces():
    s = cm.to_string(cm.SOLVED)
    (a1, a2), (b1, b2) = cm.EDGES[0], cm.EDGES[1]
    s = swap(swap(s, a1, b1), a2, b2)
    assert any("swapped" in e for e in validate(s))


def test_wrong_counts_and_bad_piece():
    s = list(cm.to_string(cm.SOLVED))
    s[0] = "D"
    errs = validate("".join(s))
    assert any("10 yellow" in e for e in errs) and any("8 white" in e for e in errs)


def test_rotated_top_scan_is_corrected():
    good = scrambled(4)
    faces = faces_of(good)
    faces["U"] = rotate_face(faces["U"], 1)
    faces["D"] = rotate_face(faces["D"], 2)
    r = check_scan(faces)
    assert r.valid and r.facelets == good and r.note


def test_rotate_face():
    f = list("abcdefghi")
    assert rotate_face(f, 1) == list("gdahebifc")
    assert rotate_face(f, 4) == f


# --- session ------------------------------------------------------------------
def _stable(colors, labs):
    det = Detection(True, labs=labs, colors=colors)
    return det, Stability(True, None, labs, colors)


def test_full_scan_and_solve():
    refs = load_references(DEFAULT_COLORS_FILE)
    good = scrambled(9)
    faces = faces_of(good)
    s = ScanSession()
    out = s.start_scan()
    assert isinstance(out[0], P.ScanPromptMsg) and out[0].face == "F"
    for step in SCAN_STEPS:
        cols = faces[step.face]
        labs = np.array([refs[c] for c in cols])
        msgs = s.on_frame(*_stable(cols, labs))
        assert isinstance(msgs[0], P.FaceCapturedMsg) and msgs[0].face == step.face
    state = msgs[-1]
    assert isinstance(state, P.CubeStateMsg) and state.valid and state.facelets == good
    sol = s.solve("beginner")[0]
    assert isinstance(sol, P.SolutionMsg) and sol.totalMoves > 0


def test_wrong_face_is_reported():
    refs = load_references(DEFAULT_COLORS_FILE)
    s = ScanSession()
    s.start_scan()
    cols = ["R"] * 9  # red face shown when green is expected
    msgs = s.on_frame(*_stable(cols, np.array([refs["R"]] * 9)))
    assert isinstance(msgs[0], P.ScanErrorMsg) and "on your right" in msgs[0].message
    assert s.step == 0


def test_manual_fix():
    refs = load_references(DEFAULT_COLORS_FILE)
    good = scrambled(12)
    faces = faces_of(good)
    s = ScanSession()
    s.start_scan()
    for step in SCAN_STEPS:
        cols = faces[step.face]
        s.on_frame(*_stable(cols, np.array([refs[c] for c in cols])))
    wrong = "W" if faces["F"][0] != "W" else "Y"
    assert not s.set_sticker("F", 0, wrong)[0].valid
    assert s.set_sticker("F", 0, faces["F"][0])[0].valid


def test_practice():
    s = ScanSession()
    msgs = s.practice("intermediate", random.Random(2))
    assert isinstance(msgs[0], P.PracticeMsg) and isinstance(msgs[1], P.SolutionMsg)
    assert cm.is_solved(cm.apply(msgs[0].facelets, [m.notation for st in msgs[1].stages for m in st.moves]))


def test_scheme_setting():
    from app import config
    import pytest
    assert config.parse_scheme("U=W, R=O, F=Y, D=G, L=R, B=B")["F"] == "Y"
    with pytest.raises(ValueError):
        config.parse_scheme("U=W,R=O,F=Y,D=G,L=R,B=R")
