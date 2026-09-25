"""Show every vision stage side by side (PLAN.md 5). Tune thresholds here first.

    python tools/debug_pipeline.py                     # live camera (CAMERA_SOURCE)
    python tools/debug_pipeline.py --source clip.mp4   # recorded video
    python tools/debug_pipeline.py --image ../referenceImages/x.jpeg

Keys: space = pause, s = save the stack to debug.png, q/Esc = quit.
"""
from __future__ import annotations

import argparse

import _common
import cv2
import cvzone
import numpy as np

from app.camera import open_capture
from app.vision.lattice import fit_grid
from app.vision.pipeline import Pipeline, annotate
from app.vision.stabilizer import Stabilizer
from app.vision.sticker_detector import detect_stickers
from app.vision.warp import warp_face


def stack(frame: np.ndarray, pipe: Pipeline, stab: Stabilizer) -> np.ndarray:
    st = detect_stickers(frame, want_debug=True)
    det = pipe.process(frame)
    s = stab.update(det)
    small = st.debug["small"]
    h, w = small.shape[:2]
    fit = fit_grid(st.candidates)
    warp = warp_face(frame, fit) if fit else None
    face = cv2.resize(warp.face, (h, h)) if warp else np.zeros((h, h, 3), np.uint8)
    face = cv2.copyMakeBorder(face, 0, 0, 0, max(0, w - h), cv2.BORDER_CONSTANT)[:, :w]
    ann = cv2.resize(annotate(frame, det, s.stable), (w, h))
    text = (f"cands={len(st.candidates)} cells={len(fit.cells) if fit else 0} "
            f"sharp={det.sharpness:.0f} hint={s.hint} stable={s.stable}")
    cvzone.putTextRect(ann, text, (10, 25), scale=1, thickness=1, offset=4)
    cvzone.putTextRect(face, "".join(c or "?" for c in det.colors), (10, 25), scale=1.2, thickness=2, offset=4)
    return cvzone.stackImages(
        [st.debug["edges"], st.debug["bright"], st.debug["candidates"], st.debug["stickers"], face, ann], 3, 0.7
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--image")
    args = ap.parse_args()
    pipe, stab = Pipeline(), Stabilizer()
    if args.image:
        img = cv2.imread(args.image)
        if img is None:
            raise SystemExit(f"cannot read {args.image}")
        cv2.imshow("debug_pipeline", stack(img, pipe, stab))
        cv2.waitKey(0)
        return
    cap = open_capture(_common.parse_source(args.source))
    paused, view = False, None
    while True:
        if not paused or view is None:
            ok, frame = cap.read()
            if not ok:
                break
            view = stack(frame, pipe, stab)
        cv2.imshow("debug_pipeline", view)
        k = cv2.waitKey(1) & 0xFF
        if k in (ord("q"), 27):
            break
        if k == ord(" "):
            paused = not paused
        if k == ord("s"):
            cv2.imwrite("debug.png", view)
            print("saved debug.png")
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
