import { Suspense, useCallback, useEffect, useMemo, useState, type ComponentType } from "react";
import { Canvas } from "@react-three/fiber";
import { Stage } from "./components/Stage";
import { ClockContext, type Clock } from "./lib";
import { Kill, KillOverlay, KILL_DURATION } from "./scenes/Kill";
import { Constraint, ConstraintOverlay, CONSTRAINT_DURATION } from "./scenes/Constraint";
import { Numbers, NUMBERS_DURATION } from "./scenes/Numbers";
import { Forget, ForgetOverlay, FORGET_DURATION } from "./scenes/Forget";
import { Packet, PacketOverlay, PACKET_DURATION } from "./scenes/Packet";

// `Component` renders inside the Canvas (3D) or as the whole frame (flat); `Hud` is the DOM layer on top.
type SceneDef = { name: string; Component: ComponentType; Hud?: ComponentType; duration: number; three: boolean };

export const SCENES: SceneDef[] = [
  { name: "forget", Component: Forget, Hud: ForgetOverlay, duration: FORGET_DURATION, three: true },
  { name: "packet", Component: Packet, Hud: PacketOverlay, duration: PACKET_DURATION, three: true },
  { name: "kill", Component: Kill, Hud: KillOverlay, duration: KILL_DURATION, three: true },
  { name: "constraint", Component: Constraint, Hud: ConstraintOverlay, duration: CONSTRAINT_DURATION, three: true },
  { name: "numbers", Component: Numbers, duration: NUMBERS_DURATION, three: false },
];

// ?scene=<name> plays one scene; ?scene=all plays them back to back.
// Space plays, R resets to the first frame, arrows step scenes, H toggles the help line.
// ?autoplay=1 starts immediately; ?t=<seconds> freezes at a time (for screenshots).
export function App() {
  const params = new URLSearchParams(location.search);
  const which = params.get("scene") ?? "all";
  const frozenAt = params.get("t");
  const playlist = useMemo(
    () => (which === "all" ? SCENES : SCENES.filter((s) => s.name === which)),
    [which],
  );
  const [idx, setIdx] = useState(0);
  const [take, setTake] = useState(0);
  const [help, setHelp] = useState(!params.has("autoplay") && frozenAt === null);
  const clock = useMemo<Clock>(() => ({ start: null }), [idx, take]); // eslint-disable-line react-hooks/exhaustive-deps

  const play = useCallback(() => {
    if (clock.start === null) clock.start = performance.now();
  }, [clock]);

  useEffect(() => {
    if (frozenAt !== null) clock.frozen = Number(frozenAt);
    else if (params.has("autoplay") || (which === "all" && idx > 0)) play();
  }, [clock]); // eslint-disable-line react-hooks/exhaustive-deps

  // Advance through the playlist when a scene's duration elapses.
  useEffect(() => {
    if (frozenAt !== null) return;
    const id = setInterval(() => {
      if (clock.start === null) return;
      const t = (performance.now() - clock.start) / 1000;
      if (t >= playlist[idx].duration && idx < playlist.length - 1) setIdx(idx + 1);
    }, 50);
    return () => clearInterval(id);
  }, [clock, idx, playlist, frozenAt]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.code === "Space") { e.preventDefault(); play(); }
      if (e.key === "r" || e.key === "R") { setIdx(0); setTake((k) => k + 1); }
      if (e.key === "h" || e.key === "H") setHelp((h) => !h);
      if (e.key === "ArrowRight") setIdx((i) => Math.min(playlist.length - 1, i + 1));
      if (e.key === "ArrowLeft") setIdx((i) => Math.max(0, i - 1));
    };
    addEventListener("keydown", onKey);
    return () => removeEventListener("keydown", onKey);
  }, [play, playlist.length]);

  const scene = playlist[idx];
  if (!scene) return <div className="help">unknown scene "{which}". Try: {SCENES.map((s) => s.name).join(", ")}, all</div>;
  const { Component, Hud } = scene;

  return (
    <ClockContext.Provider value={clock}>
      <div className="frame" key={`${idx}-${take}`}>
        {scene.three ? (
          <Canvas shadows dpr={[1, 2]} camera={{ fov: 38, near: 0.1, far: 80, position: [0, 2, 8] }}>
            {/* R3F does not bridge outer React context, so the clock is re-provided inside. */}
            <ClockContext.Provider value={clock}>
              <Suspense fallback={null}>
                <Stage />
                <Component />
              </Suspense>
            </ClockContext.Provider>
          </Canvas>
        ) : (
          <Component />
        )}
        {Hud && <Hud />}
      </div>
      {help && (
        <div className="help">
          {scene.name} ({idx + 1}/{playlist.length}, {scene.duration}s) · space play · R reset · ←/→ scene · H hide
        </div>
      )}
    </ClockContext.Provider>
  );
}
