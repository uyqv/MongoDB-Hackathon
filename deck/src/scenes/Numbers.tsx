import { useEffect, useRef, type ReactNode } from "react";
import { campaign, fmt3, ramp, useClock } from "../lib";

export const NUMBERS_DURATION = 6;

// Scene 5 (flat): the measured outcome of the real campaign. Every figure is read from campaign.json.
export function Numbers() {
  const f = campaign.final!;
  const u = campaign.llm_usage;
  const p = campaign.packet;
  return (
    <div className="numbers">
      <div className="brand"><span className="dot" /> Second Shift</div>
      <div className="num-grid">
        <Stat at={0.2} k="validation balanced accuracy" v={fmt3(f.val_balanced_accuracy)} sub="run 10 · subjects 1–5" />
        <Stat at={0.45} k="sealed test, scored once" v={fmt3(f.test_balanced_accuracy)} sub={`run 14 · n = ${f.n_test} trials`} />
        <Stat at={0.7} k="experiments" v={`${campaign.used} / ${campaign.budget_max_experiments}`} sub="real PhysioNet EEG, computed by code" />
        <Stat at={0.95} k="planner calls" v={String(u.calls)} sub={`${u.fallbacks} fallbacks · $${u.cost_usd.toFixed(3)} (provider)`} />
        <Stat at={1.2} k="briefing size" v={`${p.token_estimate}`} sub={`tokens (estimate) of a ${p.token_budget?.toLocaleString()} budget`} />
      </div>
      <Timed at={2.0} className="closer">
        A log records what was true. Second Shift knows what is still true.
      </Timed>
      <Timed at={2.6} className="source">
        MongoDB Atlas · campaign {campaign.source_campaign_id} · PhysioNet eegmmidb v1.0.0 (Schalk et al.)
      </Timed>
    </div>
  );
}

function Stat({ at, k, v, sub }: { at: number; k: string; v: string; sub: string }) {
  return (
    <Timed at={at} className="stat">
      <div className="stat-v">{v}</div>
      <div className="stat-k">{k}</div>
      <div className="stat-sub">{sub}</div>
    </Timed>
  );
}

// DOM counterpart of Overlay.Fade for the scene that has no canvas.
function Timed({ at, className, children }: { at: number; className: string; children: ReactNode }) {
  const el = useRef<HTMLDivElement>(null);
  const getT = useClock();
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const k = ramp(getT(), at, at + 0.45);
      if (el.current) {
        el.current.style.opacity = String(k);
        el.current.style.transform = `translateY(${(1 - k) * 14}px)`;
      }
      raf = requestAnimationFrame(tick);
    };
    tick();
    return () => cancelAnimationFrame(raf);
  }, [at, getT]);
  return <div ref={el} className={className} style={{ opacity: 0 }}>{children}</div>;
}
