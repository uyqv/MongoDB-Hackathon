import { Suspense, useEffect, useMemo, useRef, useState, type RefObject } from "react";
import { useGLTF, useAnimations } from "@react-three/drei";
import { useFrame, type ThreeElements } from "@react-three/fiber";
import * as THREE from "three";
import { clone as cloneSkinned } from "three/examples/jsm/utils/SkeletonUtils.js";
import { C, useClock } from "../lib";

// RobotExpressive by Tomás Laulhé (CC0), from the three.js examples.
// Clips: Dance, Death, Idle, Jump, No, Punch, Running, Sitting, Standing,
// ThumbsUp, Walking, WalkJump, Wave, Yes.
const URL = "/models/RobotExpressive.glb";
const ONCE = new Set(["Death", "No", "Yes", "ThumbsUp", "Wave", "Jump", "Punch", "Standing", "Sitting"]);

type Props = {
  // Which clip plays at scene time t. Resolved inside the robot so the parent scene never re-renders.
  action: (t: number) => string;
  groupRef?: RefObject<THREE.Group | null>;
  materialsRef?: RefObject<THREE.MeshStandardMaterial[]>;
  color?: string;
} & ThreeElements["group"];

// Own Suspense boundary: while the GLB loads, only the robot is pending. Without it the whole
// scene suspends and drei <Html> siblings lose their DOM roots.
export function Robot(props: Props) {
  return (
    <Suspense fallback={null}>
      <RobotModel {...props} />
    </Suspense>
  );
}

function RobotModel({ action: actionAt, groupRef, materialsRef, color = C.accent, ...props }: Props) {
  const { scene, animations } = useGLTF(URL);
  const getT = useClock();
  const [action, setAction] = useState(() => actionAt(getT()));
  useFrame(() => {
    const next = actionAt(getT());
    if (next !== action) setAction(next);
  });
  const inner = useRef<THREE.Group>(null);
  const model = useMemo(() => {
    const m = cloneSkinned(scene) as THREE.Group;
    const mats: THREE.MeshStandardMaterial[] = [];
    m.traverse((o) => {
      const mesh = o as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mat = (mesh.material as THREE.MeshStandardMaterial).clone();
      if (mat.name === "Main") {
        mat.color.set(color);
        mat.emissive = new THREE.Color(color);
        mat.emissiveIntensity = 0.12;
      }
      mat.transparent = true;
      mesh.material = mat;
      mesh.castShadow = true;
      mats.push(mat);
    });
    if (materialsRef) materialsRef.current = mats;
    return m;
  }, [scene, color, materialsRef]);

  const { actions } = useAnimations(animations, inner);

  useEffect(() => {
    const a = actions[action];
    if (!a) return;
    a.reset();
    if (ONCE.has(action)) {
      a.setLoop(THREE.LoopOnce, 1);
      a.clampWhenFinished = true;
    }
    a.fadeIn(0.25).play();
    return () => {
      a.fadeOut(0.25);
    };
  }, [action, actions]);

  return (
    <group ref={groupRef} {...props}>
      <group ref={inner}>
        <primitive object={model} />
      </group>
    </group>
  );
}

useGLTF.preload(URL);
