// Second Shift dashboard. OWNER: David. Vanilla JS, polls the API every 2 s.
// Every number drawn here comes from the API. Nothing is computed from a model.
"use strict";

const POLL_MS = 2000;
const TIMELINE_TYPES = new Set([
  "worker_start", "worker_stop", "worker_killed", "fault_injection", "context_reset", "goal_changed",
  "job_reused", "lease_expired", "stale_commit_rejected", "finalized",
]);

const state = { campaignId: null, userPicked: false, chart: null, fake: false };

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (x, d = 3) => (x === null || x === undefined ? "—" : Number(x).toFixed(d));
const localTime = (iso) => (iso ? new Date(iso).toLocaleTimeString() : "—");
const badge = (text, cls) => `<span class="badge ${cls}">${esc(text)}</span>`;

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    let detail = "";
    try { detail = (await r.json()).detail || ""; } catch (_) { /* not json */ }
    const err = new Error(`${r.status} ${detail || path}`);
    err.status = r.status;
    throw err;
  }
  return r.json();
}

function markFake(...docs) {
  for (const d of docs.flat()) if (d && d.fake === true) state.fake = true;
}

// ---------------------------------------------------------------- campaigns
async function loadCampaigns() {
  const list = await api("/api/campaigns");
  const sel = $("campaign-select");
  const current = sel.value;
  sel.innerHTML = list.map((c) =>
    `<option value="${esc(c._id)}">${esc(c._id)}${c.fake ? " (FAKE)" : ""} · ${esc(c.state)} · ${esc(localTime(c.created_at))}</option>`
  ).join("");
  if (!list.length) { state.campaignId = null; return; }
  if (state.userPicked && list.some((c) => c._id === current)) {
    state.campaignId = current;
  } else {
    state.campaignId = list[0]._id; // newest first
  }
  sel.value = state.campaignId;
}

// ---------------------------------------------------------------- panel 1
function renderGoal(c) {
  const hist = (c.goal_history || []).map((h) =>
    `<li>v${esc(h.version)} · max_channels ${esc(h.constraints?.max_channels)} · ${esc(localTime(h.changed_at))}${h.reason ? " · " + esc(h.reason) : ""}</li>`
  ).join("");
  const inc = c.incumbent;
  $("goal").innerHTML = `
    <dl class="kv">
      <dt>Objective</dt><dd>${esc(c.objective)}</dd>
      <dt>State</dt><dd>${esc(c.state)}</dd>
      <dt>Goal version</dt><dd>${esc(c.goal_version)}</dd>
      <dt>Max channels</dt><dd class="big">${esc(c.constraints?.max_channels)}</dd>
      <dt>Budget</dt><dd>${esc(c.used)} used / ${esc(c.remaining)} remaining of ${esc(c.budget?.max_experiments)}</dd>
      <dt>Context epoch</dt><dd>${esc(c.context_epoch)}</dd>
      <dt>Protocol</dt><dd>${esc(c.protocol_id)}</dd>
      <dt>Incumbent</dt><dd>${inc ? `${fmt(inc.val_balanced_accuracy)} · ${esc(inc.label)}` : '<span class="empty">none eligible yet</span>'}</dd>
      ${c.final ? `<dt>Final test</dt><dd>bal acc ${fmt(c.final.test_balanced_accuracy)} · F1 ${fmt(c.final.test_f1)}</dd>` : ""}
    </dl>
    <div class="muted" style="margin-top:10px">Goal history</div>
    <ol class="history">${hist || '<li class="empty">none</li>'}</ol>`;
}

// ---------------------------------------------------------------- panel 2
function renderChart(exps, campaign) {
  const done = exps.filter((e) => e.status === "done" && e.result && e.result.val_balanced_accuracy != null);
  const pts = done.map((e, i) => ({ x: i + 1, y: e.result.val_balanced_accuracy, e }));
  const elig = pts.filter((p) => p.e.eligible);
  const inel = pts.filter((p) => !p.e.eligible);
  let best = null;
  const bestLine = [];
  for (const p of pts) {
    if (p.e.eligible && (best === null || p.y > best)) best = p.y;
    if (best !== null) bestLine.push({ x: p.x, y: best });
  }
  const xmax = Math.max(pts.length, 1) + 0.5;
  const datasets = [
    { type: "scatter", label: "eligible", data: elig, backgroundColor: "#00ed64", borderColor: "#00ed64", pointRadius: 6 },
    { type: "scatter", label: "ineligible", data: inel, backgroundColor: "transparent", borderColor: "#5b6472", borderWidth: 2, pointRadius: 6 },
    { type: "line", label: "best eligible", data: bestLine, borderColor: "#00ed64", borderWidth: 1.5, stepped: true, pointRadius: 0, fill: false },
    { type: "line", label: "chance", data: [{ x: 0.5, y: 0.5 }, { x: xmax, y: 0.5 }], borderColor: "#8b95a3", borderDash: [6, 4], borderWidth: 1, pointRadius: 0 },
  ];
  const tooltip = {
    callbacks: {
      label: (ctx) => {
        const e = ctx.raw.e;
        return e ? `${fmt(ctx.raw.y)} · ${e.label}${e.eligible ? "" : " (ineligible)"}` : `${ctx.dataset.label} ${fmt(ctx.raw.y)}`;
      },
    },
  };
  if (!state.chart) {
    state.chart = new Chart($("metric-chart"), {
      data: { datasets },
      options: {
        animation: false, maintainAspectRatio: false, parsing: false,
        plugins: { legend: { display: false }, tooltip },
        scales: {
          x: { type: "linear", min: 0.5, max: xmax, ticks: { stepSize: 0.5, color: "#8b95a3", callback: (v) => (Number.isInteger(v) ? v : "") }, grid: { color: "#262c35" },
               title: { display: true, text: "done experiment #", color: "#8b95a3" } },
          y: { min: 0.3, max: 1.0, ticks: { color: "#8b95a3" }, grid: { color: "#262c35" },
               title: { display: true, text: "val balanced accuracy", color: "#8b95a3" } },
        },
      },
    });
  } else {
    state.chart.data.datasets = datasets;
    state.chart.options.scales.x.max = xmax;
    state.chart.update("none");
  }
}

// ---------------------------------------------------------------- panel 3
function renderExperiments(exps, campaign) {
  const incId = campaign.incumbent?.experiment_id;
  $("exp-table").querySelector("tbody").innerHTML = exps.map((e, i) => {
    const pb = e.proposed_by || {};
    const proposer = pb.fallback_used ? badge("FALLBACK", "b-fallback") : esc(pb.model || "—");
    const acc = e.result?.val_balanced_accuracy;
    const elig = e.eligible === true ? "yes" : e.eligible === false ? '<span class="no">no</span>' : "?";
    return `<tr class="${e._id === incId ? "incumbent" : ""}" title="${esc(pb.rationale || "")}">
      <td class="mono">${i + 1}</td>
      <td class="mono">${esc(e.label)}</td>
      <td>${badge(e.status, "s-" + e.status)}</td>
      <td>${esc(e.attempt)}</td>
      <td>${esc(e.n_channels)}</td>
      <td>${elig}</td>
      <td class="mono">${fmt(acc)}</td>
      <td>${proposer}</td>
      <td>${e.reused ? badge("reused", "b-reused") : ""}${e._id === incId ? badge("incumbent", "b-inc") : ""}${e.fake ? badge("FAKE", "b-fake") : ""}${e.error ? `<span class="muted" title="${esc(e.error)}">error</span>` : ""}</td>
    </tr>`;
  }).join("") || `<tr><td colspan="9" class="empty">no experiments yet</td></tr>`;
}

// ---------------------------------------------------------------- panel 4
function renderPacket(p) {
  if (!p) { $("packet").innerHTML = '<p class="empty">no packet built yet</p>'; return; }
  const pr = p.planner_result;
  const usage = pr?.usage;
  const mems = (p.retrieved || []).map((m) => `
    <div class="memory">
      <div>${badge(m.kind, m.kind === "synthetic_stress" ? "b-synthetic" : "")}${m.verified ? badge("verified", "b-verified") : ""}${badge(m.retrieval, "")}
        <span class="mono">${esc(m.memory_id)}</span> · score ${m.score == null ? "—" : fmt(m.score)}</div>
      <div class="text">${esc(m.text)}</div>
      <div class="meta">sources: ${esc((m.source_ids || []).join(", ") || "none")}</div>
    </div>`).join("");
  $("packet").innerHTML = `
    <dl class="kv">
      <dt>Strategy</dt><dd>${esc(p.strategy)}</dd>
      <dt>Goal version seen</dt><dd>${esc(p.goal?.goal_version)} · max_channels ${esc(p.goal?.constraints?.max_channels)}</dd>
      <dt>Built</dt><dd>${esc(localTime(p.ts))}</dd>
      <dt>Tokens</dt><dd>${esc(p.token_estimate)} (estimate) / budget ${esc(p.budget_tokens)}</dd>
      <dt>Tried keys</dt><dd>${esc((p.tried_keys || []).length)}</dd>
      ${pr ? `<dt>Planner</dt><dd>${esc(pr.action)} · ${pr.fallback_used ? badge("FALLBACK", "b-fallback") : esc(pr.model)}</dd>
      <dt>Planner usage</dt><dd>${usage ? `${esc(usage.input_tokens)} in / ${esc(usage.output_tokens ?? "—")} out · $${usage.cost_usd == null ? "—" : Number(usage.cost_usd).toFixed(4)} (${esc(usage.source)})` : "—"}</dd>
      <dt>Cited</dt><dd>${esc((pr.evidence_ids || []).join(", ") || "uncited")}</dd>` : ""}
    </dl>
    ${pr?.rationale ? `<p class="rationale">“${esc(pr.rationale)}”</p>` : ""}
    <div class="muted" style="margin-top:8px">Retrieved memories (${(p.retrieved || []).length})</div>
    ${mems || '<p class="empty">none</p>'}`;
}

// ---------------------------------------------------------------- panel 5
function describe(ev) {
  const p = ev.payload || {};
  switch (ev.type) {
    case "worker_start": {
      const done = p.counts?.done ?? p.reused_done ?? 0;
      return p.resumed ? `resumed · ${done} done reused, not recomputed` : "fresh start";
    }
    case "worker_stop": return `clean exit · ${p.steps ?? 0} steps`;
    case "fault_injection": return `${p.experiment_id ?? ""} · attempt ${p.attempt ?? "?"} · self-SIGKILL`;
    case "worker_killed": return `pid ${p.pid ?? "?"} · ${p.signal ?? ""}`;
    case "context_reset": return `epoch ${p.context_epoch}`;
    case "goal_changed": return `v${p.from_version} → v${p.to_version} · max_channels ${p.old_constraints?.max_channels} → ${p.new_constraints?.max_channels}${p.reason ? " · " + p.reason : ""}`;
    case "job_reused": case "lease_expired": case "stale_commit_rejected":
      return `${p.experiment_id ?? ""}${p.attempt ? " · attempt " + p.attempt : ""}`;
    case "finalized": return p.experiment_id ? `winner ${p.experiment_id}` : "";
    default: return "";
  }
}

function renderTimeline(events) {
  const rows = events.filter((e) => TIMELINE_TYPES.has(e.type)).reverse();
  $("timeline").innerHTML = rows.map((e) =>
    `<li class="ev-${esc(e.type)}"><span class="t">${esc(localTime(e.ts))}</span>
       <span><span class="type">${esc(e.type)}</span> <span class="muted">${esc(describe(e))}</span></span></li>`
  ).join("") || '<li class="empty">no timeline events yet</li>';
}

// ---------------------------------------------------------------- panel 6 (display only, loaded once)
const EEG_COLORS = { C3: "#7cc4ff", Cz: "#00ed64", C4: "#f5b942" };
const axis = (title) => ({ ticks: { color: "#8b95a3", maxTicksLimit: 7 }, grid: { color: "#262c35" },
  title: { display: true, text: title, color: "#8b95a3" } });

async function loadEeg() {
  let d;
  try {
    d = await api("/api/eeg/preview");
  } catch (err) {
    $("eeg-placeholder").textContent = `EEG preview unavailable: ${err.message}`;
    return;
  }
  $("eeg-placeholder").hidden = true;
  const tr = d.trace;
  // Offset channels vertically so the three traces don't overlap.
  const offsets = { C3: 60, Cz: 0, C4: -60 };
  new Chart($("eeg-trace"), {
    type: "line",
    data: {
      datasets: Object.entries(tr.channels).map(([ch, ys]) => ({
        label: ch, data: ys.map((y, i) => ({ x: tr.t[i], y: y + (offsets[ch] || 0) })),
        borderColor: EEG_COLORS[ch], borderWidth: 1, pointRadius: 0,
      })),
    },
    options: {
      animation: false, maintainAspectRatio: false, parsing: false,
      plugins: { legend: { labels: { color: "#e6e9ee", boxWidth: 10 } }, tooltip: { enabled: false } },
      scales: { x: { type: "linear", ...axis("s after cue") }, y: { ...axis(`${tr.units} (offset)`), ticks: { display: false } } },
    },
  });
  const f = d.psd.freqs;
  const avg = (byCh) => f.map((_, i) => Object.values(byCh).reduce((a, v) => a + v[i], 0) / Object.keys(byCh).length);
  new Chart($("eeg-psd"), {
    type: "line",
    data: {
      datasets: [
        { label: `T1 ${d.labels.T1} (n=${d.psd.n_epochs.T1})`, data: avg(d.psd.by_class.T1).map((y, i) => ({ x: f[i], y })),
          borderColor: "#7cc4ff", borderWidth: 1.5, pointRadius: 0 },
        { label: `T2 ${d.labels.T2} (n=${d.psd.n_epochs.T2})`, data: avg(d.psd.by_class.T2).map((y, i) => ({ x: f[i], y })),
          borderColor: "#f5b942", borderWidth: 1.5, pointRadius: 0 },
      ],
    },
    options: {
      animation: false, maintainAspectRatio: false, parsing: false,
      plugins: { legend: { labels: { color: "#e6e9ee", boxWidth: 10 } } },
      scales: { x: { type: "linear", ...axis("Hz") }, y: axis(d.psd.units) },
    },
  });
  $("eeg-trace-title").textContent = `C3 / Cz / C4, ${tr.filter}, 6 s from the ${tr.cue} (${tr.cue_label})`;
  $("eeg-psd-title").textContent = `PSD mean of C3/Cz/C4, ${d.psd.window}`;
  $("eeg-caption").textContent = `Source: ${d.source}. Display only; no metric uses this panel.`;
}

// ---------------------------------------------------------------- controls
const post = (path, body) => api(path, {
  method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}),
});

function renderWorker(st) {
  const el = $("worker-status");
  el.textContent = st.running ? `API worker: running pid ${st.pid} · ${st.campaign_id}` : "API worker: stopped";
  el.style.color = st.running ? "var(--accent)" : "var(--muted)";
  $("btn-start").disabled = st.running || !state.campaignId;
  $("btn-kill").disabled = !st.running;
}

async function control(label, fn) {
  const msg = $("control-msg");
  msg.textContent = `${label}…`;
  try {
    const out = await fn();
    msg.textContent = `${label}: ok ${out ? JSON.stringify(out).slice(0, 80) : ""}`;
  } catch (err) {
    msg.textContent = `${label} failed: ${err.message}`;
  }
  poll();
}

$("btn-start").addEventListener("click", () =>
  control("start", () => post("/api/worker/start", { campaign_id: state.campaignId })));
$("btn-kill").addEventListener("click", () => control("SIGKILL", () => post("/api/worker/kill")));
$("btn-reset").addEventListener("click", () =>
  control("context reset", () => post(`/api/campaigns/${state.campaignId}/context-reset`)));
$("btn-constraint").addEventListener("click", () => control("constraint", async () => {
  const c = await post(`/api/campaigns/${state.campaignId}/constraint`, {
    max_channels: Number($("sel-channels").value), reason: $("constraint-reason").value,
  });
  $("constraint-reason").value = "";
  return { goal_version: c.goal_version, max_channels: c.constraints.max_channels };
}));

// ---------------------------------------------------------------- loop
async function poll() {
  try {
    const health = await api("/api/health");
    $("db-name").textContent = `db: ${health.db}`;
    await loadCampaigns();
    renderWorker(await api("/api/worker/status"));
    const cid = state.campaignId;
    if (!cid) { $("goal").innerHTML = '<p class="empty">no campaigns yet</p>'; return; }
    const [camp, exps, events, packet] = await Promise.all([
      api(`/api/campaigns/${cid}`),
      api(`/api/campaigns/${cid}/experiments`),
      api(`/api/campaigns/${cid}/events?limit=500`),
      api(`/api/campaigns/${cid}/packets/latest?strategy=evidence`).catch((e) => (e.status === 404 ? null : Promise.reject(e))),
    ]);
    state.fake = false;
    markFake(camp, exps, events, packet ? [packet] : []);
    $("fake-banner").hidden = !state.fake;
    renderGoal(camp);
    renderChart(exps, camp);
    renderExperiments(exps, camp);
    renderPacket(packet);
    renderTimeline(events);
    $("last-poll").textContent = `updated ${new Date().toLocaleTimeString()}`;
  } catch (err) {
    $("last-poll").textContent = `poll failed: ${err.message}`;
  }
}

$("campaign-select").addEventListener("change", () => {
  state.userPicked = true;
  state.campaignId = $("campaign-select").value;
  poll();
});

poll();
setInterval(poll, POLL_MS);
loadEeg();
