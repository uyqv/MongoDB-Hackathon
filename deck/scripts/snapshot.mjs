// Snapshot the real campaign from the Second Shift API into src/snapshot/campaign.json.
// Every number the scenes display comes from this file; nothing is typed in by hand.
//
// Usage: API=http://localhost:8001 CAMPAIGN=camp_0f8981ee node scripts/snapshot.mjs
// The API must be pointed at the real DB (DB_NAME=second_shift), not the fake dev DB.
import { writeFile } from "node:fs/promises";

const API = process.env.API ?? "http://localhost:8001";
const CID = process.env.CAMPAIGN ?? "camp_0f8981ee";

async function get(path) {
  const r = await fetch(API + path);
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status} ${await r.text()}`);
  return r.json();
}

const health = await get("/api/health");
if (health.db !== "second_shift") throw new Error(`API is on db=${health.db}; expected second_shift`);

const camp = await get(`/api/campaigns/${CID}`);
if (camp.fake) throw new Error("refusing to snapshot a fake campaign");
const exps = await get(`/api/campaigns/${CID}/experiments`);
const events = await get(`/api/campaigns/${CID}/events?limit=2000`);
const packet = await get(`/api/campaigns/${CID}/packets/latest`);
let eeg = null;
try { eeg = await get("/api/eeg/preview"); } catch (e) { console.warn("no EEG preview:", e.message); }

const experiments = exps.map((e, i) => ({
  n: i + 1,
  id: e._id,
  label: e.label,
  status: e.status,
  n_channels: e.n_channels ?? e.result?.n_channels ?? null,
  val_balanced_accuracy: e.result?.val_balanced_accuracy ?? null,
  reused: e.reused,
}));

const out = {
  source_campaign_id: CID,
  source_db: health.db,
  fetched_at: new Date().toISOString(),
  budget_max_experiments: camp.budget?.max_experiments ?? null,
  used: camp.used,
  constraints: camp.constraints,
  constraint_history: camp.constraint_history ?? null,
  incumbent: camp.incumbent,
  final: camp.final ?? null,
  llm_usage: camp.llm_usage,
  event_count: events.length,
  packet: {
    strategy: packet.strategy,
    token_estimate: packet.token_estimate ?? null,
    token_budget: packet.budget_tokens ?? null,
    retrieved: (packet.retrieved ?? []).length,
    recent: (packet.recent ?? []).length,
    pending: (packet.pending ?? []).length,
  },
  experiments,
  eeg: eeg && {
    source: eeg.source,
    sfreq_display: eeg.trace.sfreq_display,
    units: eeg.trace.units,
    filter: eeg.trace.filter,
    channels: eeg.trace.channels, // { C3: [...], Cz: [...], C4: [...] }
  },
};

await writeFile(new URL("../src/snapshot/campaign.json", import.meta.url), JSON.stringify(out, null, 2) + "\n");
console.log(`wrote campaign.json: ${experiments.length} experiments, ${events.length} events, incumbent ${camp.incumbent?.val_balanced_accuracy}`);
