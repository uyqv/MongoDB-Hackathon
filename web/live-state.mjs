// Pure display state. The database remains the authority for results and worker state.
export const phaseFor = (s) =>
  ({
    REHYDRATE: "context",
    PLAN: "decide",
    VALIDATE: "decide",
    QUEUE: "queued",
    EXECUTE: "experiment",
    COMMIT: "memory",
    WAITING: "waiting",
    DONE: "done",
    FAILED: "failed",
  })[s] || "ready";
const priority = {
  worker_killed: 100,
  fault_injection: 100,
  worker_start: 95,
  goal_changed: 90,
  context_reset: 85,
  job_committed: 80,
  memory_added: 70,
  packet_built: 60,
  job_claimed: 50,
  proposal: 40,
  finalized: 30,
};
export function newState(cid = null) {
  return {
    cid,
    initialized: false,
    seen: new Set(),
    phase: "ready",
    event: null,
    eventsPlayed: 0,
    connected: true,
  };
}
export function reconcile(previous, snapshot) {
  const { campaign: c, events = [], worker = {}, packet } = snapshot;
  let prev = previous.cid === c._id ? previous : newState(c._id);
  const fresh = prev.initialized
    ? events.filter((e) => !prev.seen.has(e._id))
    : [];
  // Keep only the current overlapping event window. Its IDs prevent duplicate animations.
  const seen = new Set(events.map((e) => e._id));
  const life = [...events]
    .reverse()
    .find((e) =>
      [
        "worker_start",
        "worker_stop",
        "worker_killed",
        "fault_injection",
      ].includes(e.type),
    );
  const ownsWorker = worker.running && worker.campaign_id === c._id;
  let phase = phaseFor(c.state);
  if (!worker.remote && c.state !== "DONE" && c.state !== "FAILED") {
    if (ownsWorker && ["worker_killed", "fault_injection"].includes(life?.type))
      phase = "context";
    if (
      !ownsWorker &&
      ["worker_killed", "fault_injection"].includes(life?.type)
    )
      phase = "stopped";
    else if (!ownsWorker && life?.type === "worker_stop") phase = "paused";
    else if (!life && !snapshot.experiments?.length && !ownsWorker)
      phase = "ready";
    else if (!ownsWorker) phase = "paused";
  }
  const meaningful = fresh.filter((e) => priority[e.type]);
  // A restart supersedes a crash even if both arrive in one network response.
  const latestLife = meaningful
    .filter((e) =>
      ["worker_start", "worker_killed", "fault_injection"].includes(e.type),
    )
    .at(-1);
  const event =
    latestLife ||
    meaningful.reduce(
      (best, e) =>
        !best || priority[e.type] >= priority[best.type] ? e : best,
      null,
    );
  const currentPacket =
    packet && (packet.context_epoch ?? 0) >= (c.context_epoch ?? 0)
      ? packet
      : null;
  return {
    ...prev,
    cid: c._id,
    initialized: true,
    seen,
    phase,
    event,
    connected: true,
    currentPacket,
    ownsWorker,
    eventsPlayed: prev.eventsPlayed + meaningful.length,
    freshIds: meaningful.map((e) => e._id),
  };
}
export function numericalEvidence(packet) {
  if (!packet) return [];
  const rows = [
    packet.incumbent,
    ...(packet.leaders || []),
    ...(packet.laggards || []),
    ...(packet.recent || []),
  ].filter(Boolean);
  return [
    ...new Map(
      rows.filter((x) => x.experiment_id).map((x) => [x.experiment_id, x]),
    ).values(),
  ];
}
