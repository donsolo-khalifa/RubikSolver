import "./style.css";
import { CubeView } from "./cube/CubeView";
import { SOLVED } from "./cube/facelets";
import { speech } from "./guidance/speech";
import { SCHEME, type Face } from "./net/protocol";
import { Socket } from "./net/socket";
import type { App } from "./ui/app";
import { faceLetterColor } from "./ui/diagrams";
import { h, type Panel } from "./ui/dom";
import { introSeen, NotationIntro } from "./ui/NotationIntro";
import { PracticePanel } from "./ui/PracticePanel";
import { ReviewPanel } from "./ui/ReviewPanel";
import { ScanPanel } from "./ui/ScanPanel";
import { SolvePanel } from "./ui/SolvePanel";

const panelRoot = document.getElementById("panel")!;
const view = new CubeView(document.getElementById("cube")!);
const socket = new Socket();
const toastEl = document.getElementById("toast")!;

let current: Panel | null = null;
let mode: "home" | "scan" | "practice" | "solve" = "home";

const app: App = {
  view,
  socket,
  cameraOk: true,
  show(panel) {
    current?.unmount?.();
    current = panel;
    panelRoot.replaceChildren(panel.el);
    panelRoot.scrollTop = 0;
    panel.mount?.();
  },
  home() {
    mode = "home";
    app.show(homePanel());
  },
  startScan(rescanFace?: Face) {
    mode = "scan";
    speech.unlock();
    app.show(new ScanPanel(app, rescanFace));
  },
  startPractice() {
    mode = "practice";
    practice = new PracticePanel(app);
    app.show(practice);
  },
  toast(message, kind = "info") {
    toastEl.textContent = message;
    toastEl.className = `toast show ${kind}`;
    clearTimeout((toastEl as HTMLElement & { timer?: number }).timer);
    (toastEl as HTMLElement & { timer?: number }).timer = window.setTimeout(() => (toastEl.className = "toast"), 5000);
  },
};

let practice: PracticePanel | null = null;

function homePanel(): Panel {
  const el = h("div", { class: "panel home" },
    h("h2", {}, "Let's solve your cube"),
    h("p", {}, "Show each face of your cube to the camera, and the app will walk you through solving it, one move at a time."),
    h("div", { class: "choices" },
      h("button", { class: "choice", onclick: () => app.startScan() },
        h("span", { class: "choice-title" }, "Scan my cube"),
        h("span", { class: "muted" }, "Uses the camera (your phone through Iriun).")),
      h("button", { class: "choice", onclick: () => app.startPractice() },
        h("span", { class: "choice-title" }, "Practice"),
        h("span", { class: "muted" }, "No camera: scramble a virtual cube and learn to solve it.")),
    ),
    h("p", {}, h("button", { class: "link", onclick: () => openIntro() }, "New to cubing? Learn how to read moves first.")),
  );
  return {
    el,
    mount() {
      view.cube.highlight([]);
      view.arrow.hide();
      view.cube.setFacelets(SOLVED, faceLetterColor);
    },
  };
}

// --- routing on server messages ------------------------------------------------
socket.on("status", (m) => {
  app.cameraOk = m.camera;
  const changed = (Object.keys(m.scheme) as Face[]).some((f) => SCHEME[f] !== m.scheme[f]);
  Object.assign(SCHEME, m.scheme);
  // Redraw with the cube's real colours if the first screen was drawn with the defaults.
  if (changed && (mode === "home" || mode === "practice")) mode === "home" ? app.home() : app.startPractice();
  document.body.classList.toggle("no-camera", !m.camera);
});
socket.on("cube_state", (m) => {
  if (mode === "scan") {
    mode = "solve";
    app.show(new ReviewPanel(app, m));
  }
});
socket.on("solution", async (m) => {
  if (mode === "practice" && practice) {
    await practice.scrambled;
    mode = "solve";
    app.show(new SolvePanel(app, m, "practice"));
  } else if (mode === "solve" || mode === "scan") {
    mode = "solve";
    app.show(new SolvePanel(app, m, "scan"));
  }
});
socket.on("error", (m) => app.toast(m.message, "error"));

const dot = document.getElementById("conn")!;
socket.onConnectionChange = (ok) => {
  dot.className = `conn ${ok ? "ok" : "bad"}`;
  dot.title = ok ? "Connected to the backend" : "Backend not reachable: start it with uvicorn app.main:app";
};

// --- header -----------------------------------------------------------------------
function openIntro(): void {
  new NotationIntro(() => undefined);
}

const speakerBtn = document.getElementById("speaker") as HTMLButtonElement;
const renderSpeaker = (on: boolean) => {
  speakerBtn.textContent = on ? "🔊" : "🔇";
  speakerBtn.setAttribute("aria-pressed", String(on));
  speakerBtn.title = on ? "Speech on (click to mute)" : "Speech off (click to turn on)";
};
renderSpeaker(speech.enabled);
speech.onChange(renderSpeaker);
speakerBtn.addEventListener("click", () => speech.set(!speech.enabled));
if (!speech.supported) speakerBtn.hidden = true;

document.getElementById("help")!.addEventListener("click", openIntro);
document.getElementById("home")!.addEventListener("click", () => app.home());
document.getElementById("reset-view")!.addEventListener("click", () => view.resetView());

app.home();
if (!introSeen()) openIntro();
