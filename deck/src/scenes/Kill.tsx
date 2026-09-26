import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Line } from "@react-three/drei";
import * as THREE from "three";
import { Robot } from "../components/Robot";
import { DbTower, discY } from "../components/DbTower";
import { CameraRig, orbit } from "../components/CameraRig";
import { Brand, Caption, Fade, Overlay } from "../components/Overlay";
import { C, campaign, ease, fmt3, ramp, useClock } from "../lib";

export const KILL_DURATION = 6.5;

const TOWER_X = 2.3;
const ROBOT_SCALE = 0.36;

// Scene 3: the worker dies, the campaign in Atlas does not, and a fresh worker rehydrates from it.
export function Kill() {
  const getT = useClock();
  const a = useRef<THREE.Group>(null);
  const b = useRef<THREE.Group>(null);
  const matsA = useRef<THREE.MeshStandardMaterial[]>([]);
  const matsB = useRef<THREE.MeshStandardMaterial[]>([]);
  const flash = useRef<THREE.Mesh>(null);
  const ring = useRef<THREE.Mesh>(null);
  const beams = useRef<THREE.Group>(null);

  const count = campaign.event_count;
  const highlight = useMemo(
    () => campaign.experiments.map((e) => Math.round((e.n / (campaign.experiments.length + 1)) * count)),
    [count],
  );

  useFrame(() => {
    const t = getT();

    // Worker A: killed at 1.0 s, dissolves 2.4 -> 3.1 s.
    const fadeA = 1 - ramp(t, 2.4, 3.1);
    matsA.current.forEach((m) => (m.opacity = fadeA));
    if (a.current) {
      a.current.visible = fadeA > 0.01;
      a.current.position.y = -ramp(t, 2.4, 3.1) * 0.4;
    }
    // Red kill flash.
    if (flash.current) {
      const f = ramp(t, 0.95, 1.05) * (1 - ramp(t, 1.1, 1.9));
      (flash.current.material as THREE.MeshBasicMaterial).opacity = f * 0.55;
      flash.current.scale.setScalar(1 + ramp(t, 0.95, 1.9) * 2.5);
    }
    // Worker B assembles 3.3 -> 4.1 s.
    const s = ease(ramp(t, 3.3, 4.1));
    if (b.current) {
      b.current.visible = s > 0.001;
      b.current.scale.setScalar(ROBOT_SCALE * Math.max(0.001, s));
    }
    matsB.current.forEach((m) => (m.opacity = s));
    if (ring.current) {
      const r = ramp(t, 3.2, 4.3);
      ring.current.scale.setScalar(0.4 + r * 1.6);
      (ring.current.material as THREE.MeshBasicMaterial).opacity = Math.sin(r * Math.PI) * 0.9;
    }
    // Rehydrate beams from the tower into the new worker, 4.1 -> 5.2 s.
    if (beams.current) {
      const k = ramp(t, 4.1, 4.5) * (1 - ramp(t, 5.4, 5.9));
      beams.current.children.forEach((c, i) => {
        const line = c as unknown as { material: THREE.Material & { opacity: number; dashOffset: number } };
        line.material.opacity = k;
        line.material.dashOffset = -t * 2 - i * 0.3;
      });
    }
  });

  const beamPts = useMemo(
    () =>
      [0.2, 0.45, 0.7, 0.95].map((f) => {
        const from = new THREE.Vector3(TOWER_X - 0.5, discY(Math.round(f * (count - 1))), 0);
        const to = new THREE.Vector3(0.1, 1.55, 0.1);
        const mid = from.clone().lerp(to, 0.5).add(new THREE.Vector3(0, 0.6, 0.4));
        return new THREE.QuadraticBezierCurve3(from, mid, to).getPoints(24);
      }),
    [count],
  );

  return (
    <>
      <CameraRig shot={(t) => orbit(t, KILL_DURATION, -0.5, -0.15, 10.5, 3.0, [1.0, 1.7, 0])} />

      <Robot action={(t) => (t < 1.0 ? "Idle" : "Death")} groupRef={a} materialsRef={matsA} scale={ROBOT_SCALE} rotation-y={0.35} />
      <Robot action={(t) => (t < 5.0 ? "Idle" : "ThumbsUp")} groupRef={b} materialsRef={matsB} scale={0.001} rotation-y={0.35} position={[0, 0, 0.05]} />

      <mesh ref={flash} position={[0, 1.2, 0.2]}>
        <sphereGeometry args={[0.6, 32, 32]} />
        <meshBasicMaterial color={C.bad} transparent opacity={0} depthWrite={false} />
      </mesh>
      <mesh ref={ring} rotation-x={-Math.PI / 2} position={[0, 0.02, 0.05]}>
        <ringGeometry args={[0.5, 0.56, 64]} />
        <meshBasicMaterial color={C.accent} transparent opacity={0} depthWrite={false} />
      </mesh>

      <DbTower count={count} highlight={highlight} pulse={1} position={[TOWER_X, 0, 0]} />
      <group ref={beams}>
        {beamPts.map((pts, i) => (
          <Line key={i} points={pts} color={C.accent} lineWidth={2.5} dashed dashSize={0.18} gapSize={0.1} transparent opacity={0} />
        ))}
      </group>


    </>
  );
}

export function KillOverlay() {
  return (
    <Overlay>
      <Brand />
      <div className="hud">
        <div className="hud-row"><span className="hud-k">MongoDB Atlas</span><span className="hud-v">{campaign.source_campaign_id}</span></div>
        <div className="hud-row"><span className="hud-k">experiments stored</span><span className="hud-v">{campaign.used}</span></div>
        <div className="hud-row"><span className="hud-k">incumbent</span><span className="hud-v">{fmt3(campaign.incumbent!.val_balanced_accuracy)}</span></div>
      </div>
      <Fade from={0.95} to={2.6} className="alert">SIGKILL · worker process</Fade>
      <Fade from={4.2} className="note">new worker · rehydrate from Atlas</Fade>
      <Caption from={0.3}>Kill the worker. The campaign lives in Atlas.</Caption>
    </Overlay>
  );
}
