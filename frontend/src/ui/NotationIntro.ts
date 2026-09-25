// "How to read moves": a short interactive introduction on its own 3D cube (PLAN.md 10).
import { CubeView } from "../cube/CubeView";
import { SOLVED } from "../cube/facelets";
import { invertMove } from "../cube/notation";
import { describe } from "../guidance/describe";
import { speech } from "../guidance/speech";
import { faceLetterColor } from "./diagrams";
import { h } from "./dom";

const SEEN_KEY = "rubik.introSeen";
const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function introSeen(): boolean {
  try {
    return localStorage.getItem(SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

function markSeen(): void {
  try {
    localStorage.setItem(SEEN_KEY, "1");
  } catch {
    /* ignore */
  }
}

class Cancelled extends Error {}

/** Every await in a slide goes through this, so a slide's loop stops the moment you leave it. */
interface Guard {
  alive: () => boolean;
  wait: (ms: number) => Promise<void>;
  step: <T>(p: Promise<T>) => Promise<T>;
}

interface Slide {
  title: string;
  html: string;
  run?: (view: CubeView, g: Guard, extra: HTMLElement) => Promise<void>;
}

const FACE_INFO: [string, string][] = [
  ["F", "Front: the face pointing at you"],
  ["R", "Right"],
  ["U", "Up: the top face"],
  ["B", "Back: the face pointing away from you"],
  ["L", "Left"],
  ["D", "Down: the bottom face"],
];
const FACE_INDEX: Record<string, number> = { U: 0, R: 1, F: 2, D: 3, L: 4, B: 5 };
const faceStickers = (f: string) => Array.from({ length: 9 }, (_, i) => 9 * FACE_INDEX[f] + i);

const TRY_TARGET = 5;

export class NotationIntro {
  private el: HTMLElement;
  private view: CubeView;
  private slide = 0;
  private runId = 0;
  private body = h("div", { class: "intro-body" });
  private extra = h("div", { class: "intro-extra" });
  private dots = h("div", { class: "dots" });
  private nextBtn = h("button", { class: "primary" }, "Next") as HTMLButtonElement;
  private backBtn = h("button", {}, "Back") as HTMLButtonElement;
  private slides: Slide[];

  constructor(private onClose: () => void) {
    const stage = h("div", { class: "intro-cube" });
    this.el = h("div", { class: "modal", role: "dialog", "aria-modal": "true", "aria-label": "How to read moves" },
      h("div", { class: "modal-card intro" },
        h("div", { class: "intro-top" },
          h("h2", {}, "How to read moves"),
          h("button", { class: "ghost", onclick: () => this.close() }, "Skip")),
        h("div", { class: "intro-main" }, stage, h("div", { class: "intro-text" }, this.body, this.extra)),
        h("div", { class: "intro-nav" }, this.backBtn, this.dots, this.nextBtn),
      ),
    );
    document.body.append(this.el);
    this.view = new CubeView(stage);
    this.view.cube.setFacelets(SOLVED, faceLetterColor);
    this.nextBtn.onclick = () => this.go(this.slide + 1);
    this.backBtn.onclick = () => this.go(this.slide - 1);
    this.el.addEventListener("keydown", (e) => {
      if (e.key === "Escape") this.close();
    });
    this.slides = this.buildSlides();
    speech.unlock();
    this.go(0);
    this.nextBtn.focus();
  }

  private close(): void {
    markSeen();
    speech.stop();
    this.runId++;
    this.view.renderer.setAnimationLoop(null);
    this.view.renderer.dispose();
    this.el.remove();
    this.onClose();
  }

  private go(i: number): void {
    if (i >= this.slides.length) return this.close();
    if (i < 0) return;
    this.slide = i;
    const s = this.slides[i];
    this.body.innerHTML = `<h3>${s.title}</h3>${s.html}`;
    this.extra.replaceChildren();
    this.backBtn.disabled = i === 0;
    this.nextBtn.textContent = i === this.slides.length - 1 ? "Done" : "Next";
    this.dots.replaceChildren(...this.slides.map((_, k) => h("span", { class: k === i ? "on" : "" })));
    speech.say(this.body.textContent ?? "");
    const id = ++this.runId;
    const alive = () => id === this.runId;
    const step = async <T>(p: Promise<T>): Promise<T> => {
      const r = await p;
      if (!alive()) throw new Cancelled();
      return r;
    };
    const g: Guard = { alive, step, wait: (ms) => step(sleep(ms)) };
    void (async () => {
      await this.view.animator.flush();
      if (!alive()) return;
      this.view.arrow.hide();
      this.view.cube.highlight([]);
      this.view.cube.setFacelets(SOLVED, faceLetterColor);
      try {
        await g.step(this.view.swingTo(CubeView.home, 400));
        await s.run?.(this.view, g, this.extra);
      } catch (e) {
        if (!(e instanceof Cancelled)) throw e;
      }
    })();
  }

  private buildSlides(): Slide[] {
    return [
      {
        title: "1. Six faces, six letters",
        html: "<p>Every move names a face by its position, not its colour: <strong>F</strong>ront, <strong>R</strong>ight, <strong>U</strong>p, <strong>B</strong>ack, <strong>L</strong>eft, <strong>D</strong>own.</p><p class='now'></p>",
        run: async (view, g) => {
          const now = this.body.querySelector(".now") as HTMLElement;
          for (;;) {
            for (const [f, label] of FACE_INFO) {
              now.innerHTML = `<span class="big-letter">${f}</span> ${label}`;
              view.cube.highlight(faceStickers(f));
              await g.step(view.swingTo("BLD".includes(f) ? CubeView.viewOf(f) : CubeView.home, 600));
              await g.wait(1300);
            }
          }
        },
      },
      {
        title: "2. Clockwise means as you look at that face",
        html: "<p><code>R</code> turns the right face clockwise <em>as if you were looking straight at the right face</em>.</p><p>This catches everyone out with <code>L</code>, <code>D</code> and <code>B</code>: seen from the front, they turn the “other way”. Watch the camera swing round to each face.</p>",
        run: async (view, g) => {
          for (;;) {
            for (const f of ["R", "L", "D", "B"]) {
              view.cube.highlight(faceStickers(f));
              await g.step(view.swingTo(CubeView.viewOf(f), 700));
              view.arrow.show(f);
              await g.wait(500);
              await g.step(view.animator.play(f, 700));
              await g.wait(500);
              view.arrow.hide();
              await g.step(view.swingTo(CubeView.home, 700));
              await g.step(view.animator.play(invertMove(f), 300));
              await g.wait(400);
            }
          }
        },
      },
      {
        title: "3. ' means anticlockwise, 2 means twice",
        html: "<p><code>R</code> is a clockwise quarter turn. <code>R'</code> (say “R prime”) turns it back the other way. <code>R2</code> is a half turn: twice in either direction.</p><p class='now'></p>",
        run: async (view, g) => {
          const now = this.body.querySelector(".now") as HTMLElement;
          for (;;) {
            for (const m of ["R", "R'", "R2", "U", "U'", "U2"]) {
              now.innerHTML = describe(m).html;
              view.arrow.show(m);
              await g.wait(600);
              await g.step(view.animator.play(m, 600));
              view.arrow.hide();
              await g.wait(700);
              await g.step(view.animator.play(invertMove(m), 250));
              await g.wait(300);
            }
          }
        },
      },
      {
        title: "4. Try it",
        html: `<p>Press the button for the move shown. Get ${TRY_TARGET} right to finish. (You can drag the cube to look around.)</p>`,
        run: async (view, g, extra) => this.tryIt(view, g.alive, extra),
      },
      {
        title: "5. Whole-cube rotations: x, y, z",
        html: "<p>Lower-case <code>x</code>, <code>y</code> and <code>z</code> mean <strong>turn the whole cube in your hands</strong>, not a layer. <code>y</code> turns it like <code>U</code>, <code>x</code> like <code>R</code>, <code>z</code> like <code>F</code>.</p><p class='now'></p>",
        run: async (view, g) => {
          const now = this.body.querySelector(".now") as HTMLElement;
          for (;;) {
            for (const m of ["y", "y'", "x", "x'", "z2"]) {
              now.innerHTML = describe(m).html;
              view.arrow.show(m);
              await g.wait(600);
              await g.step(view.animator.play(m, 800));
              view.arrow.hide();
              await g.wait(900);
              await g.step(view.animator.play(invertMove(m), 300));
              await g.wait(300);
            }
          }
        },
      },
    ];
  }

  private async tryIt(view: CubeView, alive: () => boolean, extra: HTMLElement): Promise<void> {
    let score = 0;
    const moves = ["U", "U'", "R", "R'", "F", "F'", "D", "D'", "L", "L'", "B", "B'"];
    let target = "";
    const prompt = h("p", { class: "try-prompt" });
    const feedback = h("p", { class: "try-feedback", role: "status" });
    const scoreEl = h("p", { class: "muted" });
    const pickTarget = () => {
      let t = target;
      while (t === target) t = moves[Math.floor(Math.random() * moves.length)];
      target = t;
      prompt.innerHTML = `Do: <span class="big-letter">${target}</span>`;
      scoreEl.textContent = `${score} of ${TRY_TARGET} right`;
      speech.say(describe(target).text);
    };
    const grid = h("div", { class: "move-buttons" },
      ...moves.map((m) =>
        h("button", {
          onclick: async () => {
            if (!alive() || view.animator.busy) return;
            await view.animator.play(m, 450);
            if (m === target) {
              score++;
              feedback.textContent = "Right!";
              feedback.className = "try-feedback ok";
              if (score >= TRY_TARGET) {
                prompt.textContent = "Nicely done. You can read moves now.";
                scoreEl.textContent = "";
                speech.say("Nicely done.");
                return;
              }
              pickTarget();
            } else {
              feedback.textContent = `Not quite: that was ${m}. Watch it undo, then try ${target}.`;
              feedback.className = "try-feedback bad";
              await sleep(400);
              await view.animator.play(invertMove(m), 300);
            }
          },
        }, m)),
    );
    extra.replaceChildren(prompt, grid, feedback, scoreEl);
    pickTarget();
  }
}
