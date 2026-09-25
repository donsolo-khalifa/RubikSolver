"""FastAPI server: ``GET /video`` (MJPEG of annotated frames) and ``WS /ws`` (JSON events).

Run from ``backend/``:  ``uvicorn app.main:app --reload``  (or ``python -m app.main``)
"""
from __future__ import annotations

import asyncio
import contextlib
import logging
import threading
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from . import config
from . import protocol as P
from .camera import Camera
from .scan.cube_state import SCHEME
from .scan.session import SCAN_STEPS, ScanSession
from .vision.pipeline import Pipeline, annotate
from .vision.stabilizer import Stabilizer

log = logging.getLogger("rubik")
DETECTION_INTERVAL = 0.1  # ~10 Hz


class Hub:
    """Owns the camera, the vision thread and the scan session; fans messages out to clients."""

    def __init__(self) -> None:
        self.camera = Camera()
        self.pipeline = Pipeline()
        self.stabilizer = Stabilizer()
        self.session = ScanSession()
        self.lock = threading.Lock()  # guards session + stabilizer
        self.clients: set[WebSocket] = set()
        self.queue: asyncio.Queue[BaseModel] = asyncio.Queue()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.jpeg: bytes = _placeholder("Starting camera...")
        self.jpeg_seq = 0
        self._stop = threading.Event()

    # --- lifecycle ------------------------------------------------------------
    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        self.loop = loop
        if self.camera.start():
            threading.Thread(target=self._vision_loop, name="vision", daemon=True).start()
        else:
            log.warning("Could not open camera source %r; practice mode still works", config.CAMERA_SOURCE)
            self.jpeg = _placeholder(f"No camera at source {config.CAMERA_SOURCE!r}. See tools/list_cameras.py")
            self.jpeg_seq += 1

    def stop(self) -> None:
        self._stop.set()
        self.camera.stop()

    def emit(self, msgs: list[BaseModel]) -> None:
        """Thread-safe: queue messages for every connected client."""
        if self.loop is None:
            return
        for m in msgs:
            self.loop.call_soon_threadsafe(self.queue.put_nowait, m)

    async def broadcast_forever(self) -> None:
        while True:
            msg = await self.queue.get()
            data = msg.model_dump(mode="json")
            for ws in list(self.clients):
                try:
                    await ws.send_json(data)
                except Exception:  # noqa: BLE001 - a dropped client must not stop the others
                    self.clients.discard(ws)

    # --- vision thread --------------------------------------------------------
    def _vision_loop(self) -> None:
        last_seq, last_sent = -1, 0.0
        while not self._stop.is_set():
            seq, frame = self.camera.latest()
            if frame is None or seq == last_seq:
                time.sleep(0.005)
                continue
            last_seq = seq
            try:
                det = self.pipeline.process(frame)
            except Exception:  # noqa: BLE001 - keep streaming even if one frame breaks
                log.exception("vision pipeline failed on a frame")
                continue
            with self.lock:
                st = self.stabilizer.update(det)
                msgs = self.session.on_frame(det, st)
                if any(isinstance(m, P.FaceCapturedMsg) for m in msgs):
                    self.stabilizer.reset()
                scanning = self.session.phase == "scanning"
                target = SCHEME[SCAN_STEPS[self.session.step].face] if scanning else None
            ok, buf = cv2.imencode(".jpg", annotate(frame, det, st.stable, target), [cv2.IMWRITE_JPEG_QUALITY, 75])
            if ok:
                self.jpeg = buf.tobytes()
                self.jpeg_seq += 1
            now = time.monotonic()
            if now - last_sent >= DETECTION_INTERVAL:
                last_sent = now
                msgs.insert(0, P.DetectionMsg(found=det.found, stable=st.stable,
                                              colors=det.colors if det.found else [None] * 9,  # type: ignore[arg-type]
                                              hint=st.hint))  # type: ignore[arg-type]
            self.emit(msgs)

    # --- client commands ------------------------------------------------------
    def handle(self, msg: BaseModel) -> list[BaseModel]:
        s = self.session
        with self.lock:
            if isinstance(msg, P.StartScan):
                self.stabilizer.reset()
                return s.start_scan()
            if isinstance(msg, P.Capture):
                out = s.capture()
                self.stabilizer.reset()
                return out
            if isinstance(msg, P.Rescan):
                self.stabilizer.reset()
                return s.rescan(msg.face)
            if isinstance(msg, P.SetSticker):
                return s.set_sticker(msg.face, msg.index, msg.color)
            if isinstance(msg, P.Solve):
                return s.solve(msg.method)
            if isinstance(msg, P.PracticeScramble):
                return s.practice(msg.method)
            if isinstance(msg, P.Reset):
                return s.reset()
        return [P.ErrorMsg(message="unknown message")]


def _placeholder(text: str) -> bytes:
    img = np.full((360, 640, 3), 30, np.uint8)
    cv2.putText(img, text[:70], (20, 185), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 1, cv2.LINE_AA)
    return cv2.imencode(".jpg", img)[1].tobytes()


hub = Hub()


@contextlib.asynccontextmanager
async def lifespan(_: FastAPI):
    hub.start(asyncio.get_running_loop())
    task = asyncio.create_task(hub.broadcast_forever())
    yield
    task.cancel()
    hub.stop()


app = FastAPI(title="Rubik's Cube Vision Solver", lifespan=lifespan)


@app.get("/video")
async def video() -> StreamingResponse:
    async def frames():
        seen = -1
        while True:
            if hub.jpeg_seq != seen:
                seen = hub.jpeg_seq
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + hub.jpeg + b"\r\n"
            await asyncio.sleep(0.02)

    return StreamingResponse(frames(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()
    hub.clients.add(ws)
    with hub.lock:
        hello: list[BaseModel] = [hub.session.status(hub.camera.ok)]
        if hub.session.phase == "scanning":
            hello.append(hub.session.prompt())
    for m in hello:
        await ws.send_json(m.model_dump(mode="json"))
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = P.client_adapter.validate_json(raw)
            except ValidationError as e:
                await ws.send_json(P.ErrorMsg(message=f"bad message: {e.errors()[0]['msg']}").model_dump())
                continue
            out = await asyncio.to_thread(hub.handle, msg)
            for m in out:
                hub.queue.put_nowait(m)
    except WebSocketDisconnect:
        pass
    finally:
        hub.clients.discard(ws)


# Serve the built frontend (npm run build) when it exists; in development use the Vite server.
_dist = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000)
