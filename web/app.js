// Second Shift dashboard. Every value comes from Atlas through the API; nothing is invented here.
const $ = (id) => document.getElementById(id);
const params = new URLSearchParams(location.search);
const state = { cid: params.get("campaign"), picked: params.has("campaign"), chart: null, eeg: false, feedKeys: "" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const acc = (x) => (x === null || x === undefined ? "—" : Number(x).toFixed(3));
const clock = (iso) => (iso ? new Date(iso).toLocaleTimeString([], { hour: "numeric", minute: "2-digit", second: "2-digit" }) : "");

const METHOD = { csp_lda: "CSP", bandpower_lr: "Band power" };
const BAND = { mu_8_12: "8–12 Hz", lowbeta_13_20: "13–20 Hz", highbeta_20_30: "20–30 Hz", beta_13_30: "13–30 Hz", broad_8_30: "8–30 Hz" };
const WIN = { "w0.5_2.5": "0.5–2.5 s", "w1.0_3.0": "1–3 s", "w1.5_3.5": "1.5–3.5 s" };
const CH = { central9: 9, motor21: 21, all64: 64 };
const short = (c) => (c ? `${METHOD[c.method] || c.method} · ${BAND[c.band] || c.band} · ${CH[c.channels]} electrodes` : "");

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) { const e = new Error(`${r.status}`); e.status = r.status; throw e; }
  return r.json();
}
const post = (path, body) => api(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body || {}) });

function toast(msg) {
  const t = $("toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast.h); toast.h = setTimeout(() => { t.hidden = true; }, 2500);
}

// ---------------------------------------------------------------- campaigns
async function loadCampaigns() {
  const list = await api("/api/campaigns");
  const sel = $("campaign-select");
  if (!state.picked && list.length) state.cid = list[0]._id;
  sel.innerHTML = list.map((c) => `<option value="${esc(c._id)}" ${c._id === state.cid ? "selected" : ""}>${esc(c._id)} · ${esc(c.state)}</option>`).join("");
}
$("campaign-select").addEventListener("change", (e) => { state.cid = e.target.value; state.picked = true; state.feedKeys = ""; poll(); });

// ---------------------------------------------------------------- status
function lifecycle(events) {
  for (let i = events.length - 1; i >= 0; i--) {
    const t = events[i].type;
    if (["worker_start", "worker_stop", "fault_injection", "worker_killed"].includes(t)) return events[i];
  }
  return null;
}

function status(c, events, exps) {
  if (c.state === "DONE") return { text: "Complete", tone: "done", sub: "sealed test set scored once" };
  const life = lifecycle(events);
  if (life && (life.type === "fault_injection" || life.type === "worker_killed")) return { text: "Worker down", tone: "bad", sub: "campaign state is safe in Atlas" };
  if (!life && exps.length === 0) return { text: "Ready", tone: "", sub: "press Start worker" };
  if (life && life.type === "worker_stop") return { text: "Paused", tone: "", sub: "no worker running" };
  const s = c.state;
  if (s === "WAITING") return { text: "Recovering", tone: "warn", sub: "waiting out the dead worker's lease" };
  if (s === "REHYDRATE") return { text: "Rebuilding", tone: "info", sub: "reading the campaign from Atlas" };
  if (s === "PLAN" || s === "VALIDATE") return { text: "Thinking", tone: "info", sub: "Claude is choosing the next experiment" };
  return { text: "Running", tone: "ok", sub: "measuring on real EEG" };
}

function renderKpis(c, exps, events, packet) {
  const st = status(c, events, exps);
  const k = $("k-status"); k.className = `kpi tone-${st.tone}`;
  $("kv-status").textContent = st.text; $("ks-status").textContent = st.sub;

  const inc = c.incumbent;
  $("kv-best").textContent = inc ? acc(inc.val_balanced_accuracy) : "—";
  $("ks-best").textContent = c.final ? `sealed test ${acc(c.final.test_balanced_accuracy)} · ${CH[c.final.config.channels]} electrodes`
    : inc ? short(inc.config) : "nothing within the limit yet";

  const max = c.budget.max_experiments;
  $("kv-used").textContent = c.used; $("kv-max").textContent = max;
  $("kb-budget").style.width = `${Math.min(100, (100 * c.used) / max)}%`;

  const lim = c.constraints.max_channels;
  $("kv-limit").textContent = lim;
  const first = (c.goal_history || [])[0];
  const changed = c.goal_version > 1 && first && first.constraints.max_channels !== lim;
  $("k-limit").classList.toggle("changed", !!changed);
  $("ks-limit").textContent = changed ? `cut from ${first.constraints.max_channels} · goal v${c.goal_version}` : `goal v${c.goal_version}`;
  document.querySelectorAll("#limit-seg button").forEach((b) => b.classList.toggle("on", Number(b.dataset.v) === lim));

  if (packet) {
    $("kv-tokens").textContent = packet.token_estimate.toLocaleString();
    $("kb-tokens").style.width = `${Math.min(100, (100 * packet.token_estimate) / packet.budget_tokens)}%`;
    $("ks-tokens").textContent = `of ${packet.budget_tokens.toLocaleString()} budget · rebuilt from Atlas`;
  } else {
    $("kv-tokens").textContent = "—"; $("kb-tokens").style.width = "0";
  }
}

// ---------------------------------------------------------------- chart
function markers(done, events) {
  const at = (ts) => done.filter((e) => e.finished_at && e.finished_at <= ts).length + 0.5;
  const out = [];
  for (const ev of events) {
    if (ev.type === "fault_injection" || ev.type === "worker_killed") out.push({ x: at(ev.ts), label: "Worker killed", color: "#ff5d5d" });
    if (ev.type === "worker_start" && ev.payload && ev.payload.resumed) out.push({ x: at(ev.ts), label: "Resumed from Atlas", color: "#00ed64" });
    if (ev.type === "goal_changed") {
      const p = ev.payload || {};
      out.push({ x: at(ev.ts), label: `Limit ${p.old_constraints?.max_channels ?? "?"} → ${p.new_constraints?.max_channels ?? "?"}`, color: "#ffb547" });
    }
  }
  // merge a kill and a resume that land in the same gap
  const merged = [];
  for (const m of out) {
    const same = merged.find((x) => Math.abs(x.x - m.x) < 0.01);
    if (same) { if (!same.label.includes(m.label)) same.label = same.label.startsWith("Worker killed") ? "Killed · resumed" : `${same.label} · ${m.label}`; }
    else merged.push({ ...m });
  }
  return merged;
}

const markerPlugin = {
  id: "markers",
  afterDatasetsDraw(chart) {
    const ms = chart.$markers || [];
    const { ctx, chartArea: a, scales: { x } } = chart;
    ms.forEach((m, i) => {
      const px = x.getPixelForValue(m.x);
      if (px < a.left || px > a.right) return;
      ctx.save();
      ctx.strokeStyle = m.color; ctx.lineWidth = 2; ctx.setLineDash([5, 4]);
      ctx.beginPath(); ctx.moveTo(px, a.top + 22); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.setLineDash([]);
      ctx.font = "600 12.5px Inter, sans-serif";
      const w = ctx.measureText(m.label).width + 16, y = a.top + 2 + (i % 2) * 0;
      const lx = Math.min(Math.max(px - w / 2, a.left), a.right - w);
      ctx.fillStyle = m.color; ctx.globalAlpha = 0.16;
      ctx.beginPath(); ctx.roundRect(lx, y, w, 20, 6); ctx.fill();
      ctx.globalAlpha = 1; ctx.fillStyle = m.color; ctx.fillText(m.label, lx + 8, y + 14);
      ctx.restore();
    });
  },
};

function renderChart(c, exps, events) {
  const done = exps.filter((e) => e.status === "done" && e.result).sort((a, b) => (a.finished_at < b.finished_at ? -1 : 1));
  const pts = done.map((e, i) => ({ x: i + 1, y: e.result.val_balanced_accuracy, eligible: e.eligible !== false, label: short(e.config) }));
  let best = null;
  const bestLine = pts.map((p) => { if (p.eligible && (best === null || p.y > best)) best = p.y; return { x: p.x, y: best }; }).filter((p) => p.y !== null);
  const max = Math.max(c.budget.max_experiments, pts.length);
  const data = {
    datasets: [
      { type: "line", data: bestLine, borderColor: "#00ed64", borderWidth: 3, stepped: "before", pointRadius: 0, order: 2 },
      { type: "scatter", data: pts, order: 1,
        pointRadius: 7, pointHoverRadius: 9, pointBorderWidth: 2.5,
        pointBackgroundColor: pts.map((p) => (p.eligible ? "#8b9bff" : "transparent")),
        pointBorderColor: pts.map((p) => (p.eligible ? "#8b9bff" : "#5b6476")) },
      { type: "line", data: [{ x: 0.5, y: 0.5 }, { x: max + 0.5, y: 0.5 }], borderColor: "#3a4152", borderDash: [4, 5], borderWidth: 1.5, pointRadius: 0, order: 3 },
    ],
  };
  if (!state.chart) {
    Chart.defaults.font.family = "Inter, sans-serif";
    Chart.defaults.color = "#8c95a8";
    state.chart = new Chart($("chart"), {
      data, plugins: [markerPlugin],
      options: {
        animation: { duration: 500 }, maintainAspectRatio: false, layout: { padding: { top: 4, right: 8 } },
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: (t) => `${t.raw.label || ""}  ${acc(t.raw.y)}` } } },
        scales: {
          x: { type: "linear", min: 0.5, max: max + 0.5, ticks: { stepSize: 1, callback: (v) => (Number.isInteger(v) ? `#${v}` : "") }, grid: { display: false }, border: { color: "#1e2430" } },
          y: { min: 0.4, max: 0.9, ticks: { stepSize: 0.1, callback: (v) => v.toFixed(1) }, grid: { color: "#161b25" }, border: { display: false },
               title: { display: true, text: "balanced accuracy (0.5 = chance)", color: "#5b6476", font: { size: 12 } } },
        },
      },
    });
  } else {
    state.chart.data = data;
    state.chart.options.scales.x.max = max + 0.5;
  }
  state.chart.$markers = markers(done, events);
  state.chart.update();
}

// ---------------------------------------------------------------- experiments
function renderExperiments(c, exps) {
  const incId = c.incumbent && c.incumbent.experiment_id;
  if (!exps.length) { $("exp-list").innerHTML = '<div class="empty">Waiting for the first proposal</div>'; return; }
  const rows = exps.map((e, i) => {
    const r = e.result, cfg = e.config, ch = CH[cfg.channels];
    const out = e.eligible === false;
    const pill = e.status === "done" ? "done" : e.status;
    return `<div class="exp-row ${e._id === incId ? "best" : ""} ${out ? "out" : ""}">
      <span class="n">${i + 1}</span>
      <span class="cfg"><b>${esc(METHOD[cfg.method])}</b> <span>· ${esc(BAND[cfg.band])} · ${esc(WIN[cfg.window])}</span></span>
      <span class="chip ${ch === 9 ? "c9" : ""}">${ch} ch</span>
      <span class="acc">${r ? `<span class="track"><i style="width:${Math.max(0, (r.val_balanced_accuracy - 0.4) / 0.5) * 100}%"></i></span>${acc(r.val_balanced_accuracy)}` : '<span class="track"></span>—'}</span>
      <span class="status-cell"><span class="pill ${pill}">${esc(pill)}</span>${e.attempt > 1 ? `<span class="pill retry">attempt ${e.attempt}</span>` : ""}${e._id === incId ? '<span class="pill best">best</span>' : ""}</span>
    </div>`;
  });
  $("exp-list").innerHTML = `<div class="exp-row head"><span>#</span><span>Configuration</span><span>Electrodes</span><span>Accuracy</span><span>Status</span></div>${rows.join("")}`;
}

// ---------------------------------------------------------------- feed
function feedItem(ev, idx) {
  const p = ev.payload || {};
  const n = (id) => (idx[id] ? `#${idx[id].n}` : "");
  switch (ev.type) {
    case "campaign_created": return { cls: "", ic: "★", t1: "Campaign created", t2: `goal: best accuracy with at most ${p.constraints?.max_channels} electrodes, ${p.max_experiments} experiments` };
    case "worker_start": return p.resumed
      ? { cls: "ok", ic: "↻", t1: "New worker rebuilt the campaign from Atlas", t2: `${p.counts?.done ?? 0} finished experiments reused, none recomputed` }
      : { cls: "", ic: "▶", t1: "Worker started", t2: "fresh campaign" };
    case "fault_injection": return { cls: "bad", ic: "✕", t1: "Worker killed mid experiment", t2: `SIGKILL while running ${n(p.experiment_id)}` };
    case "worker_killed": return { cls: "bad", ic: "✕", t1: "Worker killed from the dashboard", t2: "SIGKILL, no cleanup" };
    case "lease_expired": return { cls: "warn", ic: "⟲", t1: `Orphaned experiment ${n(p.experiment_id)} reclaimed`, t2: "rerunning it as attempt 2" };
    case "job_committed": { const e = idx[p.experiment_id]; return { cls: "res", ic: "✓", t1: `Experiment ${n(p.experiment_id)} measured ${acc(p.val_balanced_accuracy)}`, t2: e ? short(e.config) : "" }; }
    case "proposal": return { cls: "ai", ic: "✦", t1: `Claude proposed ${short(p.config)}`, t2: p.rationale || "" };
    case "context_reset": return { cls: "ctx", ic: "⌫", t1: "Context wiped", t2: "the next decision is rebuilt from Atlas alone" };
    case "goal_changed": return { cls: "warn", ic: "⚑", t1: `Electrode limit ${p.old_constraints?.max_channels} → ${p.new_constraints?.max_channels}`, t2: "past results re-ranked, nothing rerun" };
    case "jev_routed": return { cls: "jev", ic: "J", t1: `Jev filed Claude's note as ${String(p.label || "").replace("_", " ")}`, t2: p.model || "" };
    case "job_reused": return { cls: "ok", ic: "↺", t1: "Reused a finished experiment", t2: "no recompute" };
    case "stale_commit_rejected": return { cls: "warn", ic: "⛨", t1: "Blocked a stale write from a dead worker", t2: n(p.experiment_id) };
    case "finalized": return { cls: "ok", ic: "★", t1: `Campaign complete · sealed test ${acc(p.test_balanced_accuracy)}`, t2: short(p.config) };
    default: return null;
  }
}

function renderFeed(events, exps) {
  const idx = {};
  exps.forEach((e, i) => { idx[e._id] = { n: i + 1, config: e.config }; });
  const items = [];
  for (let i = events.length - 1; i >= 0 && items.length < 11; i--) {
    const it = feedItem(events[i], idx);
    if (it) items.push({ ...it, ts: events[i].ts });
  }
  const key = items.map((x) => x.ts).join("|");
  if (key === state.feedKeys) return;
  state.feedKeys = key;
  $("feed").innerHTML = items.length ? items.map((x) => `<li class="${x.cls}"><span class="ic">${x.ic}</span>
      <div><div class="t1">${esc(x.t1)}</div>${x.t2 ? `<div class="t2">${esc(x.t2)}</div>` : ""}</div>
      <span class="ts">${clock(x.ts)}</span></li>`).join("") : '<li class="empty">Nothing yet</li>';
}

// ---------------------------------------------------------------- packet
function renderPacket(p) {
  if (!p) { $("packet").innerHTML = '<div class="empty">No decision yet</div>'; $("packet-time").textContent = ""; return; }
  $("packet-time").textContent = `built ${clock(p.ts)}`;
  const g = p.goal || {}, inc = p.incumbent;
  const notes = (p.retrieved || []).slice(0, 2).map((m) => {
    const txt = String(m.text || "").replace(/^Unverified note \(routed by Jev as [a-z_]+\): /, "").replace(/^Planner hypothesis before running [^:]+: /, "");
    return `<div class="note"><div class="nh"><span class="tagx">${m.verified ? "verified" : "Jev · " + esc(m.kind)}</span><span class="tagx v">${esc(m.retrieval === "vector" ? "Vector Search" : "exact read")}</span></div><div class="nt">${esc(txt)}</div></div>`;
  }).join("");
  $("packet").innerHTML = `
    <div class="p-chips">
      <span class="p-chip ${g.goal_version > 1 ? "amber" : ""}">Goal <b>v${g.goal_version}</b></span>
      <span class="p-chip ${g.goal_version > 1 ? "amber" : ""}">Limit <b>${g.constraints?.max_channels} electrodes</b></span>
      <span class="p-chip">Best so far <b>${inc ? acc(inc.val_balanced_accuracy) : "none"}</b></span>
      <span class="p-chip"><b>${(p.tried || []).length}</b> tried</span>
      <span class="p-chip"><b>${(g.budget || {}).remaining ?? "?"}</b> left</span>
    </div>
    <div class="p-tokens"><span>${p.token_estimate.toLocaleString()} tokens</span><div class="bar"><i style="width:${(100 * p.token_estimate) / p.budget_tokens}%"></i></div><span>${p.budget_tokens.toLocaleString()}</span></div>
    ${notes ? `<div class="p-sec">Recalled from memory</div>${notes}` : ""}`;
}

// ---------------------------------------------------------------- eeg
async function loadEeg() {
  if (state.eeg) return;
  try {
    const d = await api("/api/eeg/preview");
    const ys = d.trace.channels.C3 || Object.values(d.trace.channels)[0];
    const cv = $("eeg"), ctx = cv.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    cv.width = cv.clientWidth * dpr; cv.height = cv.clientHeight * dpr; ctx.scale(dpr, dpr);
    const w = cv.clientWidth, h = cv.clientHeight, lo = Math.min(...ys), hi = Math.max(...ys);
    const grad = ctx.createLinearGradient(0, 0, w, 0); grad.addColorStop(0, "#5cc8ff"); grad.addColorStop(1, "#8b9bff");
    ctx.strokeStyle = grad; ctx.lineWidth = 1.4; ctx.beginPath();
    ys.forEach((y, i) => { const x = (i / (ys.length - 1)) * w, py = h - ((y - lo) / (hi - lo || 1)) * (h - 4) - 2; i ? ctx.lineTo(x, py) : ctx.moveTo(x, py); });
    ctx.stroke(); state.eeg = true;
  } catch (e) { /* the panel stays empty rather than inventing a signal */ }
}

// ---------------------------------------------------------------- results
async function renderResults() {
  const r = await api("/api/proof");
  const ab = r.ablation || {}, ev = ab.evidence || {}, rw = ab.recent_window || {};
  const cards = [
    { cls: "g", v: `${r.checks.passed}<small> / ${r.checks.total}</small>`, t: "reliability checks passed",
      s: `${r.checks.by_check.recovery?.passed ?? 0} crash recovery and ${r.checks.by_check.constraint?.passed ?? 0} goal change checks, on real runs` },
    { cls: "b", v: `${(r.memory.notes || 0).toLocaleString()}<small> notes</small>`, t: `still ${Number(r.memory.packet_tokens || 0).toLocaleString()} tokens per decision`,
      s: `memory grew a thousandfold, context stayed under its ${Number(r.memory.budget_tokens || 0).toLocaleString()} token budget` },
    { cls: "i", v: `${ev.cited}<small> / ${ev.decisions}</small>`, t: "decisions found the buried evidence",
      s: `vs ${rw.cited} / ${rw.decisions} with a recent window, same model, same guards` },
    { cls: "a", v: `${r.results_lost ?? "?"}<small> results lost</small>`, t: "across a crash and a goal change",
      s: "every finished experiment committed exactly once, sealed test scored once" },
  ];
  $("results").innerHTML = cards.map((c) => `<div class="rcard ${c.cls}"><div class="rv">${c.v}</div><div class="rt">${esc(c.t)}</div><div class="rs">${esc(c.s)}</div></div>`).join("");
}

const SNIPPETS = [
  { file: "harness/worker.py", fn: "rehydrate", title: "Rebuild from Atlas, every step",
    desc: "The worker keeps no memory of its own. Each decision starts by reading the campaign back from MongoDB." },
  { file: "harness/store.py", fn: "commit_result", title: "A dead worker can never overwrite a result",
    desc: "Results commit only under the current lease token, so a zombie attempt is rejected by the database." },
];

async function renderCode() {
  if (state.codeLoaded) return;
  const dedent = (code) => {
    const lines = code.split("\n"), pad = Math.min(...lines.filter((l) => l.trim()).map((l) => l.match(/^ */)[0].length));
    return lines.map((l) => l.slice(pad)).join("\n");
  };
  const parts = (await Promise.all(SNIPPETS.map((s) => api(`/api/source?file=${encodeURIComponent(s.file)}&fn=${s.fn}`))))
    .map((p) => ({ ...p, code: dedent(p.code) }));
  $("code").innerHTML = parts.map((p, i) => `<div class="code-card"><div class="ch"><h3>${esc(SNIPPETS[i].title)}</h3>
      <span class="cf">${esc(p.file)}:${p.start}</span></div><div class="cd">${esc(SNIPPETS[i].desc)}</div>
      <pre><code class="language-python">${esc(p.code)}</code></pre></div>`).join("");
  if (window.hljs) document.querySelectorAll("#code code").forEach((el) => hljs.highlightElement(el));
  state.codeLoaded = true;
}

function showView(v) {
  document.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b.dataset.view === v));
  $("view-live").hidden = v !== "live"; $("view-results").hidden = v !== "results"; $("view-code").hidden = v !== "code";
  if (v === "results") renderResults();
  if (v === "code") renderCode();
}
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

// ---------------------------------------------------------------- controls
async function control(fn, msg) { try { await fn(); toast(msg); poll(); } catch (e) { toast(`Failed: ${e.message}`); } }
$("btn-start").addEventListener("click", () => control(() => post("/api/worker/start", { campaign_id: state.cid }), "Worker started"));
$("btn-kill").addEventListener("click", () => control(() => post("/api/worker/kill"), "Worker killed (SIGKILL)"));
$("btn-reset").addEventListener("click", () => control(() => post(`/api/campaigns/${state.cid}/context-reset`), "Context wiped"));
document.querySelectorAll("#limit-seg button").forEach((b) => b.addEventListener("click", () => control(
  () => post(`/api/campaigns/${state.cid}/constraint`, { max_channels: Number(b.dataset.v), reason: `electrode limit set to ${b.dataset.v} from the dashboard` }),
  `Electrode limit set to ${b.dataset.v}`)));

// ---------------------------------------------------------------- poll
async function poll() {
  try {
    if (!state.cid) await loadCampaigns();
    if (!state.cid) return;
    const cid = state.cid;
    const [c, exps, events, packet, worker] = await Promise.all([
      api(`/api/campaigns/${cid}`),
      api(`/api/campaigns/${cid}/experiments`),
      api(`/api/campaigns/${cid}/events?limit=400`),
      api(`/api/campaigns/${cid}/packets/latest?strategy=evidence`).catch((e) => (e.status === 404 ? null : Promise.reject(e))),
      api("/api/worker/status"),
    ]);
    renderKpis(c, exps, events, packet);
    renderChart(c, exps, events);
    renderExperiments(c, exps);
    renderFeed(events, exps);
    renderPacket(packet);
    $("btn-start").disabled = worker.running || c.state === "DONE";
    $("btn-kill").disabled = !worker.running;
    $("live-text").textContent = c.state === "DONE" ? "Finished" : "Live";
  } catch (e) {
    $("live-text").textContent = "Reconnecting";
  }
}

(async () => {
  await loadCampaigns().catch(() => {});
  loadEeg();
  if (["results", "code"].includes(params.get("view"))) showView(params.get("view"));
  poll();
  setInterval(poll, 1500);
})();
