// Typed WebSocket client with automatic reconnect.
import type { ClientMsg, ServerMsg } from "./protocol";

type Handler<T extends ServerMsg["type"]> = (msg: Extract<ServerMsg, { type: T }>) => void;

export class Socket {
  private ws: WebSocket | null = null;
  private handlers = new Map<string, Set<(m: ServerMsg) => void>>();
  private pending: ClientMsg[] = [];
  onConnectionChange: (connected: boolean) => void = () => {};

  constructor(private url = `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`) {
    this.connect();
  }

  get connected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  private connect(): void {
    const ws = new WebSocket(this.url);
    this.ws = ws;
    ws.onopen = () => {
      this.onConnectionChange(true);
      for (const m of this.pending.splice(0)) ws.send(JSON.stringify(m));
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data as string) as ServerMsg;
      if (msg.type !== "detection") console.debug("ws <-", msg);
      this.handlers.get(msg.type)?.forEach((h) => h(msg));
      this.handlers.get("*")?.forEach((h) => h(msg));
    };
    ws.onclose = () => {
      this.onConnectionChange(false);
      setTimeout(() => this.connect(), 1500);
    };
  }

  send(msg: ClientMsg): void {
    if (this.connected) this.ws!.send(JSON.stringify(msg));
    else this.pending.push(msg);
  }

  on<T extends ServerMsg["type"]>(type: T, handler: Handler<T>): () => void {
    const set = this.handlers.get(type) ?? new Set();
    set.add(handler as (m: ServerMsg) => void);
    this.handlers.set(type, set);
    return () => set.delete(handler as (m: ServerMsg) => void);
  }
}
