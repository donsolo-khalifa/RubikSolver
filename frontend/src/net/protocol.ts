// WebSocket message types. Mirrors backend/app/protocol.py: keep the two in sync.

export type Color = "W" | "Y" | "R" | "O" | "G" | "B";
export type Face = "U" | "R" | "F" | "D" | "L" | "B";
export type Method = "beginner" | "intermediate" | "advanced";
export type Hint = "too_far" | "too_close" | "hold_still" | "glare" | "occluded";
export type Phase = "idle" | "scanning" | "review" | "solving";

export interface Move {
  notation: string;
  description: string;
  algorithm: string | null;
  step: number | null;
  steps: number | null;
  rep: number | null;
  reps: number | null;
}

export interface Stage {
  name: string;
  goal: string;
  explanation: string;
  algorithm: string | null;
  tips: string[];
  moves: Move[];
}

export type ServerMsg =
  | { type: "detection"; found: boolean; stable: boolean; colors: (Color | null)[]; hint: Hint | null }
  | { type: "scan_prompt"; step: number; face: Face; rotation: string | null; text: string }
  | { type: "face_captured"; face: Face; colors: Color[] }
  | { type: "scan_error"; face: Face; message: string }
  | { type: "cube_state"; facelets: string; valid: boolean; errors: string[]; note: string | null }
  | { type: "solution"; method: Method; stages: Stage[]; totalMoves: number; facelets: string }
  | { type: "practice"; scramble: string[]; facelets: string }
  | { type: "status"; camera: boolean; phase: Phase }
  | { type: "error"; message: string };

export type ClientMsg =
  | { type: "start_scan" }
  | { type: "capture" }
  | { type: "rescan"; face: Face }
  | { type: "set_sticker"; face: Face; index: number; color: Color }
  | { type: "solve"; method: Method }
  | { type: "practice_scramble"; method: Method }
  | { type: "reset" };

export type SolutionMsg = Extract<ServerMsg, { type: "solution" }>;

// Standard scheme with the cube held white on top, green facing the camera.
export const SCHEME: Record<Face, Color> = { U: "W", R: "R", F: "G", D: "Y", L: "O", B: "B" };
export const FACES: Face[] = ["U", "R", "F", "D", "L", "B"];
export const COLOR_NAMES: Record<Color, string> = {
  W: "white", Y: "yellow", R: "red", O: "orange", G: "green", B: "blue",
};
export const COLOR_HEX: Record<Color, string> = {
  W: "#f4f4f0", Y: "#ffd500", R: "#d0203a", O: "#ff6a13", G: "#1faa55", B: "#1466d8",
};
export const UNKNOWN_HEX = "#4a4f59";
