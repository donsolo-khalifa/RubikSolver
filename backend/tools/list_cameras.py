"""Probe camera indices 0-5 and preview each one, to find which index is Iriun.

    python tools/list_cameras.py          # press any key to move to the next camera

Put the index you want in CAMERA_SOURCE (environment variable or app/config.py).
"""
from __future__ import annotations

import _common  # noqa: F401
import cv2

from app.camera import open_capture


def main() -> None:
    found = []
    for i in range(6):
        cap = open_capture(i)
        if not cap.isOpened():
            print(f"[{i}] not available")
            continue
        ok, frame = cap.read()
        if not ok:
            print(f"[{i}] opens but gives no frames")
            cap.release()
            continue
        h, w = frame.shape[:2]
        print(f"[{i}] {w}x{h}  (press any key in the preview window for the next one)")
        found.append(i)
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            cv2.putText(frame, f"camera index {i}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (0, 255, 255), 2)
            cv2.imshow("list_cameras", frame)
            if cv2.waitKey(30) != -1:
                break
        cap.release()
    cv2.destroyAllWindows()
    print("Working indices:", found or "none")


if __name__ == "__main__":
    main()
