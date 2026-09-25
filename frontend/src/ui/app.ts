import type { CubeView } from "../cube/CubeView";
import type { Face } from "../net/protocol";
import type { Socket } from "../net/socket";
import type { Panel } from "./dom";

/** What panels can reach: the shared 3D view, the socket and navigation. */
export interface App {
  view: CubeView;
  socket: Socket;
  cameraOk: boolean;
  show(panel: Panel): void;
  home(): void;
  startScan(rescanFace?: Face): void;
  startPractice(): void;
  toast(message: string, kind?: "info" | "error"): void;
}
