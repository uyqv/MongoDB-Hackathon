import { useLayoutEffect, useMemo, useRef } from "react";
import { useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";
import { C, useClock } from "../lib";

export const DISC = { radius: 0.75, height: 0.026, pitch: 0.034 };

export function discY(i: number) {
  return 0.05 + i * DISC.pitch;
}

// The campaign's history in Atlas: one disc per stored event, stacked like the database icon.
// `grow(t)` controls how many discs exist at time t; `highlight` marks experiment records.
export function DbTower({ count, grow, highlight = [], pulse = 0, ...props }: {
  count: number;
  grow?: (t: number) => number;
  highlight?: number[];
  pulse?: number;
} & ThreeElements["group"]) {
  const mesh = useRef<THREE.InstancedMesh>(null);
  const getT = useClock();
  const hi = useMemo(() => new Set(highlight), [highlight]);
  const dummy = useMemo(() => new THREE.Object3D(), []);
  const base = useMemo(() => new THREE.Color(C.accentDim), []);
  const bright = useMemo(() => new THREE.Color(C.accent), []);

  useLayoutEffect(() => {
    const m = mesh.current!;
    for (let i = 0; i < count; i++) m.setColorAt(i, hi.has(i) ? bright : base);
    m.instanceColor!.needsUpdate = true;
  }, [count, hi, base, bright]);

  useFrame(() => {
    const m = mesh.current;
    if (!m) return;
    const t = getT();
    const n = grow ? grow(t) : count;
    for (let i = 0; i < count; i++) {
      const shown = Math.min(1, Math.max(0, n - i)); // partial disc = dropping in
      const drop = (1 - shown) * 0.6;
      dummy.position.set(0, discY(i) + drop, 0);
      const s = shown <= 0 ? 0.0001 : 1;
      dummy.scale.set(s, s, s);
      dummy.updateMatrix();
      m.setMatrixAt(i, dummy.matrix);
    }
    m.instanceMatrix.needsUpdate = true;
    const mat = m.material as THREE.MeshStandardMaterial;
    mat.emissiveIntensity = 0.35 + pulse * 0.25 * (1 + Math.sin(t * 5));
  });

  return (
    <group {...props}>
      <instancedMesh ref={mesh} args={[undefined, undefined, count]} castShadow>
        <cylinderGeometry args={[DISC.radius, DISC.radius, DISC.height, 48]} />
        <meshStandardMaterial
          color="#ffffff"
          emissive={C.accentDim}
          emissiveIntensity={0.35}
          metalness={0.2}
          roughness={0.35}
        />
      </instancedMesh>
    </group>
  );
}
