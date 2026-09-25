// "R'" -> "Turn the right face anticlockwise". Mirrors backend/app/solver/describe.py,
// with an HTML version that bolds the key words (PLAN.md 10).
import { parseMove } from "../cube/notation";
import type { Move } from "../net/protocol";

const FACE: Record<string, string> = { U: "top", D: "bottom", R: "right", L: "left", F: "front", B: "back" };

const SLICE: Record<string, { layer: string; like: string; dir: Record<number, string> }> = {
  M: { layer: "middle layer", like: "L", dir: { 1: "down", 3: "up" } },
  E: { layer: "middle horizontal layer", like: "D", dir: { 1: "to the right", 3: "to the left" } },
  S: { layer: "middle layer (between front and back)", like: "F", dir: { 1: "clockwise", 3: "anticlockwise" } },
};

const ROTATION: Record<string, Record<number, string>> = {
  x: {
    1: "Tip the whole cube back, so the front face goes to the top",
    3: "Tip the whole cube forward, so the top face comes to the front",
    2: "Flip the whole cube over, top away from you",
  },
  y: {
    1: "Turn the whole cube to the left, so the right face comes to the front",
    3: "Turn the whole cube to the right, so the left face comes to the front",
    2: "Turn the whole cube around, so the back face comes to the front",
  },
  z: {
    1: "Tilt the whole cube to the right (clockwise as seen from the front)",
    3: "Tilt the whole cube to the left (anticlockwise as seen from the front)",
    2: "Turn the whole cube upside down, keeping the front facing you",
  },
};

/** Clockwise quarter turns: 1, 2 or 3. */
function amountOf(notation: string): number {
  const suffix = notation.slice(1);
  return suffix === "" ? 1 : suffix.startsWith("2") || suffix.endsWith("2") ? 2 : 3;
}

const dirWord = (a: number) => ({ 1: "clockwise", 3: "anticlockwise", 2: "twice (a half turn)" })[a]!;

export interface Description {
  text: string; // plain, for speech
  html: string; // with the key words bold
}

export function describe(notation: string): Description {
  const { base } = parseMove(notation);
  const a = amountOf(notation);
  const b = (s: string) => `<strong>${s}</strong>`;
  const code = `<code>${notation}</code>`;
  if (FACE[base]) {
    return {
      text: `Turn the ${FACE[base]} face ${dirWord(a)}`,
      html: `Turn the ${b(FACE[base])} face ${b(dirWord(a))} (${code})`,
    };
  }
  if (FACE[base.toUpperCase()]) {
    const f = FACE[base.toUpperCase()];
    return {
      text: `Turn the ${f} two layers ${dirWord(a)}`,
      html: `Turn the ${b(f)} ${b("two layers")} ${b(dirWord(a))} (${code})`,
    };
  }
  if (SLICE[base]) {
    const s = SLICE[base];
    if (a === 2) return { text: `Turn the ${s.layer} twice`, html: `Turn the ${b(s.layer)} ${b("twice")} (${code})` };
    const like = a === 1 ? s.like : s.like + "'";
    return {
      text: `Turn the ${s.layer} ${s.dir[a]}, the same way as ${like}`,
      html: `Turn the ${b(s.layer)} ${b(s.dir[a])}, the same way as ${like} (${code})`,
    };
  }
  const t = ROTATION[base][a];
  return { text: t, html: `${t.replace("whole cube", b("whole cube"))} (${code})` };
}

/** "Sune: move 4 of 7" / "R U R' U': repetition 2 of 5". */
export function progressLabel(m: Move): string | null {
  if (!m.algorithm) return null;
  const parts = [`${m.algorithm}: move ${m.step} of ${m.steps}`];
  if (m.reps && m.reps > 1) parts.push(`repetition ${m.rep} of ${m.reps}`);
  return parts.join(" · ");
}
