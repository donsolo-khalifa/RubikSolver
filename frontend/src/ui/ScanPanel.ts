// Guided 6-face scan: live video, prompts, hints, and the 3D cube showing how to turn it.
import { parseAlg } from "../cube/notation";
import { speech } from "../guidance/speech";
import { COLOR_HEX, COLOR_NAMES, FACES, SCHEME, UNKNOWN_HEX, type Color, type Face, type Hint, type ServerMsg } from "../net/protocol";
import type { App } from "./app";
import { colorLetterColor } from "./diagrams";
import { h, type Panel } from "./dom";

// Rotation shown before each step (PLAN.md 6.2); index = step.
const STEP_ROTATIONS = [null, "y", "y", "y", "y x'", "x2"];
const STEP_FACES: Face[] = ["F", "R", "B", "L", "U", "D"];

const HINT_TEXT: Record<Hint, string> = {
  too_far: "Move the cube closer to the camera",
  too_close: "Move the cube a little further away",
  hold_still: "Hold still…",
  glare: "Glare on a sticker: tilt the cube slightly",
  occluded: "A finger is covering a sticker",
};

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export class ScanPanel implements Panel {
  el = h("div", { class: "panel scan" });
  private video = h("img", { class: "video", alt: "Live camera view with the detected face outlined" }) as HTMLImageElement;
  private steps = h("ol", { class: "scan-steps", "aria-label": "Faces to scan" });
  private prompt = h("p", { class: "prompt" }, "Connecting…");
  private hint = h("p", { class: "hint" });
  private warn = h("p", { class: "warn", role: "status" });
  private live = h("div", { class: "live-grid", "aria-hidden": "true" });
  private step = 0;
  private captured = new Map<Face, Color[]>();
  private offs: (() => void)[] = [];
  private loopId = 0;
  private onKey = (e: KeyboardEvent) => {
    if (e.key === " " && !document.querySelector(".modal")) {
      e.preventDefault();
      this.app.socket.send({ type: "capture" });
    }
  };

  constructor(private app: App, private rescanFace?: Face) {
    for (let i = 0; i < 9; i++) this.live.append(h("span"));
    this.el.append(
      h("div", { class: "video-wrap" }, this.video, this.live),
      this.steps,
      this.prompt,
      this.hint,
      this.warn,
      h("div", { class: "row" },
        h("button", { class: "primary", onclick: () => app.socket.send({ type: "capture" }), title: "Capture this face now (Space)" }, "Capture now"),
        h("button", { onclick: () => app.startScan() }, "Restart scan"),
      ),
      h("p", { class: "muted small" }, "Tips: plain background, soft even light, cube about 30–40 cm from the phone. A face is captured automatically once it's held steady."),
    );
    this.renderSteps();
  }

  mount(): void {
    this.video.src = `/video?t=${Date.now()}`;
    document.addEventListener("keydown", this.onKey);
    const s = this.app.socket;
    this.offs.push(
      s.on("scan_prompt", (m) => this.onPrompt(m)),
      s.on("detection", (m) => this.onDetection(m)),
      s.on("face_captured", (m) => {
        this.captured.set(m.face, m.colors);
        this.warn.textContent = "";
        this.renderSteps();
      }),
      s.on("scan_error", (m) => {
        this.warn.textContent = m.message;
        speech.say(m.message);
      }),
    );
    if (!this.app.cameraOk) this.warn.textContent = "The backend has no camera. Check CAMERA_SOURCE (see tools/list_cameras.py).";
    if (this.rescanFace) this.app.socket.send({ type: "rescan", face: this.rescanFace });
    else this.app.socket.send({ type: "start_scan" });
  }

  unmount(): void {
    this.video.src = "";
    this.loopId++;
    this.offs.forEach((off) => off());
    document.removeEventListener("keydown", this.onKey);
    this.app.view.arrow.hide();
    this.app.view.cube.highlight([]);
  }

  private onPrompt(m: Extract<ServerMsg, { type: "scan_prompt" }>): void {
    this.step = m.step;
    this.warn.textContent = "";
    this.prompt.textContent = m.text;
    this.renderSteps();
    speech.say(m.text);
    void this.guide();
  }

  private onDetection(m: Extract<ServerMsg, { type: "detection" }>): void {
    const cells = this.live.children;
    m.colors.forEach((c, i) => ((cells[i] as HTMLElement).style.background = c ? COLOR_HEX[c] : "transparent"));
    this.live.classList.toggle("on", m.found);
    // The right face is back in view: the "wrong face" warning no longer applies.
    if (m.found && m.colors[4] === SCHEME[STEP_FACES[this.step]]) this.warn.textContent = "";
    this.live.classList.toggle("stable", m.stable);
    this.hint.textContent = !m.found
      ? `Show the ${COLOR_NAMES[SCHEME[STEP_FACES[this.step]]]} face to the camera`
      : m.hint ? HINT_TEXT[m.hint] : m.stable ? "Got it…" : "Hold steady…";
    this.hint.className = `hint${m.hint ? " bad" : m.found ? " ok" : ""}`;
  }

  /** Colour-letter facelets for the 3D cube: captured faces in colour, the rest grey. */
  private scanState(): string {
    return FACES.map((f) => {
      const cols = this.captured.get(f);
      if (cols) return cols.join("");
      return "????" + SCHEME[f] + "????";
    }).join("");
  }

  /** Loop the whole-cube rotation that leads to this step's face, with an arrow. */
  private async guide(): Promise<void> {
    const id = ++this.loopId;
    const view = this.app.view;
    const before = STEP_ROTATIONS.slice(1, this.step).flatMap((r) => (r ? parseAlg(r) : []));
    const rot = STEP_ROTATIONS[this.step];
    const target = FACES.indexOf(STEP_FACES[this.step]);
    view.cube.highlight(Array.from({ length: 9 }, (_, i) => 9 * target + i));
    await view.animator.flush();
    do {
      view.cube.setFacelets(this.scanState(), (ch) => (ch === "?" ? UNKNOWN_HEX : colorLetterColor(ch)));
      await view.animator.jump(before);
      if (!rot) break;
      await sleep(700);
      for (const m of parseAlg(rot)) {
        if (id !== this.loopId) return;
        view.arrow.show(m);
        await sleep(500);
        await view.animator.play(m, 650);
      }
      view.arrow.hide();
      await sleep(1600);
    } while (id === this.loopId);
  }

  private renderSteps(): void {
    this.steps.replaceChildren(
      ...STEP_FACES.map((f, i) => {
        const col = SCHEME[f];
        const done = this.captured.has(f);
        return h("li", { class: `${done ? "done" : ""}${i === this.step ? " current" : ""}`, title: `${COLOR_NAMES[col]} face` },
          h("span", { class: "swatch", style: `background:${COLOR_HEX[col]}` }, done ? "✓" : String(i + 1)));
      }),
    );
  }
}
