import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Html, RoundedBox } from "@react-three/drei";
import * as THREE from "three";
import { CameraRig } from "../components/CameraRig";
import { Brand, Caption, Fade, Overlay, useTicker } from "../components/Overlay";
import { C, bestEligible, campaign, ease, fmt3, lerp, ramp, useClock } from "../lib";

export const CONSTRAINT_DURATION = 6;
const NEW_MAX = 9; // the demo's constraint change, 64 -> 9 (docs/WORKPLAN.md)

const FLIP = 1.1;
const SWEEP = [1.4, 2.6] as const;
const MOVE = [2.9, 3.7] as const;

const colX = (i: number, n: number) => (i - (n - 1) / 2) * 0.78;
const colZ = (i: number, n: number) => -Math.pow(i - (n - 1) / 2, 2) * 0.05;
const colH = (acc: number) => Math.max(0.15, (acc - 0.5) * 8);
const colW = (ch: number) => (ch >= 64 ? 0.56 : ch >= 21 ? 0.44 : 0.32);

// Scene 4: the channel budget drops, every result is re-checked, the incumbent is re-ranked.
export function Constraint() {
  const getT = useClock();
  const exps = campaign.experiments.filter((e) => e.val_balanced_accuracy != null && e.n_channels != null);
  const n = exps.length;
  const before = campaign.incumbent!;
  const after = bestEligible(NEW_MAX)!;
  const iBefore = exps.findIndex((e) => e.id === before.experiment_id);
  const iAfter = exps.findIndex((e) => e.id === after.id);

  const cols = useRef<(THREE.Group | null)[]>([]);
  const mats = useRef<(THREE.MeshStandardMaterial | null)[]>([]);
  const labels = useRef<(HTMLDivElement | null)[]>([]);
  const scanner = useRef<THREE.Mesh>(null);
  const marker = useRef<THREE.Group>(null);
  const green = useMemo(() => new THREE.Color(C.accent), []);
  const grey = useMemo(() => new THREE.Color(C.grey), []);

  const markerPos = (i: number) =>
    new THREE.Vector3(colX(i, n), colH(exps[i].val_balanced_accuracy!) + 0.45, colZ(i, n));

  useFrame(() => {
    const t = getT();
    exps.forEach((e, i) => {
      const hitAt = lerp(SWEEP[0], SWEEP[1], i / (n - 1));
      const k = ease(ramp(t, hitAt, hitAt + 0.35));
      const ok = e.n_channels! <= NEW_MAX;
      const g = cols.current[i];
      const m = mats.current[i];
      if (g) g.scale.y = ok ? 1 : 1 - k * 0.55; // ineligible results shrink and grey out; they are kept, not deleted
      if (m) {
        m.color.copy(green).lerp(ok ? green : grey, k);
        m.emissive.copy(green).lerp(ok ? green : grey, k);
        m.emissiveIntensity = ok ? 0.25 + k * 0.6 : 0.25 * (1 - k);
        m.opacity = ok ? 1 : 1 - k * 0.6;
      }
      const l = labels.current[i];
      if (l) l.style.opacity = String(ok ? 1 : 1 - k * 0.65);
    });
    if (scanner.current) {
      const s = ramp(t, SWEEP[0] - 0.2, SWEEP[1] + 0.2);
      scanner.current.position.x = lerp(colX(0, n) - 0.8, colX(n - 1, n) + 0.8, s);
      (scanner.current.material as THREE.MeshBasicMaterial).opacity = Math.sin(s * Math.PI) * 0.35;
    }
    if (marker.current) {
      const k = ease(ramp(t, MOVE[0], MOVE[1]));
      const p = markerPos(iBefore).lerp(markerPos(iAfter), k);
      p.y += Math.sin(k * Math.PI) * 0.9 + Math.sin(t * 3) * 0.05;
      marker.current.position.copy(p);
      marker.current.rotation.y = t * 1.6;
    }
  });

  return (
    <>
      <CameraRig
        shot={(t) => {
          const k = ease(ramp(t, 0, CONSTRAINT_DURATION));
          return { pos: [lerp(-1.2, 1.0, k), lerp(3.2, 2.7, k), lerp(8.2, 7.4, k)], look: [0, 1.0, 0] };
        }}
      />

      {exps.map((e, i) => {
        const h = colH(e.val_balanced_accuracy!);
        const w = colW(e.n_channels!);
        return (
          <group key={e.id} position={[colX(i, n), 0, colZ(i, n)]}>
            <group ref={(el) => { cols.current[i] = el; }}>
              <RoundedBox args={[w, h, w]} radius={0.04} position={[0, h / 2, 0]} castShadow>
                <meshStandardMaterial
                  ref={(m) => { mats.current[i] = m; }}
                  color={C.accent}
                  emissive={C.accent}
                  emissiveIntensity={0.25}
                  metalness={0.1}
                  roughness={0.35}
                  transparent
                />
              </RoundedBox>
            </group>
            <Html position={[0, -0.05, 0.45]} center>
              <div className="col-label" ref={(el) => { labels.current[i] = el; }}>
                <b>{fmt3(e.val_balanced_accuracy!)}</b>
                <span>{e.n_channels} ch</span>
              </div>
            </Html>
          </group>
        );
      })}

      <mesh ref={scanner} position={[0, 1.4, 0]}>
        <boxGeometry args={[0.05, 3.2, 2.2]} />
        <meshBasicMaterial color={C.warn} transparent opacity={0} depthWrite={false} />
      </mesh>

      <group ref={marker}>
        <mesh rotation-x={Math.PI}>
          <coneGeometry args={[0.16, 0.34, 4]} />
          <meshStandardMaterial color={C.warn} emissive={C.warn} emissiveIntensity={0.8} />
        </mesh>
      </group>

    </>
  );
}

export function ConstraintOverlay() {
  const before = campaign.incumbent!;
  const after = bestEligible(NEW_MAX)!;
  const chip = useRef<HTMLSpanElement>(null);
  useTicker((t) => {
    if (!chip.current) return;
    const flipped = t >= FLIP;
    chip.current.textContent = flipped
      ? `${campaign.constraints.max_channels} → ${NEW_MAX}`
      : String(campaign.constraints.max_channels);
    chip.current.className = flipped ? "chip chip-warn" : "chip";
  });
  return (
    <Overlay>
      <Brand />
      <div className="hud">
        <div className="hud-row">
          <span className="hud-k">max_channels</span>
          <span ref={chip} className="chip">{campaign.constraints.max_channels}</span>
        </div>
      </div>
      <Fade from={3.8} className="note">
        incumbent re-ranked · {fmt3(before.val_balanced_accuracy)} ({before.n_channels} ch) →{" "}
        {fmt3(after.val_balanced_accuracy!)} ({after.n_channels} ch)
      </Fade>
      <Caption from={0.3}>The rules change. It re-checks what is still valid.</Caption>
    </Overlay>
  );
}
