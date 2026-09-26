import { newState, reconcile, numericalEvidence } from "./live-state.mjs";
const $ = (id) => document.getElementById(id),
  SVG = "http://www.w3.org/2000/svg";
const params = new URLSearchParams(location.search);
let live = newState(params.get("campaign")),
  data = null,
  generation = 0,
  controller = null,
  inFlight = false,
  pollTimer = null,
  follow = true,
  view = "live",
  busy = false,
  lastSignature = "",
  drawerType = null,
  drawerPacket = null,
  animatedId = null;
const reduced = matchMedia("(prefers-reduced-motion: reduce)");
const esc = (v) =>
  String(v ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const fmt = (v) => (v == null ? "—" : Number(v).toFixed(3)),
  num = (v) => Number(v || 0).toLocaleString();
const CH = { central9: 9, motor21: 21, all64: 64 },
  METHOD = { csp_lda: "CSP + LDA", bandpower_lr: "Band power + LR" };
const statusText = {
  ready: "Ready to begin",
  context: "Rebuilding context",
  decide: "Choosing the next step",
  experiment: "An experiment is running",
  queued: "Experiment queued",
  memory: "Saving the result",
  waiting: "Recovering from memory",
  stopped: "Worker stopped. Memory intact.",
  paused: "Worker paused",
  done: "Campaign complete",
  failed: "Campaign needs attention",
};
const relevant = [
  "worker_start",
  "worker_killed",
  "fault_injection",
  "context_reset",
  "goal_changed",
  "packet_built",
  "proposal",
  "job_claimed",
  "job_committed",
  "job_failed",
  "memory_added",
  "lease_expired",
  "finalized",
];
async function api(path, options = {}) {
  const r = await fetch(path, options);
  if (!r.ok) {
    const e = new Error(`Request failed (${r.status})`);
    e.status = r.status;
    throw e;
  }
  return r.json();
}
const post = (path, body = {}) =>
  api(path, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
function text(id, v) {
  if ($(id).textContent !== String(v)) $(id).textContent = v;
}
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => ($("toast").hidden = true), 2800);
}
function svgEl(tag, attrs = {}) {
  const el = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  return el;
}
function pulse(el, cls) {
  el.classList.remove(cls);
  void el.offsetWidth;
  el.classList.add(cls);
  setTimeout(() => el.classList.remove(cls), 850);
}
function travel(edge) {
  if (
    reduced.matches ||
    !live.connected ||
    ["stopped", "paused", "done", "failed"].includes(live.phase)
  )
    return;
  const path = $(`edge-${edge}`);
  if (!path) return;
  for (let i = 0; i < 3; i++) {
    const dot = svgEl("circle", {
      r: i === 0 ? 3.5 : 2.5,
      class: "travel-dot",
    });
    const motion = svgEl("animateMotion", {
      dur: "1.05s",
      begin: `${i * 0.15}s`,
      path: path.getAttribute("d"),
      fill: "freeze",
      calcMode: "spline",
      keyTimes: "0;1",
      keySplines: ".2 .65 .3 1",
    });
    dot.append(motion);
    $("travel-signals").append(dot);
    motion.beginElementAt(i * 0.15);
    setTimeout(() => dot.remove(), 1700);
  }
}
function animateEvent(e) {
  if (!e || reduced.matches || e._id === animatedId) return;
  animatedId = e._id;
  if (e.type === "packet_built") {
    pulse($("packet-art"), "rebuilding");
    travel("context");
    travel("decide");
  }
  if (e.type === "proposal" || e.type === "job_claimed") travel("experiment");
  if (e.type === "job_committed" || e.type === "memory_added") {
    travel("memory");
    pulse($("memory"), "received");
  }
  if (e.type === "worker_start") {
    pulse($("packet-art"), "rebuilding");
    travel("context");
  }
  if (e.type === "goal_changed") pulse($("electrode-grid"), "changed");
}
for (let i = 0; i < 64; i++) {
  const dot = document.createElement("i");
  dot.className = "electrode";
  dot.style.setProperty("--i", i);
  dot.setAttribute("aria-hidden", "true");
  $("electrode-grid").append(dot);
}
async function loadCampaigns() {
  const list = await api("/api/campaigns");
  const available = list.filter((c) => !c.fake || c._id === live.cid);
  if (!live.cid && available.length) live.cid = available[0]._id;
  $("campaign-select").innerHTML = available
    .map(
      (c) =>
        `<option value="${esc(c._id)}" ${c._id === live.cid ? "selected" : ""}>${esc(c._id)}</option>`,
    )
    .join("");
  if (!available.length) {
    text("state-label", "No research campaign yet");
    text("connection", "No campaigns");
  }
}
function setFocus() {
  const focus =
    follow &&
    !reduced.matches &&
    ["context", "decide", "experiment"].includes(live.phase)
      ? live.phase
      : "overview";
  $("camera").dataset.focus = focus;
}
function renderPacket(packet) {
  const exact = numericalEvidence(packet),
    notes = packet?.retrieved || [];
  const sig = JSON.stringify([
    packet?.packet_id,
    packet?.token_estimate,
    exact.map((x) => x.experiment_id),
    notes.map((x) => x.memory_id),
  ]);
  $("packet-art").classList.toggle("empty", !packet);
  if (sig !== lastSignature) {
    lastSignature = sig;
    $("evidence-marks").innerHTML =
      exact
        .slice(0, 12)
        .map(() => '<i class="evidence-mark"></i>')
        .join("") +
      notes
        .slice(0, 6)
        .map(() => '<i class="evidence-mark note"></i>')
        .join("");
  }
  text("packet-count", `${exact.length + notes.length} sources`);
  text(
    "packet-tokens",
    packet
      ? `${num(packet.token_estimate)} / ${num(packet.budget_tokens)} tokens`
      : "Awaiting fresh evidence",
  );
  text(
    "packet-version",
    packet
      ? `goal ${packet.goal?.goal_version ?? data.campaign.goal_version}`
      : "",
  );
}
function renderMemory(c, exps, fresh) {
  const done = exps.filter((e) => e.status === "done" && e.result);
  text("saved-count", done.length);
  text("best-result", fmt(c.incumbent?.val_balanced_accuracy));
  text(
    "best-detail",
    c.final
      ? `sealed test ${fmt(c.final.test_balanced_accuracy)}`
      : c.incumbent
        ? `${c.incumbent.n_channels || CH[c.incumbent.config?.channels]} electrodes · validation`
        : "No eligible result yet",
  );
  text(
    "memory-status",
    live.phase === "stopped"
      ? "Completed results remain in Atlas"
      : live.phase === "waiting"
        ? "Waiting for the previous lease to expire"
        : c.goal_version > 1
          ? `Goal ${c.goal_version} · results checked against ${c.constraints.max_channels} electrodes`
          : "Campaign state persists across restarts",
  );
  text("campaign-id", c._id);
  const records = $("memory-records");
  const visible = done.slice(-10),
    keys = new Set(visible.map((e) => e._id));
  for (const el of [...records.children])
    if (!keys.has(el.dataset.id)) el.remove();
  if (!done.length && !records.querySelector(".memory-empty"))
    records.innerHTML =
      '<div class="memory-empty"><div class="empty-slots"><i class="empty-slot"></i><i class="empty-slot"></i><i class="empty-slot"></i></div><span>Ready to remember</span></div>';
  for (const e of visible) {
    let el = [...records.children].find((x) => x.dataset.id === e._id);
    if (!el) {
      el = document.createElement("button");
      el.dataset.id = e._id;
      el.innerHTML = "<strong></strong><small></small>";
      el.onclick = () => showExperiment(e._id);
      records.append(el);
      if (
        fresh.some(
          (ev) =>
            ev.payload?.experiment_id === e._id && ev.type === "job_committed",
        )
      )
        pulse(el, "arriving");
    }
    el.classList.add("memory-record");
    el.classList.toggle("ineligible", e.eligible === false);
    el.classList.toggle("best", c.incumbent?.experiment_id === e._id);
    el.querySelector("strong").textContent = fmt(
      e.result.val_balanced_accuracy,
    );
    el.querySelector("small").textContent =
      `${e.n_channels || CH[e.config?.channels]} CH${e.attempt > 1 ? ` · ↺${e.attempt}` : ""}`;
    el.setAttribute(
      "aria-label",
      `Inspect result ${fmt(e.result.val_balanced_accuracy)}, ${e.eligible === false ? "outside current limit" : "eligible"}`,
    );
  }
  text(
    "progress-count",
    `${done.length} / ${c.budget?.max_experiments ?? "—"}`,
  );
  const signature = JSON.stringify(
    done.map((e) => [e._id, e.eligible, e.result.val_balanced_accuracy]),
  );
  if (signature === renderMemory.chartSignature) return;
  renderMemory.chartSignature = signature;
  const chart = $("results-chart"),
    W = 820,
    H = 78,
    max = Math.max(c.budget?.max_experiments || 10, done.length);
  chart.innerHTML = "";
  chart.append(
    svgEl("line", {
      x1: 15,
      y1: 65,
      x2: 805,
      y2: 65,
      stroke: "#e0e0dc",
      "stroke-width": 1,
    }),
  );
  chart.append(
    svgEl("line", {
      x1: 15,
      y1: 36,
      x2: 805,
      y2: 36,
      stroke: "#e9e9e5",
      "stroke-width": 1,
      "stroke-dasharray": "3 5",
    }),
  );
  const base = svgEl("text", {
    x: 0,
    y: 39,
    fill: "#999",
    "font-size": 9,
    "font-family": "IBM Plex Mono",
  });
  base.textContent = ".5";
  chart.append(base);
  const pts = done.map((e, i) => ({
    x: 30 + (i * 755) / Math.max(max - 1, 1),
    y: 65 - Math.max(0, Math.min(1, e.result.val_balanced_accuracy)) * 58,
    e,
  }));
  if (pts.length > 1)
    chart.append(
      svgEl("polyline", {
        points: pts.map((p) => `${p.x},${p.y}`).join(" "),
        fill: "none",
        stroke: "#c3c3be",
        "stroke-width": 1.2,
      }),
    );
  for (const p of pts) {
    const dot = svgEl("circle", {
      cx: p.x,
      cy: p.y,
      r: 4,
      fill: p.e.eligible === false ? "#fff" : "#111",
      stroke: p.e.eligible === false ? "#aaa" : "#111",
      "stroke-width": 1.5,
    });
    const title = svgEl("title");
    title.textContent = `${fmt(p.e.result.val_balanced_accuracy)} · ${p.e.n_channels || CH[p.e.config.channels]} electrodes`;
    dot.append(title);
    chart.append(dot);
  }
  if (pts.length) {
    const p = pts.at(-1),
      label = svgEl("text", {
        x: Math.min(780, p.x + 10),
        y: p.y + 3,
        fill: "#333",
        "font-size": 11,
        "font-family": "IBM Plex Mono",
      });
    label.textContent = fmt(p.e.result.val_balanced_accuracy);
    chart.append(label);
  }
}
function render(snapshot) {
  if (!live.connected) return;
  const c = snapshot.campaign,
    exps = snapshot.experiments,
    worker = snapshot.worker;
  document.body.dataset.phase = live.phase;
  document.body.dataset.connected = "true";
  text(
    "connection",
    worker.data_mode === "snapshot" ? "Recorded data" : live.phase === "done" ? "Complete" : live.ownsWorker ? "Live" : "Connected",
  );
  text("state-label", worker.remote && !["done", "failed"].includes(live.phase)
    ? `Last recorded: ${statusText[live.phase] || c.state}`
    : statusText[live.phase] || "Ready");
  text(
    "worker-caption",
    worker.data_mode === "snapshot"
      ? `Atlas snapshot · ${new Date(worker.captured_at).toLocaleString()}`
      : worker.remote
      ? "Live Atlas data · controls run locally"
      : live.phase === "stopped"
      ? "Process interrupted"
      : live.ownsWorker
        ? `Worker ${worker.pid} · ${c.state.toLowerCase()}`
        : live.phase === "done"
          ? "Process complete"
          : "Process not running",
  );
  renderPacket(live.currentPacket);
  renderMemory(
    c,
    exps,
    snapshot.events.filter((e) => live.freshIds?.includes(e._id)),
  );
  const lim = c.constraints.max_channels;
  text("electrode-count", lim);
  $("electrode-grid").setAttribute(
    "aria-label",
    `${lim} electrodes allowed; count diagram, not anatomical placement`,
  );
  [...$("electrode-grid").children].forEach((el, i) =>
    el.classList.toggle("off", i >= lim),
  );
  const running = c.running?.[0],
    latest = exps.at(-1);
  text(
    "experiment-caption",
    live.phase === "experiment"
      ? "Measuring recorded EEG"
      : live.phase === "stopped"
        ? "Interrupted work will retry"
        : live.phase === "waiting"
          ? "Waiting for the lease"
          : "Numerical evaluation",
  );
  text(
    "attempt",
    running?.attempt
      ? `attempt ${running.attempt}`
      : latest?.attempt
        ? `attempt ${latest.attempt}${latest.status === "done" ? " · saved" : ""}`
        : "",
  );
  const lastProposal = [...snapshot.events]
    .reverse()
    .find((e) => e.type === "proposal");
  text(
    "decision-caption",
    live.phase === "decide"
      ? "Selecting from measured evidence"
      : lastProposal?.payload?.config
        ? `${METHOD[lastProposal.payload.config.method] || "Experiment"} · next configuration`
        : "A fresh start, every step",
  );
  $("btn-start").disabled =
    worker.read_only || busy || worker.running || ["DONE", "FAILED"].includes(c.state);
  $("btn-kill").disabled = worker.read_only || busy || !live.ownsWorker;
  $("btn-reset").disabled = worker.read_only || busy || !live.cid;
  document.querySelectorAll("#limit-seg button").forEach((b) => {
    b.setAttribute("aria-pressed", String(Number(b.dataset.v) === lim));
    b.disabled = worker.read_only || busy;
  });
  document.querySelectorAll(".run-controls button, #limit-seg button").forEach((b) => {
    b.title = worker.read_only ? "Read-only dashboard. Run operator controls locally." : "";
  });
  setFocus();
  animateEvent(live.event);
  // Update a live inspector only when its substantive data change, preserving scroll position.
  if (
    drawerType === "packet" &&
    !drawerPacket &&
    $("inspector").open &&
    render.packetId !== live.currentPacket?.packet_id
  ) {
    render.packetId = live.currentPacket?.packet_id;
    showPacket(live.currentPacket, false);
  }
  if (
    drawerType === "history" &&
    $("inspector").open &&
    render.historyEvent !== (snapshot.events.at(-1)?._id || "empty")
  ) {
    const scroll = $("inspector").scrollTop;
    showHistory();
    $("inspector").scrollTop = scroll;
  }
}
async function poll() {
  if (inFlight) return;
  inFlight = true;
  const g = generation,
    cid = live.cid;
  controller = new AbortController();
  const timeout = setTimeout(() => controller?.abort(), 10000);
  const t = performance.now();
  try {
    if (!cid) {
      await loadCampaigns();
      return;
    }
    const opts = { signal: controller.signal };
    const [campaign, experiments, events, packet, worker] = await Promise.all([
      api(`/api/campaigns/${cid}`, opts),
      api(`/api/campaigns/${cid}/experiments`, opts),
      api(`/api/campaigns/${cid}/events?limit=400`, opts),
      api(`/api/campaigns/${cid}/packets/latest`, opts).catch((e) => {
        if (e.status === 404) return null;
        throw e;
      }),
      api("/api/worker/status", opts),
    ]);
    if (g !== generation) return;
    data = { campaign, experiments, events, packet, worker };
    live = reconcile(live, data);
    render(data);
  } catch (e) {
    controller?.abort();
    if (g === generation) {
      live = { ...live, connected: false };
      document.body.dataset.connected = "false";
      text("connection", "Reconnecting");
      text("state-label", "Connection lost");
      $("travel-signals").replaceChildren();
      ["btn-start", "btn-kill", "btn-reset"].forEach(
        (id) => ($(id).disabled = true),
      );
      document
        .querySelectorAll("#limit-seg button")
        .forEach((b) => (b.disabled = true));
    }
  } finally {
    clearTimeout(timeout);
    inFlight = false;
    clearTimeout(pollTimer);
    const interval = data?.worker.data_mode === "snapshot" ? 60000 : data?.worker.read_only ? 3000 : 500;
    pollTimer = setTimeout(poll, Math.max(50, interval - (performance.now() - t)));
  }
}
$("campaign-select").addEventListener("change", (e) => {
  generation++;
  controller?.abort();
  live = newState(e.target.value);
  data = null;
  lastSignature = "";
  animatedId = null;
  renderMemory.chartSignature = "";
  $("memory-records").replaceChildren();
  $("travel-signals").replaceChildren();
  $("inspector").close();
  const url = new URL(location);
  url.searchParams.set("campaign", live.cid);
  history.replaceState({}, "", url);
  if (!inFlight) {
    clearTimeout(pollTimer);
    poll();
  }
});
async function control(action) {
  if (busy || !data || !live.connected || data.worker.read_only) return;
  busy = true;
  render(data);
  try {
    await action();
  } catch (e) {
    toast(e.message);
  } finally {
    busy = false;
    if (data) render(data);
    if (!inFlight) {
      clearTimeout(pollTimer);
      poll();
    }
  }
}
$("btn-start").onclick = () =>
  control(() => post("/api/worker/start", { campaign_id: live.cid }));
$("btn-kill").onclick = () => control(() => post("/api/worker/kill"));
$("btn-reset").onclick = () =>
  control(() => post(`/api/campaigns/${live.cid}/context-reset`));
for (const b of document.querySelectorAll("#limit-seg button"))
  b.onclick = () => {
    if (Number(b.dataset.v) === data?.campaign.constraints.max_channels) return;
    control(() =>
      post(`/api/campaigns/${live.cid}/constraint`, {
        max_channels: Number(b.dataset.v),
        reason: "Electrode budget changed from the research dashboard",
      }),
    );
  };
$("btn-follow").onclick = () => {
  follow = !follow;
  $("btn-follow").setAttribute("aria-pressed", String(follow));
  $("btn-follow").innerHTML = follow
    ? "Follow activity <span>↗</span>"
    : "Overview <span>↗</span>";
  setFocus();
};
reduced.addEventListener("change", () => {
  if (reduced.matches) $("travel-signals").replaceChildren();
  setFocus();
});
function openInspector(kicker, title, body, type) {
  text("inspector-kicker", kicker);
  text("inspector-title", title);
  $("inspector-body").innerHTML = body;
  drawerType = type;
  if (!$("inspector").open) $("inspector").showModal();
}
$("close-inspector").onclick = () => $("inspector").close();
$("inspector").addEventListener("click", (e) => {
  if (
    e.target === $("inspector") &&
    e.clientX < $("inspector").getBoundingClientRect().left
  )
    $("inspector").close();
});
function intervalText(u) {
  return u?.available && u.interval ? `${fmt(u.interval[0])} to ${fmt(u.interval[1])}` : "Unavailable";
}
function hypothesisView(h) {
  if (!h) return "";
  return `<section class="inspector-section"><h3>Research hypothesis</h3><p>${esc(h.claim || h.kind)}</p><p><strong>${esc(h.status || "pending")}</strong></p>${h.reference_experiment_id ? `<p>Reference: <code>${esc(h.reference_experiment_id)}</code></p>` : ""}${h.comparison ? `<p>Measured difference: ${fmt(h.comparison.estimate)}<br>95% paired subject interval: ${intervalText(h.comparison)}</p>` : ""}${h.reason ? `<p>${esc(h.reason)}</p>` : ""}<p>Exploratory validation evidence for this configuration comparison.</p></section>`;
}
function researchView(p) {
  if (!p?.research) return "";
  return `<section class="inspector-section"><h3>Uncertainty-aware experiment design</h3><p>${esc(p.policy)} · ${esc(p.research.phase)}</p>${p.research.fallback_reason ? `<p>${esc(p.research.fallback_reason)}</p>` : ""}<p>Predictions are model estimates. Measured results appear above.</p>${p.research.candidates.map((c, i) => `<div class="research-candidate"><h4>${i + 1}. ${esc(c.label)}</h4><p>${esc(c.selection_reason.replaceAll("_", " "))}</p><div class="source-row"><span>Predicted accuracy</span><strong>${fmt(c.predicted_accuracy)}</strong></div><div class="source-row"><span>Predictive standard deviation</span><strong>${fmt(c.predictive_std)}</strong></div><div class="source-row"><span>Expected improvement</span><strong>${fmt(c.expected_improvement)}</strong></div><code>${esc(c.candidate_id)}</code></div>`).join("")}</section>${(p.hypotheses || []).map(hypothesisView).join("")}`;
}
function showPacket(packet, manual = true) {
  if (manual) drawerPacket = null;
  const p = packet,
    exact = numericalEvidence(p);
  let body = p
    ? `<div class="inspector-stats"><div><strong>${num(p.token_estimate)}</strong><span>tokens / ${num(p.budget_tokens)} budget</span></div><div><strong>${p.goal?.goal_version ?? data.campaign.goal_version}</strong><span>goal version</span></div></div><section class="inspector-section"><h3>Measured results · exact reads</h3>${exact.length ? exact.map((e) => `<div class="source-row"><span>${esc(e.label || e.experiment_id?.split(":").at(-1).slice(0, 10))}</span><strong>${fmt(e.val_balanced_accuracy ?? e.result?.val_balanced_accuracy)}</strong></div>`).join("") : "<p>No prior numerical evidence.</p>"}</section>${researchView(p)}<section class="inspector-section"><h3>Research notes · vector search</h3>${(p.retrieved || []).map((n) => `<p>${esc(n.text)}</p><code>${esc(n.memory_id)}</code>`).join("") || "<p>No notes retrieved.</p>"}</section><section class="inspector-section"><code>${esc(p.packet_id || p._id)}</code></section>`
    : '<section class="inspector-section"><p>A fresh evidence packet will appear when the next decision begins.</p></section>';
  openInspector("WORKING CONTEXT", "What the agent sees", body, "packet");
}
function showDecision() {
  const p = live.currentPacket;
  const result = p?.planner_result;
  openInspector(
    "DECISION",
    "The next experiment",
    `<section class="inspector-section"><h3>${esc(result?.model || "Planner")}</h3><p>${esc(result?.rationale || "Waiting for a decision.")}</p>${result?.fallback_used ? "<p>Deterministic fallback used for this decision.</p>" : ""}</section><section class="inspector-section"><h3>Cited evidence</h3>${(result?.evidence_ids || []).map((id) => `<p><code>${esc(id)}</code></p>`).join("") || "<p>No citations yet.</p>"}</section>`,
    "decision",
  );
}
function showExperiment(id) {
  const e = id
    ? data?.experiments.find((e) => e._id === id)
    : data?.experiments.find((e) => e.status === "running") ||
      data?.experiments.at(-1);
  if (!e) {
    openInspector(
      "NUMERICAL EVALUATION",
      "An experiment is next",
      '<section class="inspector-section"><p>The planner selects a configuration. Numerical code runs it against recorded EEG and commits the measured result.</p></section>',
      "experiment",
    );
    return;
  }
  const cfg = e.config || {};
  const reference = data?.experiments.find((row) => row._id === e.hypothesis?.reference_experiment_id);
  const predicted = e.hypothesis?.predicted_improvement != null && reference?.result?.val_balanced_accuracy != null
    ? reference.result.val_balanced_accuracy + e.hypothesis.predicted_improvement
    : null;
  const predictionView = predicted == null ? "" : `<section class="inspector-section"><h3>Prediction and observation</h3><div class="source-row"><span>Predicted before execution</span><strong>${fmt(predicted)}</strong></div><div class="source-row"><span>Measured validation accuracy</span><strong>${fmt(e.result?.val_balanced_accuracy)}</strong></div><p>The forecast is reconstructed from the registered predicted improvement and its measured reference.</p></section>`;
  openInspector(
    "MEASURED BY CODE",
    METHOD[cfg.method] || "Experiment",
    `<div class="inspector-stats"><div><strong>${fmt(e.result?.val_balanced_accuracy)}</strong><span>validation balanced accuracy</span></div><div><strong>${e.n_channels || CH[cfg.channels]}</strong><span>electrodes</span></div></div><section class="inspector-section">${Object.entries(
      {
        status: e.status,
        attempt: e.attempt,
        eligibility:
          e.eligible === false
            ? "outside current limit"
            : "within current limit",
        band: cfg.band,
        window: cfg.window,
      },
    )
      .map(
        ([k, v]) =>
          `<div class="source-row"><span>${esc(k)}</span><strong>${esc(v ?? "—")}</strong></div>`,
      )
      .join(
        "",
      )}</section>${predictionView}${e.result?.uncertainty ? `<section class="inspector-section"><h3>Measured uncertainty</h3><p>95% subject interval: ${intervalText(e.result.uncertainty)}</p><p>${num(e.result.uncertainty.n_subjects)} subjects · 2,000 cluster resamples</p><p>Exploratory adaptive validation. This interval does not establish population performance.</p></section>` : ""}${hypothesisView(e.hypothesis)}<section class="inspector-section"><code>${esc(e._id)}</code></section>`,
    "experiment",
  );
}
function labelEvent(e) {
  const p = e.payload || {};
  return (
    {
      worker_start: p.resumed ? "Worker resumed from Atlas" : "Worker started",
      worker_killed: "Worker stopped · SIGKILL",
      fault_injection: "Worker interrupted · SIGKILL",
      context_reset: "Working context cleared",
      goal_changed: `Electrode limit ${p.old_constraints?.max_channels} → ${p.new_constraints?.max_channels}`,
      packet_built: `Evidence packet · ${num(p.token_estimate)} tokens`,
      proposal: "Next experiment proposed",
      job_claimed: `Experiment claimed · attempt ${p.attempt}`,
      job_committed: "Measured result committed",
      job_failed: "Experiment failed",
      memory_added: "Memory stored",
      lease_expired: "Expired attempt reclaimed",
      finalized: "Sealed test scored",
    }[e.type] || e.type
  );
}
function showHistory() {
  render.historyEvent = data ? data.events.at(-1)?._id || "empty" : null;
  const events = (data?.events || [])
    .filter((e) => relevant.includes(e.type))
    .slice(-55)
    .reverse();
  openInspector(
    "CAMPAIGN HISTORY",
    "Every step, recorded",
    `<div class="inspector-log">${events.map((e) => `<button data-event="${esc(e._id)}">${esc(labelEvent(e))}<span>↗</span><small>${esc(new Date(e.ts).toLocaleTimeString())}</small></button>`).join("") || `<p>${data ? "No activity yet." : "Loading campaign history…"}</p>`}</div>`,
    "history",
  );
  $("inspector-body")
    .querySelectorAll("[data-event]")
    .forEach(
      (b) =>
        (b.onclick = async () => {
          const e = events.find((x) => x._id === b.dataset.event);
          if (e.payload?.packet_id) {
            try {
              drawerPacket = e.payload.packet_id;
              const cid = live.cid,
                p = await api(
                  `/api/campaigns/${cid}/packets/${encodeURIComponent(drawerPacket)}`,
                );
              if (cid !== live.cid) return;
              showPacket(p, false);
            } catch {
              toast("This packet is unavailable.");
            }
          } else if (e.payload?.experiment_id)
            showExperiment(e.payload.experiment_id);
          else
            openInspector(
              "RECORDED EVENT",
              labelEvent(e),
              `<section class="inspector-section">${Object.entries(
                e.payload || {},
              )
                .filter(([k]) => !k.includes("token"))
                .map(
                  ([k, v]) =>
                    `<p><strong>${esc(k.replaceAll("_", " "))}</strong><br>${esc(typeof v === "object" ? JSON.stringify(v) : v)}</p>`,
                )
                .join("")}</section>`,
              "event",
            );
        }),
    );
}
$("node-context").onclick = () => showPacket(live.currentPacket);
$("node-decide").onclick = showDecision;
$("node-experiment").onclick = () => showExperiment();
$("btn-inspect").onclick = () => showPacket(live.currentPacket);
$("btn-history").onclick = showHistory;
async function showProof() {
  try {
    const p = await api("/api/proof");
    const check = (title, key) => {
      const c = p.checks.by_check[key] || {};
      return `<section class="proof-block"><h2>${title}</h2><div class="proof-value">${c.passed ?? "—"}<span> / ${c.total ?? "—"}</span></div><div class="check-matrix">${Array.from({ length: c.total || 0 }, (_, i) => `<i>${i < c.passed ? "✓" : "×"}</i>`).join("")}</div><p>Separate verification campaign<br>${esc(c.campaign_id || "Unavailable")}</p></section>`;
    };
    $("proof-content").innerHTML =
      `<div class="proof-layout">${check("Survives a stopped worker", "recovery")}${check("Adapts to a changed goal", "constraint")}<section class="proof-block"><h2>Memory grows. Context stays bounded.</h2><div class="proof-value" style="font-size:48px">${num(p.memory.notes)}</div><div class="stress-diagram"><div class="stress-cloud">${"<i></i>".repeat(100)}</div><span>→</span><div class="stress-packet">${num(p.memory.packet_tokens)}</div></div><p>Notes including synthetic distractors → packet tokens. One measured stress sample; diagram groups notes for readability.</p></section></div>`;
  } catch {
    $("proof-content").textContent = "Verification results are unavailable.";
  }
}
const sources = {
  commit_result: ["harness/store.py", "commit_result"],
  rehydrate: ["harness/worker.py", "rehydrate"],
  build_packet: ["harness/context.py", "build_packet"],
};
let sourceRequest = 0;
async function showSource(key) {
  const request = ++sourceRequest;
  const [file, fn] = sources[key];
  document
    .querySelectorAll("[data-source]")
    .forEach((b) => b.classList.toggle("on", b.dataset.source === key));
  try {
    const s = await api(
      `/api/source?file=${encodeURIComponent(file)}&fn=${fn}`,
    );
    if (request !== sourceRequest) return;
    text("source-path", `${s.file} / ${s.fn}`);
    $("source-code").innerHTML = s.code
      .split("\n")
      .map(
        (l, i) =>
          `<span class="code-line"><span class="code-num">${s.start + i}</span>${esc(l)}</span>`,
      )
      .join("");
  } catch {
    text("source-code", "Source unavailable.");
  }
}
function showView(v) {
  view = v;
  for (const m of ["live", "results", "code"]) $(`view-${m}`).hidden = m !== v;
  document.querySelectorAll("[data-view]").forEach((b) => {
    if (b.dataset.view === v) b.setAttribute("aria-current", "page");
    else b.removeAttribute("aria-current");
  });
  if (v === "results") showProof();
  if (v === "code") showSource("commit_result");
}
document
  .querySelectorAll("[data-view]")
  .forEach((b) => (b.onclick = () => showView(b.dataset.view)));
document
  .querySelectorAll("[data-source]")
  .forEach((b) => (b.onclick = () => showSource(b.dataset.source)));
async function loadEeg() {
  try {
    const p = await api("/api/eeg/preview");
    const vals = Object.values(p.trace.channels)[0];
    const max = Math.max(...vals.map(Math.abs), 1);
    const line = vals.filter((_, i) => i % 3 === 0);
    $("eeg-trace")
      .querySelector("path")
      .setAttribute(
        "d",
        line
          .map(
            (v, i) =>
              `${i ? "L" : "M"}${(i * 130) / (line.length - 1)},${19 - (v / max) * 15}`,
          )
          .join(" "),
      );
  } catch {
    $("eeg-trace").setAttribute(
      "aria-label",
      "Recorded EEG preview unavailable",
    );
  }
}
await loadCampaigns().catch(() => text("connection", "Reconnecting"));
loadEeg();
if (["results", "code"].includes(params.get("view")))
  showView(params.get("view"));
poll();
