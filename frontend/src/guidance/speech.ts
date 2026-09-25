// Web Speech API wrapper. On by default; the toggle is remembered in localStorage.
const KEY = "rubik.speech";

function load(): boolean {
  try {
    return localStorage.getItem(KEY) !== "off";
  } catch {
    return true;
  }
}

class Speech {
  enabled = load();
  private voice: SpeechSynthesisVoice | null = null;
  private listeners = new Set<(on: boolean) => void>();

  constructor() {
    if (!("speechSynthesis" in globalThis)) {
      this.enabled = false;
      return;
    }
    const pick = () => {
      const voices = speechSynthesis.getVoices();
      this.voice =
        voices.find((v) => v.lang === "en-GB") ?? voices.find((v) => v.lang.startsWith("en")) ?? null;
    };
    pick();
    speechSynthesis.addEventListener("voiceschanged", pick);
  }

  get supported(): boolean {
    return "speechSynthesis" in globalThis;
  }

  /** Browsers only allow speech after a user gesture: call this from the first click. */
  unlock(): void {
    if (!this.supported) return;
    const u = new SpeechSynthesisUtterance("");
    u.volume = 0;
    speechSynthesis.speak(u);
  }

  say(text: string): void {
    if (!this.enabled || !this.supported) return;
    speechSynthesis.cancel(); // fast clicking must not pile up a queue
    const u = new SpeechSynthesisUtterance(text.replace(/\*\*/g, ""));
    if (this.voice) u.voice = this.voice;
    u.lang = this.voice?.lang ?? "en-GB";
    u.rate = 0.95;
    speechSynthesis.speak(u);
  }

  stop(): void {
    if (this.supported) speechSynthesis.cancel();
  }

  set(on: boolean): void {
    this.enabled = on && this.supported;
    try {
      localStorage.setItem(KEY, on ? "on" : "off");
    } catch {
      /* private mode: keep the in-memory setting */
    }
    if (!on) this.stop();
    this.listeners.forEach((l) => l(this.enabled));
  }

  onChange(l: (on: boolean) => void): void {
    this.listeners.add(l);
  }
}

export const speech = new Speech();
