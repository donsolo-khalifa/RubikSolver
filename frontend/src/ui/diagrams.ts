// SVG pictures of a cube state: an isometric view (U, F, R) and a clickable 2D net.
import { COLOR_HEX, SCHEME, UNKNOWN_HEX, type Color, type Face } from "../net/protocol";

export type ColorOf = (ch: string) => string;

/** Facelet strings in face letters (URFDLB), as the solver uses. */
export const faceLetterColor: ColorOf = (ch) => COLOR_HEX[SCHEME[ch as Face]] ?? UNKNOWN_HEX;
/** Strings in colour letters (WYROGB, '?' for unknown), as the scanner produces. */
export const colorLetterColor: ColorOf = (ch) => COLOR_HEX[ch as Color] ?? UNKNOWN_HEX;

type V3 = [number, number, number];
const ISO_FACES: { face: number; origin: V3; col: V3; row: V3 }[] = [
  { face: 0, origin: [-1.5, 1.5, -1.5], col: [1, 0, 0], row: [0, 0, 1] },  // U
  { face: 2, origin: [-1.5, 1.5, 1.5], col: [1, 0, 0], row: [0, -1, 0] },  // F
  { face: 1, origin: [1.5, 1.5, 1.5], col: [0, 0, -1], row: [0, -1, 0] },  // R
];
const COS30 = Math.cos(Math.PI / 6);

function project([x, y, z]: V3): [number, number] {
  return [(x - z) * COS30, (x + z) * 0.5 - y];
}

/** Isometric picture of the U, F and R faces. */
export function isoSvg(state: string, colorOf: ColorOf, size = 150): string {
  const m = 0.07; // gap between stickers
  const polys: string[] = [];
  for (const { face, origin, col, row } of ISO_FACES) {
    for (let i = 0; i < 9; i++) {
      const r = Math.floor(i / 3);
      const c = i % 3;
      const at = (dc: number, dr: number): string => {
        const p: V3 = [0, 1, 2].map((k) => origin[k] + col[k] * (c + dc) + row[k] * (r + dr)) as V3;
        const [sx, sy] = project(p);
        return `${sx.toFixed(3)},${sy.toFixed(3)}`;
      };
      const pts = [at(m, m), at(1 - m, m), at(1 - m, 1 - m), at(m, 1 - m)].join(" ");
      polys.push(`<polygon points="${pts}" fill="${colorOf(state[9 * face + i])}" stroke="#0b0c0f" stroke-width="0.05" stroke-linejoin="round"/>`);
    }
  }
  // Black body behind the stickers.
  const hull = [[-1.5, 1.5, -1.5], [1.5, 1.5, -1.5], [1.5, -1.5, -1.5], [1.5, -1.5, 1.5], [-1.5, -1.5, 1.5], [-1.5, 1.5, 1.5]]
    .map((p) => project(p as V3).map((n) => n.toFixed(3)).join(","))
    .join(" ");
  const w = 3 * COS30 * 2;
  return `<svg class="iso" viewBox="${-w / 2 - 0.2} -3.2 ${w + 0.4} 6.4" width="${size}" height="${size}" role="img" aria-label="Cube preview">
    <polygon points="${hull}" fill="#0b0c0f" stroke="#0b0c0f" stroke-width="0.15" stroke-linejoin="round"/>${polys.join("")}</svg>`;
}

// Net layout in sticker units: U above F; L F R B across; D below F.
const NET_POS: Record<Face, [number, number]> = { U: [3, 0], L: [0, 3], F: [3, 3], R: [6, 3], B: [9, 3], D: [3, 6] };
const ORDER: Face[] = ["U", "R", "F", "D", "L", "B"];

/** 2D net as an SVG element; ``onClick`` makes stickers clickable (centres excluded). */
export function netSvg(
  state: string,
  colorOf: ColorOf,
  onClick?: (face: Face, index: number, target: SVGRectElement) => void,
  highlight?: Face,
): SVGSVGElement {
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("viewBox", "-0.1 -0.1 12.2 9.2");
  svg.setAttribute("class", "net");
  ORDER.forEach((face, fi) => {
    const [ox, oy] = NET_POS[face];
    if (face === highlight) {
      const r = document.createElementNS(NS, "rect");
      Object.entries({ x: ox - 0.06, y: oy - 0.06, width: 3.12, height: 3.12, rx: 0.2, class: "net-hl" })
        .forEach(([k, v]) => r.setAttribute(k, String(v)));
      svg.append(r);
    }
    for (let i = 0; i < 9; i++) {
      const rect = document.createElementNS(NS, "rect");
      const x = ox + (i % 3) + 0.05;
      const y = oy + Math.floor(i / 3) + 0.05;
      Object.entries({ x, y, width: 0.9, height: 0.9, rx: 0.12, fill: colorOf(state[9 * fi + i]) })
        .forEach(([k, v]) => rect.setAttribute(k, String(v)));
      rect.setAttribute("class", i === 4 ? "sticker centre" : "sticker");
      if (onClick && i !== 4) {
        rect.classList.add("clickable");
        rect.setAttribute("tabindex", "0");
        rect.setAttribute("aria-label", `${face} sticker ${i + 1}`);
        rect.addEventListener("click", () => onClick(face, i, rect));
        rect.addEventListener("keydown", (e) => {
          if ((e as KeyboardEvent).key === "Enter") onClick(face, i, rect);
        });
      }
      svg.append(rect);
    }
    const label = document.createElementNS(NS, "text");
    label.setAttribute("x", String(ox + 1.5));
    label.setAttribute("y", String(oy + 1.62));
    label.setAttribute("class", "net-label");
    label.textContent = face;
    svg.append(label);
  });
  return svg;
}
