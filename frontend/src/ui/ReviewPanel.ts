// Review the scanned cube: 2D net with click-to-fix, validation errors, rescan buttons.
import { COLOR_HEX, COLOR_NAMES, FACES, SCHEME, type Color, type Face, type Method, type ServerMsg } from "../net/protocol";
import type { App } from "./app";
import { faceLetterColor, netSvg } from "./diagrams";
import { h, type Panel } from "./dom";
import { methodPicker } from "./MethodPicker";

type CubeState = Extract<ServerMsg, { type: "cube_state" }>;

export class ReviewPanel implements Panel {
  el = h("div", { class: "panel review" });
  private method: Method = "beginner";
  private offs: (() => void)[] = [];
  private popover: HTMLElement | null = null;

  constructor(private app: App, private state: CubeState) {}

  mount(): void {
    this.offs.push(this.app.socket.on("cube_state", (m) => this.update(m)));
    this.update(this.state);
  }

  unmount(): void {
    this.offs.forEach((o) => o());
    this.popover?.remove();
  }

  private update(state: CubeState): void {
    this.state = state;
    this.app.view.cube.highlight([]);
    this.app.view.cube.setFacelets(state.facelets, faceLetterColor);
    this.render();
  }

  private render(): void {
    const s = this.state;
    const net = netSvg(s.facelets, faceLetterColor, (face, index, rect) => this.pick(face, index, rect));
    this.el.replaceChildren(
      h("h2", {}, "Check your scan"),
      h("p", { class: "muted" }, "Compare each face with your cube. Click a sticker to change its colour."),
      h("div", { class: "net-wrap" }, net),
      s.note ? h("p", { class: "note" }, s.note) : "",
      s.valid
        ? h("p", { class: "ok-line" }, "✓ This is a valid cube.")
        : h("div", { class: "errors", role: "alert" },
            h("strong", {}, "This scan isn't a valid cube yet:"),
            h("ul", {}, ...s.errors.map((e) => h("li", {}, e)))),
      h("div", { class: "rescan" },
        h("span", { class: "muted" }, "Rescan a face: "),
        ...FACES.map((f) =>
          h("button", { class: "face-btn", title: `Rescan the ${COLOR_NAMES[SCHEME[f]]} face`, onclick: () => this.rescan(f) },
            h("span", { class: "swatch", style: `background:${COLOR_HEX[SCHEME[f]]}` }), f)),
      ),
      h("h3", {}, "Choose a method"),
      methodPicker(this.method, (m) => (this.method = m)),
      h("div", { class: "row" },
        h("button", {
          class: "primary big",
          disabled: !s.valid,
          onclick: () => this.app.socket.send({ type: "solve", method: this.method }),
        }, "Solve it"),
      ),
    );
  }

  private rescan(face: Face): void {
    this.app.startScan(face);
  }

  private pick(face: Face, index: number, rect: SVGRectElement): void {
    this.popover?.remove();
    const box = rect.getBoundingClientRect();
    const pop = h("div", { class: "palette", role: "dialog", "aria-label": "Pick a colour" },
      ...(Object.keys(COLOR_HEX) as Color[]).map((c) =>
        h("button", {
          class: "swatch big",
          style: `background:${COLOR_HEX[c]}`,
          title: COLOR_NAMES[c],
          "aria-label": COLOR_NAMES[c],
          onclick: () => {
            this.app.socket.send({ type: "set_sticker", face, index, color: c });
            pop.remove();
          },
        })),
    );
    pop.style.left = `${Math.min(innerWidth - 220, box.left + scrollX)}px`;
    pop.style.top = `${box.bottom + scrollY + 6}px`;
    document.body.append(pop);
    this.popover = pop;
    (pop.firstElementChild as HTMLElement)?.focus();
    const close = (e: MouseEvent) => {
      if (!pop.contains(e.target as Node)) {
        pop.remove();
        document.removeEventListener("mousedown", close);
      }
    };
    setTimeout(() => document.addEventListener("mousedown", close));
  }
}
