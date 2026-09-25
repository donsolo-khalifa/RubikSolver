// Layer and whole-cube rotations, one at a time from a queue (PLAN.md 9.2).
import * as THREE from "three";
import type { CubeModel } from "./CubeModel";
import { parseMove } from "./notation";

const ease = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

export class MoveAnimator {
  duration = 400; // ms per quarter turn
  private pivot = new THREE.Object3D();
  private queue: Promise<void> = Promise.resolve();
  private pending = 0;
  private hurry = false;

  constructor(private cube: CubeModel) {
    cube.group.add(this.pivot);
  }

  get busy(): boolean {
    return this.pending > 0;
  }

  /** Animate a move; resolves when it has finished. Moves play strictly in order. */
  play(move: string, duration = this.duration): Promise<void> {
    this.pending++;
    this.queue = this.queue.then(async () => {
      try {
        await this.turn(move, this.hurry ? 0 : duration);
      } finally {
        this.pending--;
        if (this.pending === 0) this.hurry = false;
      }
    });
    return this.queue;
  }

  async playAll(moves: string[], duration = this.duration): Promise<void> {
    for (const m of moves) await this.play(m, duration);
  }

  /** Apply moves instantly (still in queue order). */
  jump(moves: string[]): Promise<void> {
    let p = Promise.resolve();
    for (const m of moves) p = this.play(m, 0);
    return p;
  }

  /** Finish everything queued as fast as possible. */
  flush(): Promise<void> {
    if (this.pending) this.hurry = true;
    return this.queue;
  }

  private turn(move: string, duration: number): Promise<void> {
    const spec = parseMove(move);
    const cubies = this.cube.cubiesInLayers(spec.axis, spec.layers);
    this.pivot.rotation.set(0, 0, 0);
    this.pivot.updateMatrixWorld();
    for (const c of cubies) this.pivot.attach(c);
    // Half turns take a little longer than quarter turns.
    const ms = duration * (Math.abs(spec.quarters) === 2 ? 1.5 : 1);

    return new Promise((resolve) => {
      const finish = () => {
        this.pivot.rotation[spec.axis] = spec.angle;
        this.pivot.updateMatrixWorld();
        for (const c of cubies) {
          this.cube.group.attach(c);
          snap(c);
        }
        this.pivot.rotation.set(0, 0, 0);
        resolve();
      };
      if (ms <= 0) return finish();
      const start = performance.now();
      const step = (now: number) => {
        const t = Math.min(1, (now - start) / (this.hurry ? 1 : ms));
        this.pivot.rotation[spec.axis] = spec.angle * ease(t);
        if (t < 1) requestAnimationFrame(step);
        else finish();
      };
      requestAnimationFrame(step);
    });
  }
}

const m4 = new THREE.Matrix4();

/** Round position to integers and rotation to multiples of 90 degrees so error can't build up. */
function snap(o: THREE.Object3D): void {
  o.position.set(Math.round(o.position.x), Math.round(o.position.y), Math.round(o.position.z));
  m4.makeRotationFromQuaternion(o.quaternion);
  const e = m4.elements;
  for (let i = 0; i < 16; i++) e[i] = Math.round(e[i]);
  o.quaternion.setFromRotationMatrix(m4);
}
