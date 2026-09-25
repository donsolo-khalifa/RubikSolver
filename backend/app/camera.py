"""Capture thread that always holds only the latest frame (PLAN.md 4)."""
from __future__ import annotations

import sys
import threading
import time

import cv2
import numpy as np

from . import config


def open_capture(source: int | str) -> cv2.VideoCapture:
    if isinstance(source, int):
        # DirectShow opens faster on Windows and honours resolution requests better.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(source, backend)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAMERA_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAMERA_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap
    return cv2.VideoCapture(str(source))


class Camera:
    def __init__(self, source: int | str = config.CAMERA_SOURCE, flip: bool = config.FLIP_HORIZONTAL):
        self.source = source
        self.flip = flip
        self.is_file = isinstance(source, str)
        self._frame: np.ndarray | None = None
        self._seq = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.ok = False

    def start(self) -> bool:
        self._cap = open_capture(self.source)
        self.ok = self._cap.isOpened()
        if self.ok:
            self._thread = threading.Thread(target=self._run, name="camera", daemon=True)
            self._thread.start()
        return self.ok

    def _run(self) -> None:
        fps = self._cap.get(cv2.CAP_PROP_FPS) or 30
        delay = 1.0 / fps if self.is_file else 0.0
        while not self._stop.is_set():
            t = time.perf_counter()
            ok, frame = self._cap.read()
            if not ok:
                if self.is_file and config.LOOP_VIDEO:
                    self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    continue
                time.sleep(0.05)
                continue
            if self.flip:
                frame = cv2.flip(frame, 1)
            with self._lock:
                self._frame = frame
                self._seq += 1
            if delay:  # play video files at their real speed
                time.sleep(max(0.0, delay - (time.perf_counter() - t)))
        self._cap.release()

    def latest(self) -> tuple[int, np.ndarray | None]:
        with self._lock:
            return self._seq, self._frame

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
