// Curved arrow showing which way a layer (or the whole cube) turns.
import * as THREE from "three";
import { parseMove } from "./notation";

const AXIS_VEC = { x: new THREE.Vector3(1, 0, 0), y: new THREE.Vector3(0, 1, 0), z: new THREE.Vector3(0, 0, 1) };

export class Arrow {
  readonly object = new THREE.Group();
  private material = new THREE.MeshBasicMaterial({ color: 0xffc629, transparent: true, opacity: 0.95 });

  hide(): void {
    this.clear();
    this.object.visible = false;
  }

  show(move: string): void {
    this.clear();
    const spec = parseMove(move);
    const outer = spec.layers.length === 1 && spec.layers[0] !== 0;
    const whole = spec.layers.length === 3;
    const mean = spec.layers.reduce((a, b) => a + b, 0) / spec.layers.length;
    // Outer face: a small arc just in front of that face. Otherwise a ring around the cube.
    const offset = outer ? mean * 1.58 : whole ? 0 : mean;
    const radius = outer ? 1.05 : whole ? 2.25 : 1.95;
    const dir = Math.sign(spec.angle);
    const span = Math.abs(spec.quarters) === 2 ? Math.PI * 1.35 : Math.PI * 0.85;
    const thickness = whole ? 0.075 : 0.06;

    // Arc in the local XY plane; positive angle = anticlockwise seen from +Z (right-hand rule).
    const t0 = Math.PI * 0.25 - (dir * span) / 2;
    const pts: THREE.Vector3[] = [];
    const N = 40;
    for (let i = 0; i <= N; i++) {
      const t = t0 + (dir * span * i) / N;
      pts.push(new THREE.Vector3(radius * Math.cos(t), radius * Math.sin(t), 0));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 48, thickness, 8, false), this.material);
    const end = pts[N];
    const tangent = curve.getTangent(1);
    const head = new THREE.Mesh(new THREE.ConeGeometry(thickness * 3, thickness * 7, 16), this.material);
    head.position.copy(end);
    head.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);

    const g = new THREE.Group();
    g.add(tube, head);
    const axis = AXIS_VEC[spec.axis];
    g.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), axis);
    // setFromUnitVectors is ill-defined for opposite vectors; our axes are never -Z, so it's fine.
    g.position.copy(axis.clone().multiplyScalar(offset));
    this.object.add(g);
    this.object.visible = true;
  }

  private clear(): void {
    for (const child of [...this.object.children]) {
      child.traverse((o) => {
        if (o instanceof THREE.Mesh) o.geometry.dispose();
      });
      this.object.remove(child);
    }
  }
}
