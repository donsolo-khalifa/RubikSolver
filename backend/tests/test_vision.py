import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.vision import color
from app.vision.lattice import fit_grid
from app.vision.pipeline import Pipeline
from app.vision.sticker_detector import Candidate, detect_stickers
from app.vision.warp import cell_center, warp_face

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "referenceImages"
LABELS = json.loads((Path(__file__).parent / "fixtures" / "labels.json").read_text())["images"]


# --- reference photos ---------------------------------------------------------
@pytest.mark.parametrize("name", sorted(LABELS))
def test_reference_photo_detection_and_colours(name):
    img = cv2.imread(str(REF / name))
    assert img is not None, f"missing {name}"
    assert len(detect_stickers(img).candidates) >= 5
    det = Pipeline().process(img)
    assert det.found
    assert "".join(c or "?" for c in det.colors) == LABELS[name]["stickers"]
    assert det.colors[4] == LABELS[name]["centre"]


# --- synthetic lattice --------------------------------------------------------
def _cands(points, size=40.0, angle=0.0):
    return [Candidate(np.array(p, float), size, angle, size * size, np.zeros((4, 2))) for p in points]


def _grid(angle_deg=0.0, spacing=50.0, origin=(300, 200), cells=None):
    t = np.deg2rad(angle_deg)
    u = np.array([np.cos(t), np.sin(t)])
    v = np.array([-np.sin(t), np.cos(t)])
    cells = cells if cells is not None else [(r, c) for r in range(3) for c in range(3)]
    return {(r, c): np.array(origin) + spacing * ((c - 1) * u + (r - 1) * v) for r, c in cells}


@pytest.mark.parametrize("angle", [0, 12, -20, 40])
def test_lattice_rotated(angle):
    g = _grid(angle)
    fit = fit_grid(_cands(g.values(), angle=angle))
    assert fit is not None and len(fit.cells) == 9
    for key, cand in fit.cells.items():
        assert np.allclose(cand.center, g[key])


def test_lattice_missing_centre_and_extra_points():
    g = _grid(8, cells=[(0, 0), (0, 1), (0, 2), (1, 0), (2, 0), (2, 2)])
    noise = [(40, 40), (600, 30), (320, 420)]
    fit = fit_grid(_cands([*g.values(), *noise], angle=8))
    assert fit is not None and fit.center is None
    assert set(fit.cells) == set(g)
    assert np.allclose(fit.origin, (300, 200), atol=1)


def test_lattice_rejects_too_few():
    g = _grid(cells=[(0, 0), (0, 1), (0, 2), (1, 0)])
    assert fit_grid(_cands(g.values())) is None


# --- synthetic warp -----------------------------------------------------------
def test_warp_recovers_face_colours():
    img = np.full((600, 800, 3), 200, np.uint8)
    colours = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 255, 255), (255, 255, 255),
               (0, 128, 255), (255, 0, 255), (128, 128, 0), (0, 0, 128)]
    g = _grid(10, spacing=70, origin=(400, 300))
    for (r, c), p in g.items():
        box = cv2.boxPoints(((p[0], p[1]), (58, 58), 10))
        cv2.fillConvexPoly(img, np.int32(box), colours[3 * r + c])
    fit = fit_grid(_cands(g.values(), size=58, angle=10))
    w = warp_face(img, fit)
    for i, col in enumerate(colours):
        x, y = cell_center(i // 3, i % 3)
        assert np.abs(w.face[int(y), int(x)].astype(int) - col).max() < 10
    assert np.allclose(w.cell_points[4], (400, 300), atol=1.5)


# --- colour assignment --------------------------------------------------------
def test_constrained_assignment_fixes_ambiguous_stickers():
    refs = color.load_references(color.DEFAULT_COLORS_FILE)
    rng = np.random.default_rng(0)
    order = "WRGYOB"  # centre colours of U R F D L B
    pool = list(rng.permutation([c for c in order for _ in range(8)]))
    labels = [order[i // 9] if i % 9 == 4 else pool.pop() for i in range(54)]
    labs = np.array([refs[c] + rng.normal(0, 4, 3) for c in labels])
    # Make one red sticker look orange-ish: halfway between the two.
    red = next(i for i, c in enumerate(labels) if c == "R" and i % 9 != 4)
    labs[red] = 0.55 * refs["R"] + 0.45 * refs["O"]
    got = color.assign_all(labs)
    assert [order[k] for k in got] == labels
