"""End to end: synthetic frames -> vision pipeline -> stabiliser -> scan session -> solution."""
import random

import numpy as np

from app import protocol as P
from app.scan.cube_state import SCHEME
from app.scan.session import SCAN_STEPS, ScanSession
from app.solver import cube_model as cm
from app.vision.pipeline import Pipeline
from app.vision.stabilizer import Stabilizer

from .synthetic import render_face


def test_full_scan_from_frames():
    facelets = cm.to_string(cm.apply(cm.SOLVED, cm.random_scramble(25, random.Random(21))))
    faces = {f: [SCHEME[c] for c in facelets[9 * i: 9 * i + 9]] for i, f in enumerate("URFDLB")}
    rng = np.random.default_rng(1)
    pipe, stab, session = Pipeline(), Stabilizer(), ScanSession()
    session.start_scan()
    msgs: list = []
    for k, step in enumerate(SCAN_STEPS):
        for i in range(14):  # hold the face for a bit more than the stable window
            frame = render_face(faces[step.face], angle=4 + 3 * k, rng=rng, center=(640 + i % 2, 360))
            det = pipe.process(frame)
            out = session.on_frame(det, stab.update(det))
            if any(isinstance(m, P.FaceCapturedMsg) for m in out):
                stab.reset()
            msgs += out
    captured = [m.face for m in msgs if isinstance(m, P.FaceCapturedMsg)]
    assert captured == [s.face for s in SCAN_STEPS]
    state = next(m for m in msgs if isinstance(m, P.CubeStateMsg))
    assert state.valid and state.facelets == facelets
    sol = session.solve("beginner")[0]
    assert isinstance(sol, P.SolutionMsg)
    assert cm.is_solved(cm.apply(facelets, [m.notation for st in sol.stages for m in st.moves]))


def test_moving_face_is_not_captured():
    faces = ["G"] * 9
    pipe, stab, session = Pipeline(), Stabilizer(), ScanSession()
    session.start_scan()
    rng = np.random.default_rng(2)
    for i in range(20):
        frame = render_face(faces, rng=rng, center=(500 + 25 * i, 360))
        det = pipe.process(frame)
        st = stab.update(det)
        assert not session.on_frame(det, st)
    assert st.hint == "hold_still"
