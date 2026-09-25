import type { Method } from "../net/protocol";
import { h } from "./dom";

export const METHOD_INFO: Record<Method, { title: string; moves: string; blurb: string; badge?: string }> = {
  beginner: {
    title: "Beginner",
    moves: "about 130–190 moves",
    blurb: "Layer by layer, 8 stages and 5 short algorithms. Every step is explained.",
    badge: "Start here",
  },
  intermediate: {
    title: "Intermediate",
    moves: "about 110–150 moves",
    blurb: "Same first two layers, then 2-look OLL and PLL: 15 algorithms, the first step towards CFOP.",
  },
  advanced: {
    title: "Advanced",
    moves: "about 20 moves",
    blurb: "The computer's near-shortest solution. Nothing to learn: just follow each move.",
  },
};

export function methodPicker(selected: Method, onChange: (m: Method) => void): HTMLElement {
  const wrap = h("div", { class: "methods", role: "radiogroup", "aria-label": "Solving method" });
  const render = (sel: Method) => {
    wrap.replaceChildren(
      ...(Object.keys(METHOD_INFO) as Method[]).map((m) => {
        const info = METHOD_INFO[m];
        return h(
          "button",
          {
            class: `method${m === sel ? " selected" : ""}`,
            role: "radio",
            "aria-checked": String(m === sel),
            onclick: () => {
              render(m);
              onChange(m);
            },
          },
          h("span", { class: "method-title" }, info.title, info.badge ? h("span", { class: "badge" }, info.badge) : null),
          h("span", { class: "method-moves" }, info.moves),
          h("span", { class: "method-blurb" }, info.blurb),
        );
      }),
    );
  };
  render(selected);
  return wrap;
}
