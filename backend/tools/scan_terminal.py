"""Phase 5: guided 6-face scan in an OpenCV window, then a printed solution. No server needed.

    python tools/scan_terminal.py [--source 1] [--method beginner|intermediate|advanced]

Keys: space = capture now, r = restart, q/Esc = quit.
"""
from __future__ import annotations

import argparse

import _common
import cv2

from app import protocol as P
from app.camera import open_capture
from app.config import FLIP_HORIZONTAL
from app.scan.session import ScanSession
from app.vision.pipeline import Pipeline, annotate
from app.vision.stabilizer import Stabilizer


def print_solution(sol: P.SolutionMsg) -> None:
    print(f"\n{sol.method} solution, {sol.totalMoves} moves:")
    for i, stage in enumerate(sol.stages, 1):
        print(f"\n{i}. {stage.name}: {stage.goal}")
        print("   " + " ".join(mv.notation for mv in stage.moves))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--method", default="beginner", choices=["beginner", "intermediate", "advanced"])
    args = ap.parse_args()
    cap = open_capture(_common.parse_source(args.source))
    if not cap.isOpened():
        raise SystemExit("could not open camera")
    pipe, stab, session = Pipeline(), Stabilizer(), ScanSession()
    session.start_scan()
    text = session.prompt().text
    print(text)
    done = False
    while not done:
        ok, frame = cap.read()
        if not ok:
            break
        if FLIP_HORIZONTAL:
            frame = cv2.flip(frame, 1)
        det = pipe.process(frame)
        st = stab.update(det)
        msgs = session.on_frame(det, st)
        key = cv2.waitKey(1) & 0xFF
        if key == ord(" "):
            msgs += session.capture()
        elif key == ord("r"):
            msgs += session.start_scan()
        elif key in (ord("q"), 27):
            break
        for m in msgs:
            if isinstance(m, P.FaceCapturedMsg):
                stab.reset()
                print(f"captured {m.face}: {''.join(m.colors)}")
            elif isinstance(m, P.ScanPromptMsg):
                text = m.text
                print(text)
            elif isinstance(m, P.ScanErrorMsg):
                text = m.message
                print(text)
            elif isinstance(m, P.CubeStateMsg):
                print("facelets:", m.facelets, "valid:", m.valid)
                for e in m.errors:
                    print("  -", e)
                if m.valid:
                    sol = session.solve(args.method)[0]
                    if isinstance(sol, P.SolutionMsg):
                        print_solution(sol)
                    else:
                        print(sol)
                    done = True
                else:
                    text = "Scan is not a valid cube; press r to rescan."
        view = annotate(frame, det, st.stable)
        cv2.putText(view, text[:90], (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        if st.hint:
            cv2.putText(view, st.hint, (15, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imshow("scan", view)
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
