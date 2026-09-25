// Practice mode (no camera): the server scrambles a virtual cube and solves it.
import { SOLVED } from "../cube/facelets";
import type { Method } from "../net/protocol";
import type { App } from "./app";
import { faceLetterColor } from "./diagrams";
import { h, type Panel } from "./dom";
import { methodPicker } from "./MethodPicker";

export class PracticePanel implements Panel {
  el = h("div", { class: "panel practice" });
  private method: Method = "beginner";
  private offs: (() => void)[] = [];
  private scrambleText = h("p", { class: "scramble" });
  private button: HTMLButtonElement;
  /** Resolves when the scramble animation has finished; the solution waits for it. */
  scrambled: Promise<void> = Promise.resolve();

  constructor(private app: App) {
    this.button = h("button", { class: "primary big", onclick: () => this.scramble() }, "Scramble") as HTMLButtonElement;
    this.el.append(
      h("h2", {}, "Practice"),
      h("p", {}, "The app scrambles the cube on screen, then walks you through solving it. " +
        "To practise on your real cube too, start from a solved cube (white on top, green in front) and do the scramble shown below."),
      h("h3", {}, "Choose a method"),
      methodPicker(this.method, (m) => (this.method = m)),
      h("div", { class: "row" }, this.button),
      this.scrambleText,
    );
  }

  mount(): void {
    this.app.view.cube.highlight([]);
    this.app.view.arrow.hide();
    this.app.view.cube.setFacelets(SOLVED, faceLetterColor);
    this.offs.push(
      this.app.socket.on("practice", (m) => {
        this.scrambleText.replaceChildren(h("span", { class: "muted" }, "Scramble: "), h("code", {}, m.scramble.join(" ")));
        const view = this.app.view;
        this.scrambled = (async () => {
          await view.animator.flush();
          view.cube.setFacelets(SOLVED, faceLetterColor);
          await view.animator.playAll(m.scramble, 110);
        })();
      }),
      this.app.socket.on("error", () => {
        this.button.disabled = false;
      }),
    );
  }

  unmount(): void {
    this.offs.forEach((o) => o());
  }

  private scramble(): void {
    this.button.disabled = true;
    this.app.socket.send({ type: "practice_scramble", method: this.method });
  }
}
