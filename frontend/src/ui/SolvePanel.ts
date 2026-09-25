// The solve player: stage cards, one move at a time, speech, grouped move list (PLAN.md 10).
import { applyMoves } from "../cube/facelets";
import { invertMove, isRotation } from "../cube/notation";
import { describe, progressLabel } from "../guidance/describe";
import { speech } from "../guidance/speech";
import type { Move, SolutionMsg } from "../net/protocol";
import type { App } from "./app";
import { faceLetterColor, isoSvg } from "./diagrams";
import { h, richText, type Panel } from "./dom";
import { METHOD_INFO } from "./MethodPicker";

interface Step {
  move: Move;
  stage: number;
}

function loadDelay(): number {
  try {
    return Number(localStorage.getItem("rubik.delay") ?? 1600) || 1600;
  } catch {
    return 1600;
  }
}

const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export class SolvePanel implements Panel {
  el = h("div", { class: "panel solve" });
  private steps: Step[] = [];
  private stageStart: number[] = [];
  private done = 0;
  private started = false;
  private ackStage = -1;
  private busy = false;
  private playing = false;
  private delay = loadDelay();
  private card = h("div", { class: "card-area" });
  private list = h("div", { class: "move-list" });
  private bar = h("div", { class: "progress" });
  private chips: HTMLElement[] = [];
  private onKey = (e: KeyboardEvent) => this.key(e);

  constructor(private app: App, private sol: SolutionMsg, private origin: "scan" | "practice") {
    sol.stages.forEach((st, si) => {
      this.stageStart.push(this.steps.length);
      st.moves.forEach((move) => this.steps.push({ move, stage: si }));
    });
    const info = METHOD_INFO[sol.method];
    this.el.append(
      h("div", { class: "solve-head" },
        h("div", {}, h("h2", {}, `${info.title} solution`),
          h("p", { class: "muted" }, `${sol.totalMoves} moves in ${sol.stages.length} stage${sol.stages.length > 1 ? "s" : ""}`)),
      ),
      this.bar,
      this.card,
      h("details", { class: "list-wrap" }, h("summary", {}, "All moves, by stage"), this.list),
    );
    this.buildList();
    this.buildBar();
  }

  mount(): void {
    this.app.view.cube.highlight([]);
    this.app.view.cube.setFacelets(this.sol.facelets, faceLetterColor);
    this.app.view.arrow.hide();
    document.addEventListener("keydown", this.onKey);
    this.render();
  }

  unmount(): void {
    this.playing = false;
    speech.stop();
    this.app.view.arrow.hide();
    document.removeEventListener("keydown", this.onKey);
  }

  // --- state helpers ----------------------------------------------------------
  private get total(): number {
    return this.steps.length;
  }

  private stageOf(i: number): number {
    return i < this.total ? this.steps[i].stage : this.sol.stages.length - 1;
  }

  private needsCard(): boolean {
    return this.started && this.done < this.total && this.stageOf(this.done) > this.ackStage;
  }

  private stateAt(i: number): string {
    return applyMoves(this.sol.facelets, this.steps.slice(0, i).map((s) => s.move.notation));
  }

  // --- actions ----------------------------------------------------------------
  private start(): void {
    speech.unlock();
    this.started = true;
    this.render();
    this.speakCurrent();
  }

  private ackCard(): void {
    this.ackStage = this.stageOf(this.done);
    this.render();
    this.speakCurrent();
  }

  async next(): Promise<void> {
    if (!this.started) return this.start();
    if (this.needsCard()) return this.ackCard();
    if (this.busy || this.done >= this.total) return;
    this.busy = true;
    this.app.view.arrow.hide();
    await this.app.view.animator.play(this.steps[this.done].move.notation);
    this.done++;
    this.busy = false;
    this.render();
    this.speakCurrent();
  }

  async back(): Promise<void> {
    if (this.busy || this.done === 0 || !this.started) return;
    this.busy = true;
    this.playing = false;
    this.app.view.arrow.hide();
    await this.app.view.animator.play(invertMove(this.steps[this.done - 1].move.notation));
    this.done--;
    this.ackStage = Math.max(this.ackStage, this.stageOf(this.done));
    this.busy = false;
    this.render();
    this.speakCurrent();
  }

  /** Demonstrate the upcoming move, then put the cube back. */
  async showMe(): Promise<void> {
    if (this.busy || this.done >= this.total || this.needsCard() || !this.started) return;
    this.busy = true;
    const m = this.steps[this.done].move.notation;
    this.app.view.arrow.hide();
    await this.app.view.animator.play(m);
    await sleep(350);
    await this.app.view.animator.play(invertMove(m), 250);
    this.busy = false;
    this.render();
  }

  private async jumpTo(i: number): Promise<void> {
    this.playing = false;
    await this.app.view.animator.flush();
    this.app.view.cube.setFacelets(this.sol.facelets, faceLetterColor);
    await this.app.view.animator.jump(this.steps.slice(0, i).map((s) => s.move.notation));
    this.done = i;
    this.started = true;
    this.ackStage = this.stageOf(i);
    this.render();
    this.speakCurrent();
  }

  private async togglePlay(): Promise<void> {
    if (!this.started) this.start();
    this.playing = !this.playing;
    this.render();
    while (this.playing && this.done < this.total) {
      if (this.needsCard()) {
        this.playing = false; // pause at each stage card so it can be read
        break;
      }
      await this.next();
      await sleep(this.delay);
    }
    this.playing = false;
    this.render();
  }

  private key(e: KeyboardEvent): void {
    if ((e.target as HTMLElement)?.closest("input, textarea, select")) return;
    if (document.querySelector(".modal")) return;
    if (e.key === " " || e.key === "ArrowRight") {
      e.preventDefault();
      void this.next();
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      void this.back();
    } else if (e.key === "r") void this.showMe();
    else if (e.key === "p") void this.togglePlay();
  }

  private speakCurrent(): void {
    if (!this.started) return;
    if (this.done >= this.total) return speech.say("Solved! Well done.");
    if (this.needsCard()) {
      const si = this.stageOf(this.done);
      const st = this.sol.stages[si];
      const n = this.sol.stages.length;
      const pre = n > 1 ? `Stage ${si + 1} of ${n}: ${st.name}. ` : "";
      return speech.say(`${pre}${st.goal}. ${st.explanation} ${st.tips.join(" ")}`);
    }
    speech.say(describe(this.steps[this.done].move.notation).text);
  }

  // --- rendering --------------------------------------------------------------
  private render(): void {
    const view = this.app.view;
    if (!this.started) this.card.replaceChildren(this.readyCard());
    else if (this.done >= this.total) this.card.replaceChildren(this.solvedCard());
    else if (this.needsCard()) this.card.replaceChildren(this.stageCard(this.stageOf(this.done)));
    else this.card.replaceChildren(this.moveCard());

    if (this.started && !this.needsCard() && this.done < this.total && !this.busy) {
      view.arrow.show(this.steps[this.done].move.notation);
    } else if (!this.busy) view.arrow.hide();

    this.chips.forEach((c, i) => {
      c.classList.toggle("done", i < this.done);
      c.classList.toggle("current", i === this.done && this.started);
    });
    this.chips[this.done]?.scrollIntoView({ block: "nearest" });
    (this.bar.querySelector(".progress-fill") as HTMLElement).style.width = `${(100 * this.done) / Math.max(1, this.total)}%`;
  }

  private readyCard(): HTMLElement {
    const flips = this.sol.method !== "advanced";
    return h("div", { class: "card" },
      h("h3", {}, "Get ready"),
      h("p", { html: "Hold your cube with <strong>white on top</strong> and <strong>green facing you</strong>, just like the cube on screen." }),
      flips ? h("p", { html: "The very first move turns the whole cube upside down (<code>z2</code>), so yellow ends up on top. Beginner guides are written that way." }) : null,
      h("p", { class: "muted" }, "Each move shows as a yellow arrow on the 3D cube. Do it on your real cube, then press Next (or Space). ← goes back, R shows the move again."),
      h("div", { class: "row" }, h("button", { class: "primary big", onclick: () => this.start() }, "Start")),
    );
  }

  private stageCard(si: number): HTMLElement {
    const st = this.sol.stages[si];
    const n = this.sol.stages.length;
    const from = this.stageStart[si];
    const to = from + st.moves.length;
    const after = this.stateAt(to);
    const count = st.moves.filter((m) => !isRotation(m.notation)).length;

    // One algorithm card per named algorithm, showing the case as it appears in this solve.
    const algs = new Map<string, { moves: string[]; before: string }>();
    for (let i = from; i < to; i++) {
      const m = this.steps[i].move;
      if (!m.algorithm || algs.has(m.algorithm) || m.step !== 1) continue;
      const moves = this.steps.slice(i, i + (m.steps ?? 1)).map((s) => s.move.notation);
      algs.set(m.algorithm, { moves, before: this.stateAt(i) });
    }

    return h("div", { class: "card stage-card" },
      n > 1 ? h("div", { class: "eyebrow" }, `Stage ${si + 1} of ${n}`) : null,
      h("h3", {}, st.name),
      h("p", { class: "goal" }, st.goal),
      h("p", {}, st.explanation),
      algs.size
        ? h("div", { class: "algs" },
            ...[...algs].map(([name, a]) =>
              h("div", { class: "alg-card" },
                h("div", { class: "alg-pic", html: isoSvg(a.before, faceLetterColor, 84) }),
                h("div", {}, h("div", { class: "alg-name" }, name), h("code", { class: "alg-moves" }, a.moves.join(" "))),
              ),
            ))
        : null,
      ...st.tips.map((t) => h("p", { class: "tip", html: richText(t) })),
      h("div", { class: "preview" },
        h("div", { html: isoSvg(after, faceLetterColor, 110) }),
        h("p", { class: "muted" }, `When this stage is done (${count} move${count === 1 ? "" : "s"}).`),
      ),
      h("div", { class: "row" },
        si > 0 ? h("button", { onclick: () => void this.back() }, "◀ Back") : null,
        h("button", { class: "primary big", onclick: () => this.ackCard() }, "Start stage"),
      ),
    );
  }

  private moveCard(): HTMLElement {
    const step = this.steps[this.done];
    const d = describe(step.move.notation);
    const label = progressLabel(step.move);
    const si = step.stage;
    const n = this.sol.stages.length;
    const speed = h("input", { type: "range", min: "500", max: "4000", step: "100", value: String(this.delay), "aria-label": "Auto-play delay" }) as HTMLInputElement;
    speed.addEventListener("input", () => {
      this.delay = Number(speed.value);
      try {
        localStorage.setItem("rubik.delay", speed.value);
      } catch {
        /* not persisted in private mode */
      }
    });
    // Count turns only, to match the total; whole-cube rotations are labelled separately.
    const turn = this.steps.slice(0, this.done + 1).filter((s) => !isRotation(s.move.notation)).length;
    const where = isRotation(step.move.notation) ? "rotate the cube" : `move ${turn} of ${this.sol.totalMoves}`;
    return h("div", { class: "card move-card" },
      h("div", { class: "eyebrow" }, `${n > 1 ? `${this.sol.stages[si].name} · ` : ""}${where}`),
      h("div", { class: `notation${isRotation(step.move.notation) ? " rotation" : ""}` }, step.move.notation),
      h("p", { class: "describe", html: d.html }),
      label ? h("p", { class: "alg-progress" }, label) : null,
      h("div", { class: "row controls" },
        h("button", { onclick: () => void this.back(), disabled: this.done === 0, title: "Back (←)" }, "◀ Back"),
        h("button", { onclick: () => void this.showMe(), title: "Show me again (R)" }, "⟲ Show me"),
        h("button", { class: "primary big", onclick: () => void this.next(), title: "Next (Space or →)" }, "Next ▶"),
      ),
      h("div", { class: "row autoplay" },
        h("button", { onclick: () => void this.togglePlay(), title: "Play / pause (P)" }, this.playing ? "⏸ Pause" : "▶ Auto-play"),
        h("label", { class: "muted" }, "Speed ", speed),
      ),
    );
  }

  private solvedCard(): HTMLElement {
    return h("div", { class: "card solved" },
      h("h3", {}, "Solved!"),
      h("p", {}, `That took ${this.sol.totalMoves} moves. Well done.`),
      h("div", { class: "row" },
        h("button", { onclick: () => void this.jumpTo(0) }, "Replay from start"),
        this.origin === "practice"
          ? h("button", { class: "primary", onclick: () => this.app.startPractice() }, "Practise another")
          : h("button", { class: "primary", onclick: () => this.app.startScan() }, "Scan another cube"),
      ),
    );
  }

  private buildBar(): void {
    const segs = this.sol.stages.map((st) =>
      h("div", { class: "seg", style: `flex: ${Math.max(1, st.moves.length)}`, title: st.name }),
    );
    this.bar.replaceChildren(h("div", { class: "segs" }, ...segs), h("div", { class: "progress-fill" }));
  }

  private buildList(): void {
    this.chips = [];
    const sections = this.sol.stages.map((st, si) => {
      const chips = st.moves.map((m, k) => {
        const i = this.stageStart[si] + k;
        const chip = h("button", {
          class: `chip${isRotation(m.notation) ? " rot" : ""}${m.algorithm ? " alg" : ""}`,
          title: m.description,
          onclick: () => void this.jumpTo(i),
        }, m.notation);
        this.chips[i] = chip;
        return chip;
      });
      return h("section", {},
        h("h4", {}, `${si + 1}. ${st.name} `, h("span", { class: "muted" }, `(${st.moves.length})`)),
        h("div", { class: "chips" }, ...(chips.length ? chips : [h("span", { class: "muted" }, "Nothing to do: already done")])),
      );
    });
    this.list.replaceChildren(...sections);
  }
}
