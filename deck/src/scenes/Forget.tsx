import { useMemo, useRef } from "react";
import { useFrame, useThree } from "@react-three/fiber";
import { Edges, RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { Robot } from "../components/Robot";
import { EegRibbons } from "../components/EegRibbons";
import { CameraRig, orbit } from "../components/CameraRig";
import { Brand, Caption, Fade, Overlay, placeOver, useTicker } from "../components/Overlay";
import { C, ease, lerp, ramp, useClock } from "../lib";

export const FORGET_DURATION = 7;

// Illustrative, not data: a context window with room for 8 items receiving a stream of 18.
const ITEMS = 18;
const CAPACITY = 8;
const FIRST = 1.2;
const EVERY = 0.26;
const FLY = 0.4;
const WALK_END = 2.6;
const HEAD_Y = 2.45;
const TOWER_X = 1.7;

const spawn = (i: number) => FIRST + i * EVERY;
const arrive = (i: number) => spawn(i) + FLY;
const towerPos = (i: number) => new THREE.Vector3(TOWER_X + (i % 2) * 0.36, 0.17 + Math.floor(i / 2) * 0.34, 0);
const slotOffset = (s: number) =>
  new THREE.Vector3((s & 1 ? 0.19 : -0.19), (s & 2 ? 0.19 : -0.19), (s & 4 ? 0.19 : -0.19));

// Scene 1: history keeps arriving, the context window fills, and the oldest items fall out.
export function Forget() {
  const getT = useClock();
  const robot = useRef<THREE.Group>(null);
  const box = useRef<THREE.Group>(null);
  const boxLine = useRef<THREE.LineBasicMaterial>(null);
  const { camera } = useThree();
  const tower = useRef<(THREE.Mesh | null)[]>([]);
  const minis = useRef<(THREE.Mesh | null)[]>([]);
  const red = useMemo(() => new THREE.Color(C.bad), []);
  const green = useMemo(() => new THREE.Color(C.accent), []);

  useFrame(() => {
    const t = getT();

    const w = ease(ramp(t, 0, WALK_END));
    const rp = new THREE.Vector3(-1.3, 0, lerp(-2.6, 0, w));
    robot.current?.position.copy(rp);
    const boxPos = rp.clone().add(new THREE.Vector3(0, HEAD_Y, 0));
    box.current?.position.copy(boxPos);

    const full = t >= arrive(CAPACITY - 1);
    if (boxLine.current) boxLine.current.color.copy(full ? red : green);
    placeOver("lbl-box", boxPos.clone().add(new THREE.Vector3(0, 0.75, 0)), camera);
    placeOver("lbl-tower", new THREE.Vector3(TOWER_X + 0.18, -0.3, 0.4), camera);

    for (let i = 0; i < ITEMS; i++) {
      // History: every item lands on the tower and stays there.
      const tb = tower.current[i];
      if (tb) {
        const d = ramp(t, spawn(i) - 0.25, spawn(i));
        tb.visible = d > 0;
        tb.position.copy(towerPos(i)).add(new THREE.Vector3(0, (1 - ease(d)) * 1.5, 0));
      }
      // Working memory: a copy flies into the box; item i is evicted when item i+CAPACITY arrives.
      const m = minis.current[i];
      if (!m) continue;
      const mat = m.material as THREE.MeshStandardMaterial;
      const target = boxPos.clone().add(slotOffset(i % CAPACITY));
      const evictAt = i + CAPACITY < ITEMS ? arrive(i + CAPACITY) : Infinity;
      if (t < spawn(i)) {
        m.visible = false;
      } else if (t < evictAt) {
        m.visible = true;
        const f = ease(ramp(t, spawn(i), arrive(i)));
        m.position.copy(towerPos(i)).lerp(target, f);
        m.position.y += Math.sin(f * Math.PI) * 0.8;
        mat.color.copy(green);
        mat.emissive.copy(green);
        mat.opacity = 1;
      } else {
        const dt = t - evictAt;
        m.visible = dt < 1.4;
        m.position.set(target.x - dt * 0.9, target.y - 4.9 * dt * dt, target.z + dt * 0.6);
        m.rotation.set(dt * 4, dt * 3, 0);
        mat.color.copy(red);
        mat.emissive.copy(red);
        mat.opacity = 1 - ramp(dt, 0.6, 1.4);
      }
    }
  });

  return (
    <>
      <CameraRig shot={(t) => orbit(t, FORGET_DURATION, -0.25, 0.22, 8.4, 2.6, [0.2, 1.45, 0])} />
      <EegRibbons position={[0, 1.2, -7]} />

      <Robot action={(t) => (t < WALK_END ? "Walking" : t < 5.3 ? "Idle" : "No")} groupRef={robot} scale={0.42} />

      <group ref={box}>
        <mesh>
          <boxGeometry args={[0.9, 0.9, 0.9]} />
          <meshBasicMaterial transparent opacity={0.05} color={C.accent} depthWrite={false} />
          <Edges>
            <lineBasicMaterial ref={boxLine} color={C.accent} />
          </Edges>
        </mesh>
      </group>

      {Array.from({ length: ITEMS }, (_, i) => (
        <RoundedBox key={`t${i}`} ref={(el) => { tower.current[i] = el; }} args={[0.32, 0.3, 0.32]} radius={0.03} castShadow>
          <meshStandardMaterial color={C.accentDim} emissive={C.accentDim} emissiveIntensity={0.4} roughness={0.4} />
        </RoundedBox>
      ))}
      {Array.from({ length: ITEMS }, (_, i) => (
        <mesh key={`m${i}`} ref={(el) => { minis.current[i] = el; }} visible={false}>
          <boxGeometry args={[0.3, 0.3, 0.3]} />
          <meshStandardMaterial color={C.accent} emissive={C.accent} emissiveIntensity={0.5} transparent />
        </mesh>
      ))}

    </>
  );
}

export function ForgetOverlay() {
  const box = useRef<HTMLDivElement>(null);
  useTicker((t) => {
    if (!box.current) return;
    const full = t >= arrive(CAPACITY - 1);
    box.current.textContent = full ? "context window · full · oldest dropped" : "context window";
    box.current.className = full ? "tag tag-bad anchored" : "tag anchored";
  });
  return (
    <Overlay>
      <div id="lbl-box" ref={box} className="tag anchored">context window</div>
      <div id="lbl-tower" className="tag tag-muted anchored">everything it has done</div>
      <Brand />
      <Fade from={0.2} to={FORGET_DURATION} className="kicker">Long-horizon agents</Fade>
      <Caption from={0.5}>Long-running agents forget what they tried, and why.</Caption>
    </Overlay>
  );
}
