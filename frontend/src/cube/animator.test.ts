import { expect, it } from "vitest";
import { CubeModel } from "./CubeModel";
import { applyMoves, SOLVED } from "./facelets";
import { MoveAnimator } from "./MoveAnimator";
import { invertAlg, randomScramble } from "./notation";

const ALL = ["U", "D", "R", "L", "F", "B", "M", "E", "S", "r", "l", "u", "d", "f", "b", "x", "y", "z"]
  .flatMap((m) => [m, m + "'", m + "2"]);

function setup() {
  const cube = new CubeModel();
  cube.setFacelets(SOLVED, () => "#000");
  return { cube, anim: new MoveAnimator(cube) };
}

it("every move turns the 3D cube the same way as the facelet model", async () => {
  for (const m of ALL) {
    const { cube, anim } = setup();
    const scramble = ["R", "U", "F'", "L2", "D"]; // make the state asymmetric first
    await anim.jump([...scramble, m]);
    expect(cube.readState(SOLVED), m).toBe(applyMoves(SOLVED, [...scramble, m]));
  }
});

it("a scramble followed by its inverse leaves the 3D cube solved", async () => {
  const { cube, anim } = setup();
  const sc = randomScramble(30);
  await anim.jump(sc);
  expect(cube.readState(SOLVED)).toBe(applyMoves(SOLVED, sc));
  await anim.jump(invertAlg(sc));
  expect(cube.readState(SOLVED)).toBe(SOLVED);
  // Snapping keeps every cubie exactly on the integer lattice.
  for (const c of cube.cubies) for (const v of c.position.toArray()) expect(Number.isInteger(v)).toBe(true);
});
