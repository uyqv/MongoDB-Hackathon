import { useFrame, useThree } from "@react-three/fiber";
import { useMemo } from "react";
import * as THREE from "three";
import { useClock } from "../lib";

type Shot = { pos: [number, number, number]; look: [number, number, number] };

// Drives the camera from the scene clock so every take of a scene is frame-identical.
export function CameraRig({ shot }: { shot: (t: number) => Shot }) {
  const { camera } = useThree();
  const getT = useClock();
  const look = useMemo(() => new THREE.Vector3(), []);
  useFrame(() => {
    const s = shot(getT());
    camera.position.set(...s.pos);
    look.set(...s.look);
    camera.lookAt(look);
  });
  return null;
}

// Slow orbit around `target` from angle a0 to a1 (radians) over `dur` seconds.
export function orbit(t: number, dur: number, a0: number, a1: number, r: number, h: number,
  target: [number, number, number]): Shot {
  const x = Math.min(1, t / dur);
  const e = x * x * (3 - 2 * x);
  const a = a0 + (a1 - a0) * e;
  return { pos: [target[0] + Math.sin(a) * r, h, target[2] + Math.cos(a) * r], look: target };
}
