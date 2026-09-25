"""Runtime settings. Override any of them in ``backend/.env`` or with environment variables
of the same name (a variable set in the shell wins over the file)."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BACKEND_DIR / ".env", override=False)


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


# Camera: an integer webcam index (Iriun shows up as one; find it with tools/list_cameras.py)
# or a path to a video file for replay.
CAMERA_SOURCE: int | str = int(_env("CAMERA_SOURCE", "0")) if _env("CAMERA_SOURCE", "0").isdigit() \
    else _env("CAMERA_SOURCE", "0")
CAMERA_WIDTH = int(_env("CAMERA_WIDTH", "1280"))
CAMERA_HEIGHT = int(_env("CAMERA_HEIGHT", "720"))
# Iriun can mirror the picture. The vision pipeline must see the unmirrored image.
FLIP_HORIZONTAL = _env("FLIP_HORIZONTAL", "0") == "1"
# Loop a video file source instead of stopping at its end.
LOOP_VIDEO = _env("LOOP_VIDEO", "1") == "1"

# Detection runs on a copy downscaled to this width; colours are sampled at full resolution.
DETECT_WIDTH = 640

# Sticker filter (5.2)
MIN_STICKER_FRAC = 0.035   # sticker side, as a fraction of frame width
MAX_STICKER_FRAC = 0.22
MIN_FILL_RATIO = 0.8
ASPECT_RANGE = (0.75, 1.33)
AREA_TOLERANCE = 0.4       # keep candidates within +-40% of the median area
BODY_MAX_V = 90            # HSV value below which a pixel counts as black cube body

# Grid fit (5.3)
MIN_INLIERS = 5
MAX_ROUNDING_ERROR = 0.3   # in units of grid spacing

# Sampling and colour (5.5, 5.6)
UNKNOWN_DISTANCE = 36.0    # feature distance (vision/color.py) beyond which a sticker is "unknown"
GLARE_FRACTION = 0.4

# Stabiliser (5.7)
STABLE_FRAMES = 10
MAX_CENTRE_MOVE = 0.12     # in units of grid spacing
MIN_SHARPNESS = float(_env("MIN_SHARPNESS", "10"))  # variance of the Laplacian over the warped face; tune on video
TOO_FAR_FRAC = 0.06        # grid spacing below this fraction of frame width -> "move closer"
TOO_CLOSE_FRAC = 0.24

COLORS_FILE = Path(_env("COLORS_FILE", str(BACKEND_DIR / "colors.json")))
