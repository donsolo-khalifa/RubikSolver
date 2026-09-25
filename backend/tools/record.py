"""Record a scanning session to .mp4 for replay tests (PLAN.md 4).

    python tools/record.py tests/fixtures/scan1.mp4 [--source 1]

Press q or Esc to stop. Replay later with CAMERA_SOURCE=tests/fixtures/scan1.mp4.
"""
from __future__ import annotations

import argparse
import time

import _common
import cv2

from app import config
from app.camera import open_capture


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("output")
    ap.add_argument("--source")
    ap.add_argument("--fps", type=float, default=30.0)
    args = ap.parse_args()
    cap = open_capture(_common.parse_source(args.source))
    if not cap.isOpened():
        raise SystemExit("could not open camera")
    writer = None
    frames, t0 = 0, time.time()
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        if config.FLIP_HORIZONTAL:
            frame = cv2.flip(frame, 1)
        if writer is None:
            h, w = frame.shape[:2]
            writer = cv2.VideoWriter(args.output, cv2.VideoWriter_fourcc(*"mp4v"), args.fps, (w, h))
        writer.write(frame)
        frames += 1
        view = frame.copy()
        cv2.circle(view, (30, 30), 12, (0, 0, 255), -1)
        cv2.putText(view, f"REC {time.time() - t0:5.1f}s  (q to stop)", (50, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 255), 2)
        cv2.imshow("record", view)
        if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
            break
    cap.release()
    if writer:
        writer.release()
    cv2.destroyAllWindows()
    print(f"wrote {frames} frames to {args.output}")


if __name__ == "__main__":
    main()
