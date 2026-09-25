// Move notation -> {axis, layers, angle} (PLAN.md 9.2). Axes: +x = R, +y = U, +z = F.

export type Axis = "x" | "y" | "z";

export interface MoveSpec {
  notation: string;
  base: string;
  axis: Axis;
  layers: number[];
  /** Quarter turns, right-hand rule about +axis (clockwise U is -1). */
  quarters: number;
  angle: number; // radians
}

const BASE: Record<string, [Axis, number[], number]> = {
  U: ["y", [1], -1], D: ["y", [-1], 1],
  R: ["x", [1], -1], L: ["x", [-1], 1],
  F: ["z", [1], -1], B: ["z", [-1], 1],
  M: ["x", [0], 1], E: ["y", [0], 1], S: ["z", [0], -1],
  r: ["x", [0, 1], -1], l: ["x", [-1, 0], 1],
  u: ["y", [0, 1], -1], d: ["y", [-1, 0], 1],
  f: ["z", [0, 1], -1], b: ["z", [-1, 0], 1],
  x: ["x", [-1, 0, 1], -1], y: ["y", [-1, 0, 1], -1], z: ["z", [-1, 0, 1], -1],
};

const AMOUNT: Record<string, number> = { "": 1, "'": -1, "2": 2, "2'": -2, "'2": -2 };

export function parseMove(notation: string): MoveSpec {
  const base = notation[0];
  const suffix = notation.slice(1);
  const spec = BASE[base];
  const amount = AMOUNT[suffix];
  if (!spec || amount === undefined) throw new Error(`unknown move "${notation}"`);
  const [axis, layers, q] = spec;
  const quarters = q * amount;
  return { notation, base, axis, layers, quarters, angle: (quarters * Math.PI) / 2 };
}

export function parseAlg(alg: string): string[] {
  const moves = alg.trim().split(/\s+/).filter(Boolean);
  moves.forEach(parseMove); // validate
  return moves;
}

export function invertMove(notation: string): string {
  const { base } = parseMove(notation);
  const suffix = notation.slice(1);
  if (suffix === "" ) return base + "'";
  if (suffix === "'") return base;
  return base + "2";
}

export function invertAlg(moves: string[]): string[] {
  return [...moves].reverse().map(invertMove);
}

export function isRotation(notation: string): boolean {
  return "xyz".includes(notation[0]);
}

export const FACE_MOVES = ["U", "R", "F", "D", "L", "B"].flatMap((f) => [f, f + "'", f + "2"]);

export function randomScramble(length = 20, rand: () => number = Math.random): string[] {
  const out: string[] = [];
  let last = "";
  const faces = ["U", "R", "F", "D", "L", "B"];
  while (out.length < length) {
    const f = faces[Math.floor(rand() * 6)];
    if (f === last) continue;
    out.push(f + ["", "'", "2"][Math.floor(rand() * 3)]);
    last = f;
  }
  return out;
}
