import { useEffect, useRef, type ReactNode } from "react";
import { ramp, useClock } from "../lib";

// Runs `cb(t)` every animation frame with the scene clock. For DOM overlays, which live
// outside the Canvas and so cannot use useFrame.
export function useTicker(cb: (t: number) => void) {
  const getT = useClock();
  const ref = useRef(cb);
  ref.current = cb;
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      ref.current(getT());
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
}

// Full-frame HTML layer drawn over the canvas.
export function Overlay({ children }: { children: ReactNode }) {
  return <div className="overlay">{children}</div>;
}

// Fades in at `from`, out at `to` (seconds). Opacity is written per frame from the scene clock,
// so a paused scene shows exactly its t=0 state.
export function Fade({ from, to = 1e9, dur = 0.35, className, children }: {
  from: number; to?: number; dur?: number; className?: string; children: ReactNode;
}) {
  const el = useRef<HTMLDivElement>(null);
  useTicker((t) => {
    if (!el.current) return;
    const o = ramp(t, from, from + dur) * (1 - ramp(t, to, to + dur));
    el.current.style.opacity = String(o);
    el.current.style.transform = `translateY(${(1 - ramp(t, from, from + dur)) * 10}px)`;
  });
  return <div ref={el} className={className} style={{ opacity: 0 }}>{children}</div>;
}

export function Caption({ from, children }: { from: number; children: ReactNode }) {
  return (
    <Fade from={from} className="caption">
      {children}
    </Fade>
  );
}

export function Brand() {
  return (
    <div className="brand">
      <span className="dot" /> Second Shift
    </div>
  );
}

// Positions DOM element #id over a 3D point. Call from a useFrame inside the Canvas.
// Used instead of drei <Html> for labels that must survive Suspense remounts.
export function placeOver(id: string, world: { clone(): { project(c: unknown): { x: number; y: number; z: number } } }, camera: unknown) {
  const el = document.getElementById(id);
  if (!el) return;
  const p = world.clone().project(camera);
  el.style.left = `${(p.x * 0.5 + 0.5) * 100}%`;
  el.style.top = `${(-p.y * 0.5 + 0.5) * 100}%`;
  el.style.display = p.z > 1 ? "none" : "";
}
