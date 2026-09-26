import test from "node:test";
import assert from "node:assert/strict";
import { newState, reconcile, numericalEvidence } from "../web/live-state.mjs";
const ev = (id, type, payload = {}) => ({ _id: id, type, payload });
const snap = (extra = {}) => ({
  campaign: { _id: "a", state: "PLAN", context_epoch: 0 },
  worker: { running: true, campaign_id: "a" },
  experiments: [],
  events: [],
  packet: null,
  ...extra,
});
test("remote dashboard preserves the recorded state without claiming a local worker", () => {
  const s = reconcile(newState(), snap({worker: {running: false, remote: true}}));
  assert.equal(s.phase, "decide");
  assert.equal(s.ownsWorker, false);
});
test("initial history is not animated and duplicate polling is idempotent", () => {
  let s = reconcile(newState(), snap({ events: [ev("1", "proposal")] }));
  assert.equal(s.event, null);
  s = reconcile(
    s,
    snap({ events: [ev("1", "proposal"), ev("2", "packet_built")] }),
  );
  assert.equal(s.event._id, "2");
  assert.equal(s.eventsPlayed, 1);
  s = reconcile(
    s,
    snap({ events: [ev("1", "proposal"), ev("2", "packet_built")] }),
  );
  assert.equal(s.event, null);
  assert.equal(s.eventsPlayed, 1);
});
test("crash does not erase campaign evidence; restart wins a rapid batch", () => {
  let s = reconcile(newState(), snap());
  s = reconcile(
    s,
    snap({ worker: { running: false }, events: [ev("1", "worker_killed")] }),
  );
  assert.equal(s.phase, "stopped");
  s = reconcile(
    s,
    snap({
      campaign: { _id: "a", state: "WAITING" },
      events: [ev("1", "worker_killed"), ev("2", "worker_start")],
    }),
  );
  assert.equal(s.phase, "waiting");
  assert.equal(s.event.type, "worker_start");
});
test("campaign switches reset event history and worker ownership", () => {
  const a = reconcile(newState(), snap({ events: [ev("1", "proposal")] }));
  const b = reconcile(
    a,
    snap({
      campaign: { _id: "b", state: "DONE" },
      events: [ev("9", "finalized")],
    }),
  );
  assert.equal(b.event, null);
  assert.equal(b.phase, "done");
  assert.equal(b.ownsWorker, false);
});
test("context reset withholds the old packet until rebuilt; recovery can reinitialize", () => {
  let s = reconcile(
    newState(),
    snap({
      campaign: { _id: "a", state: "REHYDRATE", context_epoch: 2 },
      packet: { context_epoch: 1 },
    }),
  );
  assert.equal(s.currentPacket, null);
  s = reconcile(
    { ...s, connected: false },
    snap({
      campaign: { _id: "a", state: "PLAN", context_epoch: 2 },
      packet: { context_epoch: 2 },
    }),
  );
  assert.equal(s.currentPacket.context_epoch, 2);
  assert.equal(s.connected, true);
});
test("numerical evidence is deduplicated by source identity, including the incumbent", () => {
  assert.deepEqual(
    numericalEvidence({
      incumbent: { experiment_id: "x" },
      leaders: [{ experiment_id: "x" }, { experiment_id: "y" }],
      recent: [{ experiment_id: "y" }],
    }).map((x) => x.experiment_id),
    ["x", "y"],
  );
});
test("a newly launched process rebuilds context while the previous crash is the latest event", () => {
  const s = reconcile(
    newState(),
    snap({
      campaign: { _id: "a", state: "EXECUTE" },
      events: [ev("k", "worker_killed")],
    }),
  );
  assert.equal(s.phase, "context");
});
test("an inactive campaign cannot keep animating an old executing state", () => {
  const s = reconcile(
    newState(),
    snap({
      campaign: { _id: "a", state: "EXECUTE" },
      worker: { running: true, campaign_id: "b" },
      events: [ev("s", "worker_start")],
    }),
  );
  assert.equal(s.phase, "paused");
});
