import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Edges } from "@react-three/drei";
import * as THREE from "three";
import { Robot } from "../components/Robot";
import { DbTower, discY } from "../components/DbTower";
import { CameraRig } from "../components/CameraRig";
import { Brand, Caption, Fade, Overlay, useTicker } from "../components/Overlay";
import { C, campaign, ease, lerp, ramp, useClock } from "../lib";

export const PACKET_DURATION = 6.5;

const TOWER_X = 1.9;
const PACKET = new THREE.Vector3(-0.75, 1.55, 0.3);
const GROW = [0, 2.4] as const;

type Card = { kind: string; color: string; from: number };

// Scene 2: the history in Atlas grows; each decision gets a small briefing built from it.
export function Packet() {
  const getT = useClock();
  const count = campaign.event_count;
  const nExp = campaign.experiments.length;
  const expDisc = (n: number) => Math.round((n / (nExp + 1)) * count);
  const highlight = useMemo(() => campaign.experiments.map((e) => expDisc(e.n)), []); // eslint-disable-line react-hooks/exhaustive-deps

  // Card counts are the real latest evidence packet's sections (goal, incumbent, recent, retrieved, pending).
  const cards = useMemo<Card[]>(() => {
    const p = campaign.packet;
    const inc = campaign.experiments.find((e) => e.id === campaign.incumbent?.experiment_id);
    const out: Card[] = [{ kind: "goal", color: C.text, from: 0 }];
    if (inc) out.push({ kind: "incumbent", color: C.warn, from: expDisc(inc.n) });
    campaign.experiments.slice(-p.recent).forEach((e) => out.push({ kind: "recent", color: C.accent, from: expDisc(e.n) }));
    for (let i = 0; i < p.retrieved; i++) out.push({ kind: "retrieved", color: C.blue, from: Math.round(count * (0.15 + i * 0.17)) });
    for (let i = 0; i < p.pending; i++) out.push({ kind: "pending", color: C.muted, from: count - 1 });
    return out;
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const cardRefs = useRef<(THREE.Mesh | null)[]>([]);
  const frame = useRef<THREE.LineBasicMaterial>(null);

  useFrame(() => {
    const t = getT();
    if (frame.current) frame.current.opacity = 0.3 + 0.7 * ramp(t, 2.4, 2.8);

    cards.forEach((c, j) => {
      const m = cardRefs.current[j];
      if (!m) return;
      const s = 2.7 + j * 0.2;
      const f = ease(ramp(t, s, s + 0.55));
      m.visible = t >= s;
      const from = new THREE.Vector3(TOWER_X, discY(c.from), 0);
      const to = PACKET.clone().add(new THREE.Vector3(0, -0.42 + j * 0.105, 0));
      m.position.copy(from).lerp(to, f);
      m.position.y += Math.sin(f * Math.PI) * 0.7;
      m.position.z += Math.sin(f * Math.PI) * 0.6;
      m.rotation.y = (1 - f) * 1.2;
    });
  });

  return (
    <>
      <CameraRig
        shot={(t) => {
          const k = ease(ramp(t, 0, PACKET_DURATION));
          return { pos: [lerp(2.2, -0.2, k), lerp(4.6, 3.3, k), lerp(11.5, 9.8, k)], look: [lerp(1.0, 0.3, k), lerp(2.3, 1.9, k), 0] };
        }}
      />

      <Robot action={(t) => (t < 4.9 ? "Idle" : "Yes")} scale={0.42} position={[-2.2, 0, 0.2]} rotation-y={0.6} />
      <DbTower count={count} highlight={highlight} grow={(t) => count * ease(ramp(t, GROW[0], GROW[1]))} position={[TOWER_X, 0, 0]} />

      <mesh position={PACKET}>
        <boxGeometry args={[0.8, 1.15, 0.6]} />
        <meshBasicMaterial transparent opacity={0.06} color={C.accent} depthWrite={false} />
        <Edges>
          <lineBasicMaterial ref={frame} color={C.accent} transparent opacity={0.3} />
        </Edges>
      </mesh>
      {cards.map((c, j) => (
        <mesh key={j} ref={(el) => { cardRefs.current[j] = el; }} visible={false} castShadow>
          <boxGeometry args={[0.62, 0.06, 0.42]} />
          <meshStandardMaterial color={c.color} emissive={c.color} emissiveIntensity={0.45} roughness={0.3} />
        </mesh>
      ))}

    </>
  );
}

export function PacketOverlay() {
  const counter = useRef<HTMLSpanElement>(null);
  useTicker((t) => {
    if (counter.current) counter.current.textContent = String(Math.round(campaign.event_count * ease(ramp(t, GROW[0], GROW[1]))));
  });
  return (
    <Overlay>
      <Brand />
      <div className="hud hud-left">
        <div className="hud-row">
          <span className="hud-k">history in Atlas</span>
          <span className="hud-v"><span ref={counter}>0</span> events</span>
        </div>
        <Fade from={2.5} className="hud-row">
          <span className="hud-k">briefing per decision</span>
          <span className="hud-v">
            {campaign.packet.token_estimate} / {campaign.packet.token_budget?.toLocaleString()} tokens <em>(estimate)</em>
          </span>
        </Fade>
        <Fade from={2.5}>
          <div className="bar"><div style={{ width: `${(100 * campaign.packet.token_estimate) / (campaign.packet.token_budget ?? 1)}%` }} /></div>
        </Fade>
        <Fade from={4.4} className="legend">
          <span><i style={{ background: C.text }} />goal</span>
          <span><i style={{ background: C.warn }} />incumbent</span>
          <span><i style={{ background: C.accent }} />recent ×{campaign.packet.recent}</span>
          <span><i style={{ background: C.blue }} />retrieved ×{campaign.packet.retrieved}</span>
          <span><i style={{ background: C.muted }} />pending ×{campaign.packet.pending}</span>
        </Fade>
      </div>
      <Caption from={0.4}>History grows. The briefing stays bounded.</Caption>
    </Overlay>
  );
}
