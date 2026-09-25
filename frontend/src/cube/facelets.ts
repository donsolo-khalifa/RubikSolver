// Facelet-string model (no Three.js): positions, move permutations, previews.
// Same geometry as backend/app/solver/cube_model.py, so both sides agree by construction.
import { parseMove, type Axis } from "./notation";

export type Vec3 = [number, number, number];
export const FACE_ORDER = "URFDLB";
export const SOLVED = FACE_ORDER.split("").map((f) => f.repeat(9)).join("");

/** Cubie position and outward normal of facelet (row r, col c) on a face (PLAN.md 9.1). */
export function faceletGeometry(face: string, r: number, c: number): { pos: Vec3; normal: Vec3 } {
  switch (face) {
    case "U": return { pos: [c - 1, 1, r - 1], normal: [0, 1, 0] };
    case "D": return { pos: [c - 1, -1, 1 - r], normal: [0, -1, 0] };
    case "F": return { pos: [c - 1, 1 - r, 1], normal: [0, 0, 1] };
    case "B": return { pos: [1 - c, 1 - r, -1], normal: [0, 0, -1] };
    case "R": return { pos: [1, 1 - r, 1 - c], normal: [1, 0, 0] };
    case "L": return { pos: [-1, 1 - r, c - 1], normal: [-1, 0, 0] };
  }
  throw new Error(`bad face ${face}`);
}

export const GEOMETRY = Array.from({ length: 54 }, (_, i) =>
  faceletGeometry(FACE_ORDER[Math.floor(i / 9)], Math.floor((i % 9) / 3), i % 3),
);

const key = (p: Vec3, n: Vec3) => `${p.join(",")}|${n.join(",")}`;
const INDEX = new Map(GEOMETRY.map((g, i) => [key(g.pos, g.normal), i]));
const AXIS_INDEX: Record<Axis, number> = { x: 0, y: 1, z: 2 };

export function rotateVec(v: Vec3, axis: Axis, quarters: number): Vec3 {
  const q = ((quarters % 4) + 4) % 4;
  const cos = [1, 0, -1, 0][q];
  const sin = [0, 1, 0, -1][q];
  const [x, y, z] = v;
  const r: Vec3 =
    axis === "x" ? [x, y * cos - z * sin, y * sin + z * cos]
    : axis === "y" ? [x * cos + z * sin, y, -x * sin + z * cos]
    : [x * cos - y * sin, x * sin + y * cos, z];
  return r.map((n) => n + 0) as Vec3; // normalise -0
}

const permCache = new Map<string, number[]>();

/** perm such that new[j] = old[perm[j]]. */
export function permutation(move: string): number[] {
  let perm = permCache.get(move);
  if (perm) return perm;
  const { axis, layers, quarters } = parseMove(move);
  const a = AXIS_INDEX[axis];
  perm = Array.from({ length: 54 }, (_, i) => i);
  GEOMETRY.forEach(({ pos, normal }, i) => {
    if (!layers.includes(pos[a])) return;
    const j = INDEX.get(key(rotateVec(pos, axis, quarters), rotateVec(normal, axis, quarters)));
    if (j === undefined) throw new Error("geometry error");
    perm![j] = i;
  });
  permCache.set(move, perm);
  return perm;
}

export function applyMoves(state: string, moves: string[]): string {
  let s = state.split("");
  for (const m of moves) {
    const p = permutation(m);
    s = p.map((i) => s[i]);
  }
  return s.join("");
}

export function isSolved(state: string): boolean {
  for (let f = 0; f < 6; f++) {
    const face = state.slice(9 * f, 9 * f + 9);
    if (face.split("").some((c) => c !== face[0])) return false;
  }
  return true;
}
