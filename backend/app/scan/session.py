"""Scan state machine (PLAN.md 6.3).

IDLE -> SCANNING (face 0..5, auto-capture when stable) -> REVIEW (validate, manual fix)
-> SOLVING. Rescanning a face from REVIEW goes back to SCANNING for that one face.

The session is not thread-safe; the server calls it under a lock. Every method returns
the messages to send to the client.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np
from pydantic import BaseModel

from .. import protocol as P
from ..solver import SolveError, solve
from ..solver.cube_model import SOLVED, apply, random_scramble, to_string
from ..vision.color import assign_all
from ..vision.pipeline import Detection
from ..vision.stabilizer import Stability
from .cube_state import COLOR_NAMES, SCHEME, check_scan

FACE_ORDER = "URFDLB"


@dataclass(frozen=True)
class ScanStep:
    face: str
    rotation: str | None
    text: str


def _scan_steps() -> list[ScanStep]:
    """Prompts for each step, worded from the user's side of the cube.

    The user holds the cube between themselves and the camera, so the camera's right is the
    user's left. Each quarter turn (y) brings the face on the camera's right, which is on the
    user's LEFT, round to face the camera. The prompts name that face rather than a turning
    direction, which is ambiguous when you and the camera face each other.
    """
    n = {f: COLOR_NAMES[c] for f, c in SCHEME.items()}

    def swing(face: str) -> str:
        return f"The {n[face]} face is on your left: turn the whole cube so it swings round to face the camera."

    # Every captured image already matches the net orientation (PLAN.md 6.2).
    return [
        ScanStep("F", None, f"Hold the cube with {n['U']} on top and {n['F']} facing the camera."),
        ScanStep("R", "y", swing("R")),
        ScanStep("B", "y", swing("B")),
        ScanStep("L", "y", swing("L")),
        ScanStep("U", "y x'", f"Turn it the same way once more so {n['F']} faces the camera again, "
                              f"then tip the top towards the camera so {n['U']} faces it."),
        ScanStep("D", "x2", f"Keep tipping the top towards the camera, two more times, "
                            f"until {n['D']} (now facing you) faces the camera."),
    ]


SCAN_STEPS = _scan_steps()


@dataclass
class CapturedFace:
    labs: np.ndarray  # 9x3
    colors: list[str]


@dataclass
class ScanSession:
    phase: str = "idle"
    step: int = 0
    captured: dict[str, CapturedFace] = field(default_factory=dict)
    final: dict[str, list[str]] = field(default_factory=dict)  # after the 54-sticker assignment
    manual: dict[tuple[str, int], str] = field(default_factory=dict)
    facelets: str | None = None
    rescan_face: str | None = None
    last: Detection | None = None
    last_wrong_centre: str | None = None

    # --- commands -------------------------------------------------------------
    def reset(self) -> list[BaseModel]:
        self.__init__()  # type: ignore[misc]
        return [self.status(True)]

    def start_scan(self) -> list[BaseModel]:
        self.__init__()  # type: ignore[misc]
        self.phase = "scanning"
        return [self.prompt()]

    def rescan(self, face: str) -> list[BaseModel]:
        if not self.captured:
            return self.start_scan()
        self.phase = "scanning"
        self.rescan_face = face
        self.step = next(i for i, s in enumerate(SCAN_STEPS) if s.face == face)
        self.manual = {k: v for k, v in self.manual.items() if k[0] != face}
        step = SCAN_STEPS[self.step]
        name = COLOR_NAMES[SCHEME[face]]
        return [P.ScanPromptMsg(step=self.step, face=face, rotation=None,
                                text=f"Rescan: show the {name} face, holding the cube as in step {self.step + 1}. {step.text}")]

    def capture(self) -> list[BaseModel]:
        """Manual capture of the latest detection, even if it hasn't been held steady."""
        d = self.last
        if self.phase != "scanning" or d is None or not d.found or d.labs is None:
            return [P.ErrorMsg(message="No cube face is visible right now.")]
        return self._capture(d.labs, d.colors)

    def set_sticker(self, face: str, index: int, color: str) -> list[BaseModel]:
        if not self.final:
            return [P.ErrorMsg(message="Scan all six faces before fixing stickers.")]
        if index == 4:
            return [P.ErrorMsg(message="Centre stickers can't be changed; they name the faces.")]
        self.manual[(face, index)] = color
        self.final[face][index] = color
        return self._validate()

    def solve(self, method: str) -> list[BaseModel]:
        if not self.facelets:
            return [P.ErrorMsg(message="There is no valid scanned cube to solve yet.")]
        return self._solve(self.facelets, method)

    def practice(self, method: str, rng: random.Random | None = None) -> list[BaseModel]:
        scramble = random_scramble(20, rng)
        facelets = to_string(apply(SOLVED, scramble))
        self.phase = "solving"
        return [P.PracticeMsg(scramble=scramble, facelets=facelets), *self._solve(facelets, method)]

    # --- per frame ------------------------------------------------------------
    def on_frame(self, det: Detection, st: Stability) -> list[BaseModel]:
        self.last = det
        if self.phase != "scanning" or not st.stable or st.labs is None:
            return []
        step = SCAN_STEPS[self.step]
        expected = SCHEME[step.face]
        centre = st.colors[4] if st.colors else None
        if centre != expected:
            if centre is None or centre == self.last_wrong_centre:
                return []
            self.last_wrong_centre = centre
            return [P.ScanErrorMsg(face=step.face, message=self._wrong_centre_text(centre, step.face))]
        self.last_wrong_centre = None
        return self._capture(st.labs, st.colors)

    # --- internals ------------------------------------------------------------
    def prompt(self) -> P.ScanPromptMsg:
        s = SCAN_STEPS[self.step]
        return P.ScanPromptMsg(step=self.step, face=s.face, rotation=s.rotation, text=s.text)

    def status(self, camera: bool) -> P.StatusMsg:
        return P.StatusMsg(camera=camera, phase=self.phase, scheme=SCHEME)  # type: ignore[arg-type]

    def _wrong_centre_text(self, centre: str, face: str) -> str:
        want = COLOR_NAMES[SCHEME[face]]
        got = COLOR_NAMES.get(centre, "another")
        shown = next((f for f, c in SCHEME.items() if c == centre), None)
        order = [s.face for s in SCAN_STEPS[:4]]
        if shown in order and face in order:
            diff = (order.index(shown) - order.index(face)) % 4
            # Directions are from the user's side: the camera's left is the user's right.
            if diff == 1:
                return f"That's the {got} face; you went one step too far. Turn back: the {want} face is on your right."
            if diff == 3:
                return f"That's the {got} face; you turned the other way. The {want} face is on your left."
        return f"That's the {got} face. Show the {want} face: {SCAN_STEPS[self.step].text}"

    def _capture(self, labs: np.ndarray, colors: list[str | None]) -> list[BaseModel]:
        face = SCAN_STEPS[self.step].face
        cols = [c or SCHEME[face] for c in colors]
        cols[4] = SCHEME[face]
        self.captured[face] = CapturedFace(np.array(labs, dtype=float), cols)
        out: list[BaseModel] = [P.FaceCapturedMsg(face=face, colors=cols)]  # type: ignore[arg-type]
        if self.rescan_face is not None:
            self.rescan_face = None
            out += self._finish()
        elif self.step + 1 < len(SCAN_STEPS):
            self.step += 1
            out.append(self.prompt())
        else:
            out += self._finish()
        return out

    def _finish(self) -> list[BaseModel]:
        """All 6 faces in: assign all 54 stickers so each colour gets exactly 9, then validate."""
        labs = np.concatenate([self.captured[f].labs for f in FACE_ORDER])
        centre_colors = [SCHEME[f] for f in FACE_ORDER]
        idx = assign_all(labs)
        flat = [centre_colors[k] for k in idx]
        self.final = {f: flat[9 * i: 9 * i + 9] for i, f in enumerate(FACE_ORDER)}
        for (f, i), c in self.manual.items():
            self.final[f][i] = c
        self.phase = "review"
        return self._validate()

    def _validate(self) -> list[BaseModel]:
        result = check_scan({f: list(v) for f, v in self.final.items()})
        if result.valid:
            self.final = result.faces
        self.facelets = result.facelets if result.valid else None
        return [P.CubeStateMsg(facelets=result.facelets, valid=result.valid,
                               errors=result.errors, note=result.note)]

    def _solve(self, facelets: str, method: str) -> list[BaseModel]:
        try:
            sol = solve(facelets, method)  # type: ignore[arg-type]
        except SolveError as e:
            return [P.ErrorMsg(message=f"Could not solve this cube: {e}")]
        self.phase = "solving"
        return [P.SolutionMsg(facelets=facelets, **sol.to_dict())]
