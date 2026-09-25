import { describe as suite, expect, it } from "vitest";
import { describe } from "../guidance/describe";
import { applyMoves, GEOMETRY, isSolved, SOLVED } from "./facelets";
import { invertAlg, invertMove, parseAlg, parseMove, randomScramble } from "./notation";

const idx = (name: string) => 9 * "URFDLB".indexOf(name[0]) + Number(name[1]) - 1;

suite("facelet -> cubie mapping", () => {
  it("puts U9, F3 and R1 on cubie (1, 1, 1)", () => {
    for (const n of ["U9", "F3", "R1"]) expect(GEOMETRY[idx(n)].pos).toEqual([1, 1, 1]);
  });
  it("puts D1, F7 and L9 on cubie (-1, -1, 1)", () => {
    for (const n of ["D1", "F7", "L9"]) expect(GEOMETRY[idx(n)].pos).toEqual([-1, -1, 1]);
  });
});

suite("notation", () => {
  it("parses face, wide, slice and rotation moves", () => {
    expect(parseMove("R2")).toMatchObject({ axis: "x", layers: [1], quarters: -2 });
    expect(parseMove("U'")).toMatchObject({ axis: "y", layers: [1], quarters: 1 });
    expect(parseMove("M")).toMatchObject({ axis: "x", layers: [0], quarters: 1 });
    expect(parseMove("r")).toMatchObject({ axis: "x", layers: [0, 1], quarters: -1 });
    expect(parseMove("x'")).toMatchObject({ axis: "x", layers: [-1, 0, 1], quarters: 1 });
  });
  it("rejects nonsense", () => {
    expect(() => parseMove("Q")).toThrow();
    expect(() => parseAlg("R U3")).toThrow();
  });
  it("inverts", () => {
    expect(invertMove("R")).toBe("R'");
    expect(invertMove("R'")).toBe("R");
    expect(invertMove("R2")).toBe("R2");
    expect(invertAlg(["R", "U", "F'"])).toEqual(["F", "U'", "R'"]);
  });
});

suite("facelet model", () => {
  const all = ["U", "D", "R", "L", "F", "B", "M", "E", "S", "r", "l", "u", "d", "f", "b", "x", "y", "z"];
  it("every move done 4 times is the identity", () => {
    for (const m of all) expect(applyMoves(SOLVED, [m, m, m, m])).toBe(SOLVED);
  });
  it("scramble then inverse is solved", () => {
    for (let i = 0; i < 50; i++) {
      const sc = randomScramble(25);
      expect(applyMoves(applyMoves(SOLVED, sc), invertAlg(sc))).toBe(SOLVED);
    }
  });
  it("agrees with the backend on a known state (kociemba's example)", () => {
    const state = "DRLUUBFBRBLURRLRUBLRDDFDLFUFUFFDBRDUBRUFLLFDDBFLUBLRBD";
    const sol = parseAlg("D2 R' D' F2 B D R2 D2 R' F2 D' F2 U' B2 L2 U2 D R2 U");
    expect(applyMoves(state, sol)).toBe(SOLVED);
  });
  it("M equals x' L' R", () => {
    const s = applyMoves(SOLVED, ["R", "U2", "F'"]);
    expect(applyMoves(s, ["M"])).toBe(applyMoves(s, ["x'", "L'", "R"]));
  });
  it("is solved after a whole-cube rotation", () => {
    expect(isSolved(applyMoves(SOLVED, ["z2", "y"]))).toBe(true);
    expect(isSolved(applyMoves(SOLVED, ["R"]))).toBe(false);
  });
});

suite("move descriptions", () => {
  it("describes each kind of move", () => {
    expect(describe("R'").text).toBe("Turn the right face anticlockwise");
    expect(describe("U2").text).toBe("Turn the top face twice (a half turn)");
    expect(describe("r").text).toBe("Turn the right two layers clockwise");
    expect(describe("M").text).toBe("Turn the middle layer down, the same way as L");
    expect(describe("y").text).toMatch(/whole cube to the left/);
    expect(describe("R").html).toContain("<strong>right</strong>");
  });
});
