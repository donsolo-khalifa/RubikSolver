"""Sample reference colours from your own cube under your own light (PLAN.md 5.6).

    python tools/calibrate_colors.py [--source 1]

Show each face as prompted and hold c while it is steady to collect samples of its centre.
Saves colors.json (COLORS_FILE), which the app then uses instead of the built-in defaults.

    python tools/calibrate_colors.py --images w.jpg y.jpg r.jpg o.jpg g.jpg b.jpg

calibrates from photos instead (one face per photo, in the order W Y R O G B).
"""
from __future__ import annotations

import argparse

import _common
import cv2
import numpy as np

from app.camera import open_capture
from app.scan.cube_state import COLOR_NAMES
from app.vision.color import COLORS, save_references
from app.vision.pipeline import Pipeline, annotate

SAMPLES = 15


def from_images(paths: list[str], pipe: Pipeline) -> dict[str, np.ndarray]:
    refs = {}
    for c, p in zip(COLORS, paths):
        det = pipe.process(cv2.imread(p))
        if not det.found or det.labs is None:
            raise SystemExit(f"no face found in {p}")
        refs[c] = det.labs[4]
    return refs


def from_camera(source, pipe: Pipeline) -> dict[str, np.ndarray]:
    cap = open_capture(source)
    refs = {}
    for c in COLORS:
        samples: list[np.ndarray] = []
        while len(samples) < SAMPLES:
            ok, frame = cap.read()
            if not ok:
                raise SystemExit("camera stopped")
            det = pipe.process(frame)
            view = annotate(frame, det)
            msg = f"Show the {COLOR_NAMES[c]} face, then hold c ({len(samples)}/{SAMPLES}). q = quit"
            cv2.putText(view, msg, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            cv2.imshow("calibrate", view)
            k = cv2.waitKey(1) & 0xFF
            if k in (ord("q"), 27):
                raise SystemExit("cancelled")
            if k == ord("c") and det.found and det.labs is not None:
                samples.append(det.labs[4])
        refs[c] = np.median(samples, axis=0)
        print(c, refs[c].round(1))
    cap.release()
    cv2.destroyAllWindows()
    return refs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source")
    ap.add_argument("--images", nargs="*")
    args = ap.parse_args()
    pipe = Pipeline()
    refs = from_images(args.images, pipe) if args.images else from_camera(_common.parse_source(args.source), pipe)
    save_references(refs)
    print("saved colour references")


if __name__ == "__main__":
    main()
