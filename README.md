# Cube Coach: Rubik's Cube Vision Solver

Scan a 3x3 cube with your phone camera (through Iriun), then follow an animated 3D cube, one move at a time, with spoken instructions. Three methods: **Beginner** (default), **Intermediate** (2-look OLL/PLL) and **Advanced** (Kociemba). There's also a **Practice** mode that needs no camera.

## Setup

Backend (Python 3.11+; built and tested on 3.14):

```sh
cd backend
python -m venv .venv
.venv\Scripts\activate            # Windows (source .venv/bin/activate elsewhere)
pip install -r requirements.txt
```

`kociemba` builds a C extension. If it fails on Windows, install the MSVC Build Tools, or `pip install RubikTwoPhase` instead (the Advanced solver falls back to it automatically).

Frontend (Node 20+):

```sh
# in a new termminal
cd frontend
npm install
```

## Running

Run the backend commands in `backend/` with the virtual environment active (`.venv\Scripts\activate`).

1. Start Iriun on the phone and PC, then find its camera index:
   ```sh
   cd backend
   python tools/list_cameras.py
   ```
2. Create your settings file from the example:
   ```sh
   copy .env.example .env            # Windows (cp .env.example .env elsewhere)
   ```
   Open `backend/.env` and set `CAMERA_SOURCE` to the index from step 1 (for example `CAMERA_SOURCE=1`). If your cube is not the standard colour scheme, set `COLOR_SCHEME` too (see the table below).
3. Start the backend:
   ```sh
   python -m app.main                # http://127.0.0.1:8000
   ```
4. In a second terminal, start the frontend dev server and open the URL it prints:
   ```sh
   cd frontend
   npm run dev
   ```
   Or run `npm run build` once; the backend then serves the app itself at http://127.0.0.1:8000.

Settings go in `backend/.env` (see [backend/.env.example](backend/.env.example)); an environment variable set in the shell overrides the file. They are read in [backend/app/config.py](backend/app/config.py):

| Variable | Default | Meaning |
|----------|---------|---------|
| `CAMERA_SOURCE` | `0` | Webcam index, or a path to a video file to replay |
| `COLOR_SCHEME` | `U=W,R=R,F=G,D=Y,L=O,B=B` | Colour on each face in the first scan's hold (top, right, front, bottom, left, back); set it if your cube is not the standard scheme |
| `CAMERA_WIDTH` / `CAMERA_HEIGHT` | `1280` / `720` | Requested camera resolution |
| `FLIP_HORIZONTAL` | `0` | Set to `1` if Iriun mirrors the picture |
| `LOOP_VIDEO` | `1` | Loop a video-file source |
| `MIN_SHARPNESS` | `10` | Blur threshold for capture (see *Known limitations*) |
| `COLORS_FILE` | `backend/colors.json` | Calibrated colours; built-in defaults are used when missing |

Practice mode and the "How to read moves" introduction work without a camera.

## Tools (`backend/tools/`)

| Script | What it does |
|--------|--------------|
| `list_cameras.py` | Probes camera indices 0–5 with a preview, to find Iriun |
| `debug_pipeline.py` | Every vision stage side by side (`--image`, `--source`) |
| `calibrate_colors.py` | Measures your cube's colours under your light; writes `colors.json` |
| `record.py` | Records a scanning session to `.mp4`, for replay and tests |
| `scan_terminal.py` | Guided scan in an OpenCV window, then prints a solution (no browser) |

A session recorded with `record.py` can stand in for the camera, for example `CAMERA_SOURCE=recordings/scan1.mp4`.

## Tests

```sh
cd backend && python -m pytest          # 186 tests
cd frontend && npm test                 # 13 tests; npm run typecheck for tsc
```

They cover: the cube model (every move against Kociemba's own example); 500 random scramble → solve → check round trips per method; every OLL/PLL algorithm picked for its own case and every case reached; validation (flipped edge, twisted corner, swapped pieces, wrong counts, U/D rotation repair); lattice fitting, homography and the constrained colour assignment on synthetic data; detection and colours on every photo in `referenceImages/` against `tests/fixtures/labels.json`; a full synthetic six-face scan from rendered frames through to a verified solution; and on the frontend, every move of the Three.js cube matched against the facelet model.

## How it works

- **Vision** (`app/vision/`): sticker candidates come from Canny contours and from bright blobs enclosed by the black cube body (the second source survives motion blur). A 3x3 grid is fitted by anchoring each candidate at each of the 9 cells, so the fit works even when the centre sticker is missed. A RANSAC homography warps the face to 300×300, and the inner half of each cell is sampled with glare masked out.
- **Colour**: stickers are compared in a feature space where chroma saturates. Hue always counts fully, so a sticker washed out by glare stays next to its real colour instead of drifting to white. After all six faces are in, every sticker is assigned together so each colour gets exactly 9 (`linear_sum_assignment`).
- **Solvers** (`app/solver/`): a geometric 54-facelet model (face, wide and slice moves, rotations). Beginner and Intermediate run on a stage engine: search or procedure per stage, case recognition for the last layer. Every solution is replayed on the model and checked before it is sent.
- **Frontend** (`frontend/src/`): Three.js cube with a move queue and snapping, curved arrows, stage cards with previews and algorithm cards, speech (on by default), keyboard control (Space captures a face while scanning; when solving, Space/→ next, ← back, R show again, P auto-play).

## Known limitations and next steps

- **No real video test yet.** The pipeline is tuned on the 7 reference photos and on synthetic frames. Record 2–3 real scanning sessions with `tools/record.py` in your actual set-up, then check them with `debug_pipeline.py`.
- **Sharpness check:** at warp resolution, the "blurry" red-face photo is no less sharp than the others (the blur is mostly in the background), so no threshold can flag it without also rejecting sharp faces. `MIN_SHARPNESS` is set low; tune it on recorded video.
- **Yellow face not photographed yet.** It should have 1 red, 2 blue, 4 yellow and 2 green stickers (worked out from the colour counts of the other five faces).
- **Move counts** are higher than first estimated: median 156 (Beginner), 131 (Intermediate), 21 (Advanced) over 300 scrambles. Intermediate reuses the Beginner first two layers, which alone take about 90 moves.
- Stretch goals (AR arrows on the video, camera-based move verification, algorithm trainer) are not built yet.

## License

[MIT](LICENSE)
