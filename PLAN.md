# Rubik's Cube Vision Solver: Implementation Plan

A webcam app that scans a 3x3 Rubik's cube, works out its state, solves it, and shows the user how to solve it with an animated 3D cube, step by step.

- **Vision backend:** Python, OpenCV, cvzone (contour and debug helpers), FastAPI (server)
- **Frontend:** TypeScript + Three.js, built with Vite
- **Camera:** a phone used as a webcam through Iriun
- **Solving methods (the user picks one):**
  - *Beginner*: layer by layer, with the daisy cross; about 100–150 moves, every step explained.
  - *Intermediate*: the first two layers as in Beginner, then a 4-step last layer (2-look OLL and 2-look PLL, standard algorithm sets, see section 7); about 70–100 moves.
  - *Advanced*: Kociemba; about 20 moves, not something a person can learn, just follow along.

---

## 0. Decisions so far

| Question | Decision |
|----------|----------|
| What "gesture" means | The **app shows the user** what to do: animated 3D rotations and moves, text, and optional spoken instructions. Hand-gesture input is not in scope. |
| Cube type | Stickered, black body. The reference photos show clear black gaps between stickers. **Detection finds the individual stickers and the centre sticker**, not the outer border of the face. |
| Solver | **Three methods: Beginner, Intermediate, Advanced**, all behind one interface. The user doesn't know how to solve a cube yet, so the app also has to **teach**: an introduction to move notation, an explanation for each stage, and algorithm cards. **Beginner is the default.** |
| Camera | Phone through **Iriun** (appears as a normal webcam). The input source can be swapped: webcam index or a video file. |
| Frontend language | **TypeScript** (strict mode) |
| Speech | **On by default**, with a toggle that is remembered in `localStorage`. |
| Reference photos | `referenceImages/`: 5 faces of the user's cube, labelled in 5.0 and used as the first test fixtures. |

---

## 1. Goals and scope

### MVP (must have)
1. Find the 9 stickers of a cube face in the video feed and locate the centre sticker.
2. Compute a homography from the sticker grid and warp the face to a flat 300×300 image.
3. Sample the 3x3 grid and classify each sticker's colour.
4. Guide the user through scanning all 6 faces, with animated instructions for how to turn the cube.
5. Check that the scanned state is a legal cube.
6. Solve it with the chosen method (Beginner, Intermediate or Advanced).
7. Show the solution as animated 3D moves with plain-language instructions, **spoken aloud (on by default)**, and next/previous/play controls.
8. A **"How to read moves"** introduction for someone who has never solved a cube.

### Should have
- Manual fix: click a sticker in the UI to change its colour.
- Auto-capture: a face is captured once it has been held steady.
- Keyboard shortcuts (space for next move, and so on), since the user's hands are busy.
- **Practice mode (no camera):** the app scrambles a virtual cube and plays the solution in the 3D view. It helps with learning, and lets the frontend be tested without the vision side.

### Stretch
- **AR overlay:** draw the move arrow directly on the live video, on top of the cube.
- **Move verification:** while solving, watch the front face through the camera and move on to the next instruction automatically once the expected state is seen.
- An algorithm trainer: practise individual algorithms (Sune, the OLL and PLL cases) on the 3D cube.
- More methods behind the same interface, such as full CFOP or Roux.

---

## 2. Architecture

```
┌──────────────────────── Python backend ────────────────────────┐
│                                                                 │
│  Camera thread ──► Vision pipeline ──► Scan session (state      │
│  (Iriun / webcam /   stickers → lattice → machine) ──► Solvers  │
│   video file)        homography → warp → colours   (beginner /  │
│                                                     advanced)   │
│  FastAPI:  GET /video  (MJPEG stream of annotated frames)       │
│            WS  /ws     (JSON events both ways)                  │
└────────────────────────────┬────────────────────────────────────┘
                             │  localhost
┌────────────────────────────▼─── Browser (Vite + TS + Three.js) ─┐
│  <img src="/video">   live annotated camera feed                │
│  3D cube view          scanned state, scan guidance, move anims │
│  Panels                scan progress, manual fix, solution      │
└──────────────────────────────────────────────────────────────────┘
```

**Decision: Python owns the camera.** OpenCV reads Iriun as a normal webcam. The browser shows an MJPEG stream of the annotated frames, and the WebSocket carries only small JSON messages.

---

## 3. Project structure

```
RubikSolver/
├── PLAN.md
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py               # FastAPI app, /video, /ws
│   │   ├── camera.py             # capture thread; webcam index or video file
│   │   ├── config.py             # camera source, flip, thresholds
│   │   ├── protocol.py           # Pydantic models for WS messages
│   │   ├── vision/
│   │   │   ├── sticker_detector.py  # contours → sticker candidates
│   │   │   ├── lattice.py        # candidates → 3x3 grid coords (finds centre)
│   │   │   ├── warp.py           # homography + 300x300 warp
│   │   │   ├── grid.py           # sample the 9 cells
│   │   │   ├── color.py          # colour classification (LAB)
│   │   │   └── stabilizer.py     # multi-frame smoothing / "held steady"
│   │   ├── scan/
│   │   │   ├── session.py        # scan state machine
│   │   │   └── cube_state.py     # facelet string, validation
│   │   └── solver/
│   │       ├── cube_model.py     # facelet array + move permutations
│   │       ├── base.py           # Solver interface, Solution/Stage/Move types
│   │       ├── stage_engine.py   # runs a Method: list of stages → moves
│   │       ├── search.py         # IDDFS over reduced piece state
│   │       ├── algorithms.py     # named algorithms + descriptions (all methods)
│   │       └── methods/
│   │           ├── beginner.py   # daisy cross → … → orient corners
│   │           ├── intermediate.py # first two layers + 2-look OLL + 2-look PLL
│   │           └── advanced.py   # Kociemba wrapper
│   ├── tools/
│   │   ├── list_cameras.py       # probe camera indices, find Iriun
│   │   ├── debug_pipeline.py     # OpenCV window, all stages stacked
│   │   ├── calibrate_colors.py   # sample and save reference colours
│   │   └── record.py             # record a session to .mp4 for replay tests
│   └── tests/
│       ├── fixtures/             # recorded videos + labels.json
│       └── test_*.py             # (the photos stay in referenceImages/)
└── frontend/                     # npm create vite@latest -- --template vanilla-ts
    ├── index.html
    ├── package.json              # three, @types/three, (gsap)
    ├── tsconfig.json             # "strict": true
    └── src/
        ├── main.ts
        ├── net/
        │   ├── protocol.ts       # discriminated-union message types (mirror protocol.py)
        │   └── socket.ts         # typed WebSocket client
        ├── cube/
        │   ├── CubeModel.ts      # 27 cubies, facelet → sticker mapping
        │   ├── MoveAnimator.ts   # layer/whole-cube rotation tweens, queue
        │   ├── notation.ts       # "R2" / "x'" → {axis, layers, angle}
        │   └── Arrow.ts          # curved arrow showing turn direction
        ├── guidance/
        │   ├── describe.ts       # "R'" → "Turn the right face anticlockwise"
        │   └── speech.ts         # Web Speech API wrapper (on by default)
        └── ui/
            ├── NotationIntro.ts  # interactive "how to read moves"
            ├── ScanPanel.ts
            ├── ReviewPanel.ts    # 2D net, click-to-fix
            ├── SolvePanel.ts     # method picker, stages, controls
            └── PracticePanel.ts  # virtual scramble, no camera
```

---

## 4. Camera input (Iriun)

- Iriun shows up on Windows as an ordinary webcam. **`tools/list_cameras.py`** tries indices 0–5 with `cv2.VideoCapture(i, cv2.CAP_DSHOW)`, prints each one's resolution, and shows a preview so you can tell which one is Iriun. Save that index in `config.py`.
- Use the **`CAP_DSHOW`** backend on Windows. It usually opens faster and handles resolution settings better than the default.
- Request **1280×720**. Detection can run on a downscaled copy (for example 640 px wide), with colour sampled from the full-resolution frame.
- **Set-up tips:** mount the phone on a stand about 30–40 cm away, use a plain background and soft, even light (not a single bright lamp causing glare). If Iriun can connect over USB with your phone, use that, since it is usually steadier than Wi-Fi. If the Iriun app lets you lock focus or exposure, lock them so colours don't shift between frames.
- **Mirroring:** check whether Iriun mirrors the image. Add a `FLIP_HORIZONTAL` config flag. The vision pipeline must always see the unmirrored image, because mirroring swaps left and right and puts facelets in the wrong positions.
- **Swappable source:** `CAMERA_SOURCE` accepts a camera index **or a path to a video file**. Record a few scanning sessions once with `tools/record.py` and replay them during development and in tests, so you don't need to hold a cube every time you change a threshold.
- Alternatives if Iriun gives you trouble: DroidCam works the same way, and the laptop webcam is fine for early development.

---

## 5. Vision pipeline (backend)

Build and tune this first as a **standalone script** (`tools/debug_pipeline.py`) that shows every stage side by side with `cvzone.stackImages`. Don't start on the server until this works reliably.

### 5.0 What the reference photos show

The photos in `referenceImages/` (810×1080 phone photos, held in the hand over a wooden floor) back up the sticker-based approach and point to a few specific problems:

| Observation | What it means for the pipeline |
|-------------|--------------------------------|
| Black cube body, with **clear black gaps** between stickers (roughly 8–10% of a sticker's width) | Sticker detection should work well. The gaps are wide enough that one small dilation won't merge stickers. |
| Stickers are squares with **rounded corners** | Use the fill-ratio filter (5.2), not just "exactly 4 vertices". |
| **Wood-grain floor** with light reflections | Canny will find many false edges in the background. The size and squareness filters and the grid fit (5.3) reject them. A plain background still helps. |
| **Motion blur** (the red-face photo is visibly soft) | Add a **sharpness check** (variance of the Laplacian over the face) and don't capture blurry frames. |
| **Glare spots** (top-right green sticker, orange and green centres) | Before taking the median, mask out glare pixels (very bright and low colour). Never sample only the middle pixel. |
| **Lime green**, **sky blue**, pinkish red, strong orange, greyish white | These are far from "textbook" colours, so fixed HSV ranges would fail. Classifying against the scanned centre colours (5.6) handles this. Red and orange do look clearly different in these photos. |
| White stickers are about as bright as the floor | Not a problem, because only cells inside the fitted grid are classified. |
| The hand holds the cube from the left and the thumb sits below it, **without covering stickers** | Occlusion is rare with this grip. The unknown-colour check (5.5) covers the cases where it happens. |
| The face fills about 40–45% of the image width and is nearly upright and square-on | A good distance. Tell the user to aim for this during scanning. |

**Fixture labels.** Read row by row, as in the photos. These stay as hand-labelled test data in `tests/fixtures/labels.json`:

| File | Centre | Stickers (rows top to bottom) |
|------|--------|--------------------------------|
| `…2.22.43 AM.jpeg` (same file as `…2.23.08 AM (5).jpeg`) | Red | `R B R / B R R / R Y O` |
| `…2.23.08 AM.jpeg` | White | `W W W / W W W / W W W` |
| `…2.23.08 AM (1).jpeg` | Orange | `Y O O / Y O R / Y Y O` |
| `…2.23.08 AM (2).jpeg` | Green | `G O G / G G O / G R G` |
| `…2.23.08 AM (3).jpeg`, `(4).jpeg` | Blue | `B B O / G B R / B O B` |
| missing | Yellow | this face hasn't been photographed yet |

The 45 stickers above contain 8 R, 7 B, 5 Y, 9 O, 7 G and 9 W. So the yellow face should contain **1 R, 2 B, 4 Y, 2 G** (and no O or W). That is a useful check once it has been photographed. The photos don't record which face was on top for each shot, so they can test detection and colour classification but not a complete solve. A complete solve needs a recorded scan session (section 4).

### 5.1 Why detect stickers instead of the face border

The border around the face is thin and often lost against the background or hidden by fingers. Each sticker, by contrast, is a clear coloured square separated from its neighbours by a black gap. Finding the stickers and fitting a 3x3 grid to them:
- doesn't depend on the outer border at all,
- still works if fingers hide 2 or 3 edge stickers,
- identifies the **centre sticker** directly, and its colour tells you which face is being shown,
- gives up to 9 point pairs for the homography instead of 4 corners, so the fit is more accurate.

### 5.2 Sticker candidates (`sticker_detector.py`)

```
frame → grayscale → light blur (3x3 or bilateral) → Canny
      → at most 1 small dilation → findContours (RETR_TREE)
      → approxPolyDP / minAreaRect → filter → dedupe
```

- **Careful with dilation.** The black gaps between stickers are thin, and strong dilation merges neighbouring stickers into one blob. Start with none, or one 3×3 pass, and tune with the debug view. If Canny struggles, try `cv2.adaptiveThreshold` instead.
- **Sticker filter:**
  - 4 vertices from `approxPolyDP`, *or* a fill ratio (`contourArea / minAreaRect area`) above 0.8, to allow for rounded sticker corners;
  - aspect ratio between 0.75 and 1.33;
  - area within a range tied to frame size (reject specks and huge shapes);
  - convex.
- **Dedupe:** the inner and outer edges of one sticker can both produce a contour. Merge candidates whose centres are closer than about 0.3 × sticker size.
- Keep candidates whose area is within ±40% of the **median** candidate area. Stickers on one face are all about the same size.
- `cvzone.findContours(img, imgPre, minArea=..., filter=...)` can handle the basic contour and corner filtering. Check its signature in your installed version.

### 5.3 Fitting the 3x3 grid and finding the centre (`lattice.py`)

The goal is to give every candidate a grid position (row, column) and pick out the centre.

1. **Grid direction:** take the median `minAreaRect` angle of the candidates (modulo 90°) to get the grid's two axis directions `u` and `v`. Choose the rotation closest to upright (within ±45°), so row 0 is the top of the image. The user holds the face roughly upright.
2. **Spacing:** `s` = median distance from each candidate to its nearest neighbour (sticker size plus gap).
3. **Try each candidate as the centre:** for a candidate `c`, map every other candidate `p` to grid coordinates `(i, j) = round(((p − c)·v / s, (p − c)·u / s))`. Count the *inliers*: candidates with `|i|, |j| ≤ 1`, a small rounding error, and no two in the same cell.
4. **The centre** is the candidate with the most inliers. Accept the face when there are **at least 5 inliers covering at least 2 rows and 2 columns** (enough to pin down a homography).
5. **Perspective:** the fit above assumes a flat, square-on grid, which is close enough when the face points at the camera. The homography in the next step corrects any tilt.

### 5.4 Homography and warp (`warp.py`)

Map each inlier's image centroid to where it belongs in the 300×300 warp. Cell (row `r`, column `c`) is centred at `(50 + 100c, 50 + 100r)`.

```python
H, _ = cv2.findHomography(img_pts, warp_pts, cv2.RANSAC, 5.0)   # ≥ 4 points
face = cv2.warpPerspective(frame, H, (300, 300))
outline = cv2.perspectiveTransform(warp_corners, np.linalg.inv(H))  # face outline for the overlay
```

With 5–9 points, RANSAC throws out a sticker that was placed wrongly. Mapping the warp corners back through the inverse homography gives you the face outline for drawing on the video (for example with `cvzone.cornerRect`), without ever having detected that outline.

### 5.5 3x3 sampling (`grid.py`)

- Sample the **inner ~50%** of each 100×100 cell. This keeps out the black gaps and some edge glare.
- **Mask out glare pixels** (very high brightness with low colour, as seen on the green and orange centres in the reference photos), then take the **median** colour of what's left. If more than about 40% of a cell is glare, mark it `glare`.
- Convert to **LAB**.
- Every cell is sampled at its predicted position, **including stickers the detector missed**. If a finger covers a cell, its colour will be far from every reference colour, so it's marked **unknown** and the face is not captured until it's visible.

### 5.6 Colour classification (`color.py`)

There are two stages:
1. **Live (per face):** match each sticker to the nearest reference colour in LAB space. Reference colours come from `calibrate_colors.py`, or from centres already scanned. This drives the preview overlay and the unknown/occluded check.
2. **Final (all 54 stickers together):** the 6 **centre stickers** set the reference colours. Assign the 54 stickers so that **each colour gets exactly 9**, using `scipy.optimize.linear_sum_assignment` on a 54×54 cost matrix of LAB distances with each centre colour repeated 9 times. This fixes most red/orange and white/yellow mistakes.

Problems to watch for:
- **Red vs orange** under warm light, and **white vs yellow** under yellow bulbs. The fixes are LAB, calibration, the constrained assignment, and manual correction.
- **Glare:** very high L with low colour means a highlight. Tell the user to tilt the cube.
- **Phone camera auto white balance and exposure:** lock them in the app if possible, and use the median over the stable window.

### 5.7 Stabilisation (`stabilizer.py`)

- Keep the last N detections (N ≈ 10).
- A face is **stable** when the centre sticker's position moves less than a few pixels, all 9 colours are known, the classifications stay the same across the N frames, and the frame is **sharp**: variance of the Laplacian over the warped face is above a threshold, tuned on the blurry red-face reference photo.
- The captured colours are the per-sticker median over the stable window.
- Feedback for the UI: `too_far` (stickers too small), `too_close`, `hold_still` (moving or blurry), `glare`, `occluded`.

### 5.8 Fallback: guide box

If sticker detection is unreliable in some conditions, add a mode that draws a fixed square on the video, asks the user to fit the face inside it, and warps that region without any detection. It is simple, and useful to have for demos.

---

## 6. Scanning the 6 faces

### 6.1 Orientation convention

The solvers use a 54-character **facelet string** in the order `U R F D L B`, with each face read left to right, top to bottom in this net:

```
             U1 U2 U3
             U4 U5 U6
             U7 U8 U9
 L1 L2 L3    F1 F2 F3    R1 R2 R3    B1 B2 B3
 L4 L5 L6    F4 F5 F6    R4 R5 R6    B4 B5 B6
 L7 L8 L9    F7 F8 F9    R7 R8 R9    B7 B8 B9
             D1 D2 D3
             D4 D5 D6
             D7 D8 D9
```

Faces are named by their **centre colour**. With the standard scheme and the cube held **white on top, green facing the camera**: U = white, F = green, R = red, B = blue, L = orange, D = yellow.

### 6.2 Scan sequence

This order means **every captured image already matches the net orientation, with no rotation correction needed:**

| Step | Face shown | What the app shows the user | Top of image is |
|------|------------|-----------------------------|-----------------|
| 1 | F (green) | "Hold the cube with white on top and green facing the camera" | U |
| 2 | R (red)   | Animation: whole cube turns left (`y`) | U |
| 3 | B (blue)  | Animation: turn left again (`y`) | U |
| 4 | L (orange)| Animation: turn left again (`y`) | U |
| 5 | U (white) | Animation: turn left (back to green), then tip the top toward the camera (`x'`) | B |
| 6 | D (yellow)| Animation: flip the cube over, top away from you (`x2`) | F |

### 6.3 Scan state machine (`scan/session.py`)

```
IDLE → WAITING_FOR_FACE(i) → FACE_STABLE → CAPTURED(i) → ... → REVIEW → VALIDATED → SOLVING
                 ▲                                                  │
                 └──────────── rescan face / manual fix ───────────┘
```

- **Auto-capture** when a stable face shows the **expected centre colour** for this step.
- If the centre colour is wrong: "That's the blue face; turn the cube back one step to show red."
- Manual capture (button or spacebar) and rescanning any face from the review screen.

### 6.4 Validation (`scan/cube_state.py`)

1. Exactly 9 stickers of each colour; 6 different centres.
2. Every edge and corner is a real piece: no piece with a repeated colour or two opposite colours, and no duplicate pieces.
3. Parity: corner twist sum is 0 mod 3, edge flip sum is 0 mod 2, and the corner and edge permutation parities match.
4. If the cube is invalid, try the other 3 rotations of the U and D scans (the ones users most often hold at the wrong angle) and accept a rotation that makes the cube valid.
5. Error messages should point to the face that is probably wrong.

---

## 7. Solvers and methods

The user can't solve a cube yet, so the solver has two jobs: produce a correct solution, and **present it as something a person can learn**. There are three methods behind one interface.

| Method | Moves | Who it's for | What the user learns |
|--------|-------|--------------|----------------------|
| **Beginner** (default) | about 100–150 | first-timers | 8 stages, 5 short algorithms |
| **Intermediate** | about 70–100 | after solving with Beginner a few times | the same first two layers, then a 4-step last layer: 2-look OLL and 2-look PLL, the first step toward CFOP, the method most speedcubers use |
| **Advanced** | about 20 | "just get it solved" | nothing to learn: follow the moves |

### 7.1 Shared interface (`solver/base.py`)

```python
class Move:      notation: str            # "R", "U'", "F2", "r", "M2", "x2", "y"
                 description: str         # "Turn the right face clockwise"
class Stage:     name: str                # "White cross"
                 goal: str                # "Make a white plus sign on the bottom, matching the side centres"
                 explanation: str         # how the stage works, in plain language
                 algorithm: str | None    # "Sune", "T-perm", …
                 tips: list[str]          # "The cube will look messier halfway through; keep going"
                 moves: list[Move]
class Solution:  method: "beginner" | "intermediate" | "advanced"
                 stages: list[Stage]      # advanced = one stage
                 total_moves: int

def solve(facelets: str, method: str) -> Solution
```

**Safety check for every method:** apply the solution to `cube_model.py` and assert the cube ends up solved before sending it to the frontend. If it doesn't, log the scanned state for debugging and show an error instead of a wrong solution. This matters even more because the user can't tell when a solution is wrong.

### 7.2 Cube model (`solver/cube_model.py`)

A 54-facelet array plus permutation tables for:
- the 18 face turns (`U R F D L B`, each with `'` and `2`);
- **wide turns** `u r f d l b`, which turn two layers (some OLL algorithms use them);
- **slice turns** `M E S`, the middle layers (the H-perm and Z-perm use them);
- **whole-cube rotations** `x y z`.

Build the wide turns, slice turns and rotations by combining face-turn permutations, for example `r = R + M'` and `x = R + M' + L'`. The stage engine, the safety check and the tests all use this model. Tests: every move done 4 times gives the identity, `R R'` gives the identity, a known scramble gives a known state, and `M` equals `x' L' R`.

### 7.3 Stage engine (`solver/stage_engine.py`, `search.py`)

Beginner and Intermediate both run on one engine. **A method is an ordered list of stages**, and each stage defines:
- a **goal check** on the cube model ("white cross solved, and everything from earlier stages still solved");
- a **move set**, either single face turns (for the cross) or the stage's named algorithms, each allowed with a `U`, `U'` or `U2` before it (the setup turn, called AUF) and, where needed, from each of the 4 sides;
- a **depth limit** for **IDDFS** (iterative deepening search).

The engine solves the stages in order, adds each stage's moves with its name, explanation and algorithm, and finally tidies the move list (`U U` → `U2`, `U U'` → nothing).

- Keep the search fast in Python by **tracking only the pieces the stage cares about** (for the cross, just the 4 white edges).
- For last-layer stages the search is really **case recognition**: try each algorithm in the set with each of the 4 setup turns, and keep the one that reaches the goal. That is at most about 30 tries.
- This is much less code than a table of every case, the result is correct by construction, and each stage still has its teaching text.

### 7.4 Beginner method (`methods/beginner.py`)

The solution starts with **`z2`**, turning the cube upside down with green still facing you. White is then on the bottom and yellow on top, which is how beginner guides are written.

| # | Stage | Goal | How | Algorithm |
|---|-------|------|-----|-----------|
| 1 | Daisy | 4 white edges around the yellow centre (on top) | search, face turns | none (intuitive) |
| 2 | White cross | turn each "petal" down to the bottom, matched to its side centre | `U` until the petal's side colour matches the centre below, then turn that face twice (`F2`) | none |
| 3 | White corners | first layer complete | put the corner above its slot, then repeat until solved | `R U R' U'` × 1–5 |
| 4 | Middle layer | second-layer edges in place | insert the edge to the right or the left | `U R U' R' U' F' U F` / `U' L' U L U F U' F'` |
| 5 | Yellow cross | yellow plus sign on top (dot → L-shape → line → cross) | | `F R U R' U' F'` |
| 6 | Yellow edges | top edges match the side centres | | `R U R' U R U2 R'` (Sune) |
| 7 | Place yellow corners | corners in the right spots (possibly twisted) | | `U R U' L' U R' U' L` |
| 8 | Twist yellow corners | cube solved | with the unsolved corner at front-right, repeat until its yellow faces up, then `U` to the next corner | `R' D' R D` × 2 or 4 |

The daisy is split out as its own stage because it's the easiest way into the cross for someone who has never solved a cube.

**Stage 8 tip, shown in bold in the UI:** "Halfway through this stage the bottom layers will look scrambled. That's expected: keep going and they fix themselves." This is where most beginners give up.

### 7.5 Intermediate method (`methods/intermediate.py`)

- **Stages 1–4:** the same as Beginner (first two layers).
- **Stage 5, OLL edges (2-look OLL, step 1):** make the yellow cross, with 2 algorithms: the line case and the L-shape case. The dot case uses one after the other.
- **Stage 6, OLL corners (2-look OLL, step 2):** make the whole top yellow, with 7 cases: Sune, Antisune, H, Pi, Headlights, T and Bowtie.
- **Stage 7, PLL corners (2-look PLL, step 1):** put the corners in place, with 2 cases: headlights (T-perm) and diagonal (Y-perm).
- **Stage 8, PLL edges (2-look PLL, step 2):** put the edges in place, with 4 cases: Ua, Ub, H and Z. Finish with a `U` turn if needed.

That's 15 algorithms in total. Put them in `algorithms.py` with their standard names. The UI shows an **algorithm card** for each (name, a picture of the case on the 3D cube, the moves), so what the user learns here carries over to CFOP tutorials later.

### 7.6 Advanced method (`methods/advanced.py`)

- The `kociemba` pip package returns about 20 moves in milliseconds.
- **Windows:** `kociemba` builds a C extension and may need the MSVC Build Tools. The fallback is **`RubikTwoPhase`** (pure Python by Kociemba himself), which generates lookup tables once on first run (a few minutes).
- Returns one stage, "Solve", with move descriptions and the note: "This is the computer's shortest-ish solution. It doesn't follow human steps, so just follow each move carefully."

---

## 8. Backend server and protocol

- **FastAPI + uvicorn.** The camera and vision loop runs in a **background thread**. It writes the latest annotated JPEG and sends events to an `asyncio.Queue` using `loop.call_soon_threadsafe`. The WebSocket handler reads from that queue.
- `GET /video` returns a `StreamingResponse` with `multipart/x-mixed-replace`.
- `WS /ws` carries JSON messages defined as **Pydantic models** in `protocol.py`, mirrored as **TypeScript discriminated unions** in `protocol.ts`. Keep the two in sync by hand, or generate the TS types from the Pydantic JSON schema later.

### Server → client

```ts
type ServerMsg =
  | { type: "detection"; found: boolean; stable: boolean; colors: (Color | null)[]; hint?: Hint }  // ~10 Hz
  | { type: "scan_prompt"; step: number; face: Face; rotation: string | null; text: string }
  | { type: "face_captured"; face: Face; colors: Color[] }
  | { type: "scan_error"; face: Face; message: string }
  | { type: "cube_state"; facelets: string; valid: boolean; errors: string[] }
  | { type: "solution"; method: Method; stages: Stage[]; totalMoves: number }
  | { type: "error"; message: string };
```

### Client → server

```ts
type ClientMsg =
  | { type: "start_scan" }
  | { type: "capture" }
  | { type: "rescan"; face: Face }
  | { type: "set_sticker"; face: Face; index: number; color: Color }
  | { type: "solve"; method: Method }
  | { type: "practice_scramble"; method: Method }   // practice mode: server scrambles + solves
  | { type: "reset" };

type Method = "beginner" | "intermediate" | "advanced";
```

---

## 9. Frontend (TypeScript + Three.js)

### 9.1 Cube model (`CubeModel.ts`)

- 27 cubies at integer positions `x, y, z ∈ {-1, 0, 1}`, spaced slightly apart (about 1.02) so the gaps show.
- Each cubie is a black box with thin sticker planes on its outward faces.
- **Axes:** +x = R, +y = U, +z = F (toward the viewer).

**Facelet → 3D position mapping** (row `r`, column `c` in 0..2, index `3r + c`):

| Face | Sticker on plane | x | y | z |
|------|---------|---|---|---|
| U | y = +1 | c − 1 | 1 | r − 1 |
| D | y = −1 | c − 1 | −1 | 1 − r |
| F | z = +1 | c − 1 | 1 − r | 1 |
| B | z = −1 | 1 − c | 1 − r | −1 |
| R | x = +1 | 1 | 1 − r | 1 − c |
| L | x = −1 | −1 | 1 − r | c − 1 |

Unit test: U9, F3 and R1 must all land on cubie `(1, 1, 1)`.

### 9.2 Moves (`notation.ts`, `MoveAnimator.ts`)

| Move | Axis | Layers | Angle (clockwise) |
|------|------|--------|-------------------|
| U | y | +1 | −90° |
| D | y | −1 | +90° |
| R | x | +1 | −90° |
| L | x | −1 | +90° |
| F | z | +1 | −90° |
| B | z | −1 | +90° |
| M (middle, like L) | x | 0 | +90° |
| E (equator, like D) | y | 0 | +90° |
| S (standing, like F) | z | 0 | −90° |
| r / l | x | {0, +1} / {−1, 0} | −90° / +90° |
| u / d | y | {0, +1} / {−1, 0} | −90° / +90° |
| f / b | z | {0, +1} / {−1, 0} | −90° / +90° |
| x (whole cube, like R) | x | all | −90° |
| y (whole cube, like U) | y | all | −90° |
| z (whole cube, like F) | z | all | −90° |

A prime (`'`) negates the angle, and `2` doubles it. Cubies are chosen by their **current world position**, so moves always mean "the layer on the viewer's right/top/front". After a `z2`, `R` still means the layer on the right, which matches how the user's hands see it.

How to animate a move:
1. Select the cubies whose rounded position on the axis is in the move's layers.
2. `pivot.attach(cubie)` for each (this keeps world transforms).
3. Tween `pivot.rotation[axis]` to the angle over 300–500 ms with easing, using GSAP or a small hand-written tween.
4. `cubeGroup.attach(cubie)` to put them back, then **round positions and snap rotations to multiples of 90°** so floating-point error doesn't build up.
5. Moves play from a queue, one at a time. Stepping backwards plays the inverse move.

---

## 10. Guidance: showing the user what to do

This is the "gesture" part: everything the app shows the user.

### During scanning
- A **looping animation** of the whole-cube rotation needed to reach the next face, with a large curved arrow.
- A text prompt: "Turn the whole cube to the left so the red face is facing the camera."
- Highlight the target face on the 3D cube. Captured faces fill in with their scanned colours.
- Live feedback from the detection hints: "Move closer", "Hold still", "Glare: tilt the cube slightly", "A finger is covering a sticker".
- On the video feed: the detected face outline, the 9 sample points coloured by classification, and the centre sticker highlighted.

### First run: "How to read moves" (`NotationIntro.ts`)
The user has never solved a cube, so move notation needs teaching before the first solve. This is a short interactive introduction on the 3D cube:
1. **Face names:** each face lights up in turn: Front, Right, Up, Back, Left, Down.
2. **Clockwise means clockwise when you look straight at that face.** This is the most common beginner mistake, especially for L, D and B, which turn the "other way" when seen from the front. For each of those, the camera briefly swings round to look at that face, then back.
3. **`'` means anticlockwise, and `2` means turn it twice.**
4. **Try it:** the app shows a move and the user does it on the virtual cube (click and drag, or buttons), until they get 5 right.
5. **Whole-cube rotations** (`x`, `y`, `z`): "turn the whole cube, don't twist a layer".

The introduction can be skipped and can be reopened from the help menu.

### During solving
- **Method picker:** Beginner (default, marked "Start here"), Intermediate or Advanced, each with its move count and a one-line description.
- **Before starting:** an animation of the starting orientation ("White on top, green facing you"), and for Beginner and Intermediate the `z2` flip.
- **At the start of each stage:** a **stage card**, spoken aloud, with "Stage 3 of 8: White corners", the goal, how it works, the algorithm with its name, and tips. It shows a **preview of the cube as it will look when the stage is done**. The user presses "Start stage".
- **For each move:**
  - animate the layer turn on the 3D cube, with a **curved arrow** on the face that turns;
  - text: "Turn the **right** face **clockwise** (R)". Wide and slice moves say "Turn the right **two layers** clockwise (r)" and "Turn the **middle layer** down, the same way as L (M)";
  - **speech (on by default):** the same sentence read out with `speechSynthesis`;
  - wait for the user to press next (button, spacebar, or → key), or auto-play at an adjustable speed;
  - within an algorithm, show where the user is ("Sune: move 4 of 7"), and for repeated algorithms, which repetition ("`R U R' U'`: repetition 2 of 5").
- **The move list is grouped by stage**, with a progress bar across all stages.
- **Speech details:**
  - a speaker toggle in the header, remembered in `localStorage` (on by default);
  - browsers don't allow speech until the user has interacted with the page, so the first "Start" click also unlocks speech;
  - `speechSynthesis.cancel()` before each new phrase so fast clicking doesn't pile up a queue;
  - use an English voice where one is available, and slow the rate slightly (about 0.95).
- A **replay** button for the current move, and **step back**.
- A camera **reset view** button (OrbitControls, with a default view showing U, F and R).

### Stretch
- **AR arrows on the video feed:** use the homography from the live detection to draw the turn arrow on the real cube face in OpenCV.
- **Automatic next step:** compare the live front face with the expected state after the current move, and move on automatically when they match.

---

## 11. Implementation phases

Each phase ends with something you can run and check.

| # | Phase | Done when |
|---|-------|-----------|
| 0 | **Setup** | Python 3.10/3.11 venv; `pip install opencv-python cvzone numpy scipy kociemba fastapi uvicorn pydantic`. `npm create vite@latest frontend -- --template vanilla-ts`; `npm i three @types/three`. `list_cameras.py` finds Iriun. Record 2–3 scanning videos with `record.py`. Photograph the yellow face. |
| 1 | **Sticker detection** | The debug view shows edges, candidates and deduped stickers. At least 5 stickers are found on **every reference photo** and on most frames of the recorded videos. |
| 2 | **Grid fit + homography + warp** | The centre is found correctly, the flat 300×300 face and the reprojected outline look right, and it still works with 2 stickers covered. |
| 3 | **Colour classification** | Calibration saved. **All reference photos match `labels.json`.** The blurry red-face photo is flagged by the sharpness check. |
| 4 | **Cube model + validation + advanced solver** | `cube_model.py` tests pass, including wide and slice moves. The round-trip test (random scramble → solve → apply → solved) passes 500 times. |
| 5 | **Scan + solve in the terminal** | Guided 6-face scan in an OpenCV window, then a printed solution. **This is the core MVP.** |
| 6 | **Stage engine + Beginner method** | All 8 stages; round-trip passes 500 times; each solve takes under about 2 s. |
| 7 | **Intermediate method** | 15 algorithms in `algorithms.py`; round-trip passes 500 times; every OLL and PLL case is reached at least once in tests. |
| 8 | **Server** | FastAPI with `/video` and `/ws`; typed messages; the browser shows the stream and logs events. |
| 9 | **3D cube + animation** | Any facelet string renders correctly; every move in 9.2 animates; a scramble followed by its inverse gives a solved cube. |
| 10 | **Practice mode + notation introduction** | Scramble a virtual cube, pick a method, and play the solution with stage cards and speech, with no camera. **This is where you learn to solve a cube yourself.** |
| 11 | **Guidance UI** | Scan guidance, review with manual fix, and the solve player. Full run from a real scrambled cube to solved, following the app. |
| 12 | **Polish** | Error states, lighting hints, README. Then stretch goals. |

Phases 6–7 (methods) and 9–10 (frontend) don't depend on the vision work, so they can be done in parallel with phases 1–3, or first if the vision side gets stuck.

---

## 12. Testing strategy

- **Python unit tests:**
  - lattice fitting on synthetic point sets (rotated, with missing and extra points);
  - homography and warp on synthetic images;
  - the constrained colour assignment on noisy colours;
  - validation cases: a good cube, a flipped edge, a twisted corner, swapped pieces;
  - cube model identities;
  - solver round trips for all 3 methods;
  - each named algorithm solves its own case: apply the inverse of the algorithm to a solved cube, and check that the stage engine picks that algorithm.
- **Reference photo tests:** run detection and classification on `referenceImages/` and compare with `labels.json` (5.0). Add the yellow face and more photos (other lighting, other angles) over time.
- **Replay tests:** run the whole pipeline on the recorded videos and compare against hand-labelled facelet strings. Re-run after any threshold change.
- **Beginner usability test:** you are the ideal tester, because you can't solve a cube yet. If you can solve a scrambled cube by following the app, the guidance works. Note every point where you got confused and fix the wording or animation there.
- **TypeScript unit tests (Vitest):** facelet → cubie mapping, notation parsing, move descriptions, and scramble followed by its inverse.
- **Manual end-to-end checklist:** daylight, warm indoor light, dim light, a busy background, Iriun over USB and over Wi-Fi.

---

## 13. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Neighbouring stickers merge | The reference photos show clear gaps, so this is low risk. Still use at most 1 small dilation, and keep the face at about 30–50% of the frame width |
| Background texture (wood grain) creates false candidates | Size, squareness and similar-area filters, plus the grid fit; recommend a plain background |
| Motion blur and glare | Sharpness check before capture; glare mask before taking the median |
| The user can't spot a wrong solution or a wrong move they made | Safety check before sending any solution; step-back and replay; the "cube looks messy halfway" tips; stretch goal: camera-based move verification |
| The user turns a face the wrong way (L, D, B) | The notation introduction; arrows drawn on the turning face; the camera swings round for back-facing moves |
| Stickers of the same colour next to each other lose the edge between them | The grid fit needs only 5 stickers; the homography predicts where the missing ones are |
| Red/orange or white/yellow confusion | LAB, calibration, constrained assignment, manual fix UI |
| User holds a face at the wrong angle | Fixed scan order with animations, centre-colour check, trying U/D rotations when validation fails |
| Iriun latency, dropped frames or mirroring | USB connection, `FLIP_HORIZONTAL` flag, capture thread always keeps only the latest frame |
| Phone auto exposure and white balance | Lock in the app if possible; median over the stable window |
| Beginner search is slow in Python | Track only the pieces relevant to each stage, small move sets, one edge at a time for the cross |
| `kociemba` install fails on Windows | MSVC Build Tools, or `RubikTwoPhase` |
| Floating-point drift in Three.js | Snap positions and rotations after every move |

---

## 14. Remaining open questions

None that block the work. Things to do:
1. **Photograph the yellow face** and add it to `referenceImages/`. It should contain 1 red, 2 blue, 4 yellow and 2 green stickers (see 5.0).
2. When recording the scan sessions (phase 0), use the Iriun set-up you will actually use (phone on a stand, your normal lighting), since these recordings become the main test data.
