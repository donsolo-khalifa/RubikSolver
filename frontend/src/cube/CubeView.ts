// A Three.js viewport holding one cube, its animator and its arrow.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Arrow } from "./Arrow";
import { CubeModel } from "./CubeModel";
import { MoveAnimator } from "./MoveAnimator";

// Default view shows U, F and R.
const HOME = new THREE.Vector3(5.6, 5.3, 8.6);

export class CubeView {
  readonly scene = new THREE.Scene();
  readonly camera = new THREE.PerspectiveCamera(35, 1, 0.1, 100);
  readonly renderer: THREE.WebGLRenderer;
  readonly controls: OrbitControls;
  readonly cube = new CubeModel();
  readonly animator: MoveAnimator;
  readonly arrow = new Arrow();
  private swing: { from: THREE.Vector3; to: THREE.Vector3; start: number; ms: number; done: () => void } | null = null;

  constructor(private container: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    container.appendChild(this.renderer.domElement);

    this.scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 1.4);
    key.position.set(5, 8, 6);
    this.scene.add(key);
    const fill = new THREE.DirectionalLight(0xffffff, 0.5);
    fill.position.set(-6, -3, -4);
    this.scene.add(fill);

    this.scene.add(this.cube.group, this.arrow.object);
    this.animator = new MoveAnimator(this.cube);

    this.camera.position.copy(HOME);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enablePan = false;
    this.controls.minDistance = 8;
    this.controls.maxDistance = 20;
    this.controls.enableDamping = true;

    new ResizeObserver(() => this.resize()).observe(container);
    this.resize();
    this.renderer.setAnimationLoop((t) => this.frame(t));
  }

  resetView(): void {
    this.swingTo(HOME, 500);
  }

  /** Move the camera smoothly to a new position (used to look at the back, left or bottom). */
  swingTo(pos: THREE.Vector3, ms = 700): Promise<void> {
    return new Promise((done) => {
      this.swing?.done();
      this.swing = { from: this.camera.position.clone(), to: pos.clone(), start: performance.now(), ms, done };
    });
  }

  /** A camera position looking straight-ish at a face, keeping a little perspective. */
  static viewOf(face: string): THREE.Vector3 {
    const d: Record<string, [number, number, number]> = {
      F: [2.2, 3.0, 10], B: [-2.2, 3.0, -10], R: [10, 3.0, -2.2],
      L: [-10, 3.0, 2.2], U: [1.6, 10.3, 3.2], D: [1.6, -10.3, 3.2],
    };
    return new THREE.Vector3(...d[face]);
  }

  static get home(): THREE.Vector3 {
    return HOME.clone();
  }

  private resize(): void {
    const { clientWidth: w, clientHeight: h } = this.container;
    if (!w || !h) return;
    this.renderer.setSize(w, h, false);
    this.camera.aspect = w / h;
    // Keep the whole cube in view on tall, narrow screens too.
    this.camera.fov = w < h ? 35 * Math.min(1.6, h / w) : 35;
    this.camera.updateProjectionMatrix();
  }

  private frame(t: number): void {
    if (this.swing) {
      const s = this.swing;
      const k = Math.min(1, (performance.now() - s.start) / s.ms);
      const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
      // Interpolate on the sphere so the camera keeps its distance.
      const r = THREE.MathUtils.lerp(s.from.length(), s.to.length(), e);
      this.camera.position.copy(s.from.clone().normalize().lerp(s.to.clone().normalize(), e).normalize().multiplyScalar(r));
      this.camera.lookAt(0, 0, 0);
      if (k >= 1) {
        this.swing = null;
        s.done();
      }
    }
    this.controls.update();
    this.cube.tick(t / 1000);
    this.renderer.render(this.scene, this.camera);
  }
}
