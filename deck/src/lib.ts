import { createContext, useContext } from "react";
import data from "./snapshot/campaign.json";

export const campaign = data;
export type Experiment = (typeof data.experiments)[number];

// Palette shared with web/styles.css so the 3D cuts match the dashboard footage.
export const C = {
  bg: "#0b0e12",
  panel: "#141920",
  border: "#2a313c",
  text: "#f2f4f7",
  muted: "#a3adba",
  accent: "#00ed64",
  accentDim: "#0b7a3e",
  warn: "#f5b942",
  bad: "#ff5c5c",
  grey: "#5b6472",
  blue: "#5aa9ff",
};

export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const ramp = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));
export const ease = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);
export const lerp = (a: number, b: number, x: number) => a + (b - a) * x;
export const fmt3 = (x: number) => x.toFixed(3);

// Scene clock. Scenes sit frozen at t=0 until playback starts, so a screen
// recording can begin on a clean first frame.
export type Clock = { start: number | null; frozen?: number };
export const ClockContext = createContext<Clock>({ start: null });
export function useClock() {
  const clock = useContext(ClockContext);
  return () =>
    clock.frozen !== undefined ? clock.frozen : clock.start === null ? 0 : (performance.now() - clock.start) / 1000;
}

// Eligibility under a channel budget, same rule the harness applies (n_channels <= max_channels).
export function bestEligible(maxChannels: number): Experiment | null {
  let best: Experiment | null = null;
  for (const e of campaign.experiments) {
    if (e.status !== "done" || e.val_balanced_accuracy == null || e.n_channels == null) continue;
    if (e.n_channels > maxChannels) continue;
    if (!best || e.val_balanced_accuracy > (best.val_balanced_accuracy ?? 0)) best = e;
  }
  return best;
}
