// 26 visible cubies at integer positions; sticker meshes keyed by their home facelet index.
import * as THREE from "three";
import { GEOMETRY } from "./facelets";
import type { Axis } from "./notation";

const CUBIE_SIZE = 0.95; // leaves a small gap between cubies
const STICKER_SIZE = 0.8;
const BODY_COLOR = 0x111214;

function roundedSquare(size: number, radius: number): THREE.ShapeGeometry {
  const s = size / 2;
  const r = radius;
  const shape = new THREE.Shape();
  shape.moveTo(-s + r, -s);
  shape.lineTo(s - r, -s);
  shape.quadraticCurveTo(s, -s, s, -s + r);
  shape.lineTo(s, s - r);
  shape.quadraticCurveTo(s, s, s - r, s);
  shape.lineTo(-s + r, s);
  shape.quadraticCurveTo(-s, s, -s, s - r);
  shape.lineTo(-s, -s + r);
  shape.quadraticCurveTo(-s, -s, -s + r, -s);
  return new THREE.ShapeGeometry(shape, 4);
}

export class CubeModel {
  readonly group = new THREE.Group();
  readonly cubies: THREE.Object3D[] = [];
  /** stickers[i] is the mesh that started at facelet i (it moves with its cubie). */
  readonly stickers: THREE.Mesh<THREE.ShapeGeometry, THREE.MeshStandardMaterial>[] = [];
  private homes = new Map<THREE.Object3D, THREE.Vector3>();
  private highlighted = new Set<number>();

  constructor() {
    const body = new THREE.BoxGeometry(CUBIE_SIZE, CUBIE_SIZE, CUBIE_SIZE);
    const bodyMat = new THREE.MeshStandardMaterial({ color: BODY_COLOR, roughness: 0.6, metalness: 0.1 });
    const stickerGeo = roundedSquare(STICKER_SIZE, 0.1);
    const byPos = new Map<string, THREE.Object3D>();

    for (let x = -1; x <= 1; x++)
      for (let y = -1; y <= 1; y++)
        for (let z = -1; z <= 1; z++) {
          if (x === 0 && y === 0 && z === 0) continue;
          const cubie = new THREE.Group();
          cubie.add(new THREE.Mesh(body, bodyMat));
          cubie.position.set(x, y, z);
          this.homes.set(cubie, new THREE.Vector3(x, y, z));
          this.cubies.push(cubie);
          this.group.add(cubie);
          byPos.set(`${x},${y},${z}`, cubie);
        }

    GEOMETRY.forEach(({ pos, normal }, i) => {
      const cubie = byPos.get(pos.join(","))!;
      const mat = new THREE.MeshStandardMaterial({ color: 0x888888, roughness: 0.35, metalness: 0.0 });
      const mesh = new THREE.Mesh(stickerGeo, mat);
      const n = new THREE.Vector3(...normal);
      mesh.position.copy(n.clone().multiplyScalar(CUBIE_SIZE / 2 + 0.002));
      mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), n);
      mesh.userData.facelet = i;
      cubie.add(mesh);
      this.stickers[i] = mesh;
    });
  }

  /** Put every cubie back at its home position with no rotation. */
  reset(): void {
    for (const c of this.cubies) {
      c.position.copy(this.homes.get(c)!);
      c.quaternion.identity();
    }
  }

  /** Reset, then colour each home sticker. ``colorOf`` maps a facelet character to a CSS colour. */
  setFacelets(state: string, colorOf: (ch: string) => string): void {
    this.reset();
    for (let i = 0; i < 54; i++) this.stickers[i].material.color.set(colorOf(state[i]));
  }

  /**
   * Read the current 3D arrangement back as a facelet string, given the string it was
   * set up from. Used by tests to check the 3D cube against the facelet model.
   */
  readState(initial: string): string {
    const out: string[] = new Array(54);
    const n = new THREE.Vector3();
    const q = new THREE.Quaternion();
    for (let i = 0; i < 54; i++) {
      const sticker = this.stickers[i];
      const cubie = sticker.parent!;
      q.copy(cubie.quaternion).multiply(sticker.quaternion);
      n.set(0, 0, 1).applyQuaternion(q).round();
      const p = cubie.position;
      const j = GEOMETRY.findIndex(
        (g) => g.pos[0] === Math.round(p.x) && g.pos[1] === Math.round(p.y) && g.pos[2] === Math.round(p.z)
          && g.normal[0] === n.x + 0 && g.normal[1] === n.y + 0 && g.normal[2] === n.z + 0,
      );
      out[j] = initial[i];
    }
    return out.join("");
  }

  cubiesInLayers(axis: Axis, layers: number[]): THREE.Object3D[] {
    return this.cubies.filter((c) => layers.includes(Math.round(c.position[axis])));
  }

  /** Make the stickers that started on these facelets glow (used to point at a face). */
  highlight(facelets: number[]): void {
    this.highlighted = new Set(facelets);
    this.stickers.forEach((s, i) => {
      if (!this.highlighted.has(i)) s.material.emissive.setHex(0x000000);
    });
  }

  /** Called every frame with the time in seconds, to pulse the highlight. */
  tick(t: number): void {
    const k = 0.18 + 0.14 * Math.sin(t * 5);
    for (const i of this.highlighted) this.stickers[i].material.emissive.setScalar(k);
  }
}
