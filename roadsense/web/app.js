// RoadSense officer page: plan, map, triage queue, streetlights. Talks only to the local API.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (x, d = 3) => (x === null || x === undefined ? "n/a" : Number(x).toFixed(d));
const BAND_COLOR = { critical: "#c62828", high: "#ef6c00", prevention: "#f9a825", monitor: "#7cb342" };
const state = { ward: "", scenario: "", meta: null, map: null, lastFms: null };

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}
const post = (path, body) => api(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) });
const qs = (o) => new URLSearchParams(Object.entries(o).filter(([, v]) => v)).toString();
const wx = (s) => String(s || "").split(",").map((p) => p.split(":")[1]).filter(Boolean)
  .map((v, i) => (i === 0 ? "this week " : `wk ${i} `) + v.replace("climatology_10y", "climatology").replace("observed", "observed")).join(", ");
const gbp = (x) => "£" + Number(x).toFixed(2);
const badge = (t, cls = "") => `<span class="badge ${cls}">${t}</span>`;

async function loadMeta() {
  const m = await api("/meta?" + qs({ forecast_as_of: new URLSearchParams(location.search).get("forecast_as_of") }));
  state.meta = m;
  const sel = $("#ward");
  if (sel.options.length === 1) m.wards.forEach((w) => sel.add(new Option(w, w)));
  $("#badges").innerHTML = badge("SYNTHETIC", "") + (m.badges.mock_inputs ? badge("MOCK INPUTS", "mock") : "")
    + (m.freshness.stale ? badge("STALE", "stale") : "") + (m.freshness.provisional ? badge("PROVISIONAL", "prov") : "")
    + (m.gemini ? "" : ` <span class="muted small">Gemini off: keyword triage</span>`);
  const b = $("#stale");
  b.textContent = m.freshness.message + (m.badges.mock_inputs ? " " + m.badges.note : "");
  b.classList.toggle("hidden", !m.freshness.provisional && !m.badges.mock_inputs);
  $("#official-link").href = m.official_report_url;
}

async function loadPlan() {
  const p = await api("/plan/prevention?" + qs({ ward: state.ward, scenario: state.scenario,
    forecast_as_of: new URLSearchParams(location.search).get("forecast_as_of") }));
  $("#plan-head").innerHTML = `${p.count} segments to treat this week${state.ward ? " in " + esc(state.ward) : ""}, as of ${esc(p.as_of)}.`
    + (p.provisional ? " " + badge("PROVISIONAL", "prov") : "")
    + (p.scenario ? ` What-if <b>${esc(p.scenario)}</b> (${esc(p.scenario_method)}).` : "")
    + ` Ranked by reactive repair cost avoided per £ of treatment (planned ${gbp(p.costs.planned_repair)} vs reactive ${gbp(p.costs.reactive_repair)}, ${esc(p.costs.source)}).`;
  $("#plan-rows").innerHTML = p.rows.map((r) => `<tr data-id="${esc(r.segment_id)}">
      <td>${r.rank}</td>
      <td><b>${esc(r.name)}</b> <span class="muted small">${esc(r.highway)} · ${esc(r.ward)}</span>
        <div class="reasons">${esc(r.reasons)}</div>
        <div class="reasons">${esc(r.traffic_note)} · weather: ${esc(wx(r.weather_source))}${r.labels_synthetic ? " " + badge("SYNTHETIC") : ""}</div></td>
      <td><span class="u ${r.band}">${fmt(r.urgency, 0)}</span><div class="small muted">P30 ${fmt(r.p30_w0)} → ${fmt(r.p30_peak)}</div></td>
      <td>${esc(r.treatment_label)}<div class="small muted">£${fmt(r.treatment_cost_gbp, 0)}</div></td>
      <td>${fmt(r.avoided_per_gbp, 2)}</td></tr>`).join("") || `<tr><td colspan="5" class="muted">No segments in the prevention window are forecast to rise.</td></tr>`;
  document.querySelectorAll("#plan-rows tr[data-id]").forEach((tr) => tr.onclick = () => showSegment(tr.dataset.id, true));
}

async function loadMap() {
  const gj = await api("/segments?" + qs({ format: "geojson", ward: state.ward, scenario: state.scenario }));
  const src = state.map.getSource("segments");
  if (src) src.setData(gj); else {
    state.map.addSource("segments", { type: "geojson", data: gj });
    state.map.addLayer({ id: "segments", type: "line", source: "segments", paint: {
      "line-width": ["interpolate", ["linear"], ["zoom"], 11, 1.5, 16, 6],
      "line-color": ["case", ["==", ["get", "status"], "National Highways road, not scored"], "#9e9e9e",
        ["match", ["get", "band"], "critical", BAND_COLOR.critical, "high", BAND_COLOR.high, "prevention", BAND_COLOR.prevention, BAND_COLOR.monitor]],
      "line-opacity": ["case", ["==", ["get", "status"], "National Highways road, not scored"], 0.5, 0.9] } });
    state.map.on("click", "segments", (e) => { e.preventDefault(); showSegment(e.features[0].properties.segment_id); });
    state.map.on("mouseenter", "segments", () => state.map.getCanvas().style.cursor = "pointer");
    state.map.on("mouseleave", "segments", () => state.map.getCanvas().style.cursor = "");
    state.map.on("click", (e) => { if (!e.defaultPrevented) locate(e.lngLat.lat, e.lngLat.lng); });
    const b = new maplibregl.LngLatBounds();
    gj.features.forEach((f) => f.geometry.coordinates.forEach((c) => b.extend(c)));
    if (!b.isEmpty()) state.map.fitBounds(b, { padding: 20, duration: 0 });
  }
  const open = await api("/reports/open");
  const fc = { type: "FeatureCollection", features: open.reports.map((r) => ({ type: "Feature",
    properties: { title: r.title, date: r.reported_at, id: r.id }, geometry: { type: "Point", coordinates: [r.lon, r.lat] } })) };
  if (state.map.getSource("open")) state.map.getSource("open").setData(fc); else {
    state.map.addSource("open", { type: "geojson", data: fc });
    state.map.addLayer({ id: "open", type: "circle", source: "open", paint: { "circle-radius": 5, "circle-color": "#000",
      "circle-stroke-color": "#fff", "circle-stroke-width": 2 } });
    state.map.on("click", "open", (e) => { e.preventDefault(); const p = e.features[0].properties;
      new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<b>Open FixMyStreet report</b><br>${esc(p.title)}<br>Reported ${esc(p.date)} · urgency 100`).addTo(state.map); });
  }
}

function detail(html) { const d = $("#detail"); d.innerHTML = `<button class="close" onclick="this.parentNode.classList.add('hidden')">×</button>` + html; d.classList.remove("hidden"); }

async function locate(lat, lon) {
  const r = await api(`/locate?lat=${lat}&lon=${lon}`);
  if (r.status === "out_of_coverage") return detail(`<h3>Outside coverage</h3><p>RoadSense covers Southampton City Council roads only (E06000045).</p>`);
  if (r.status === "national_highways") return detail(`<h3>${esc(r.name)}</h3><p><b>National Highways road, not scored.</b> Motorways (M271, M27) are not council roads.</p>`);
  if (!r.segment_id) return detail(`<h3>No council road here</h3><p>${esc(r.message)}</p>`);
  showSegment(r.segment_id);
}

async function showSegment(id, fly) {
  const s = await api(`/segments/${encodeURIComponent(id)}?` + qs({ scenario: state.scenario }));
  if (fly && state.map) state.map.flyTo({ center: [s.lon, s.lat], zoom: 16 });
  if (s.status !== "scored") return detail(`<h3>${esc(s.name)}</h3><p><b>${esc(s.status)}</b></p>`);
  const dd = s.data_dates;
  detail(`<h3>${esc(s.name)}</h3><div class="muted small">${esc(s.segment_id)} · ${esc(s.highway)} · ${esc(s.ward)}</div>
    <p><span class="u ${s.band}">${fmt(s.urgency, 0)}</span> ${esc(s.band)}${s.confirmed_open ? " · <b>confirmed open pothole</b>" : ""}</p>
    <div class="kv">
      <div>Wear</div><div>${fmt(s.wear_pct, 0)}% ${s.wear_synthetic ? badge("SYNTHETIC") : ""}</div>
      <div>Risk P7 / P30</div><div>${fmt(s.p7)} / ${fmt(s.p30)} ${badge("SYNTHETIC LABELS")}</div>
      <div>P30 next 4 wks</div><div>${[s.p30_w0, s.p30_w1, s.p30_w2, s.p30_w3].map((x) => fmt(x)).join(" → ")}</div>
      <div>Consequence</div><div>×${fmt(s.consequence, 2)} ${esc(s.consequence_text)}</div>
      <div>Load</div><div>${fmt(s.esal_day, 0)} ESAL/day · ${esc(s.traffic_note)}</div>
      <div>Treatment</div><div><b>${esc(s.treatment_label)}</b> £${fmt(s.treatment_cost_gbp, 0)}</div>
      <div>Why</div><div>${s.reasons.map(esc).join("<br>") || "n/a"}</div>
      <div>Data dates</div><div class="small">risk as of ${esc(dd.risk_as_of)}<br>${esc(dd.forecast.message)}<br>FixMyStreet retrieved ${esc((dd.fixmystreet_retrieved_at || "").slice(0, 10))}</div>
    </div>
    <div><b>Record crew outcome</b><br>
      <button onclick="outcome('${esc(s.segment_id)}','pothole')">Pothole</button>
      <button onclick="outcome('${esc(s.segment_id)}','cracking')">Cracking</button>
      <button onclick="outcome('${esc(s.segment_id)}','none')">Nothing found</button></div>
    ${s.outcomes.map((o) => `<div class="small muted">Outcome ${esc(o.outcome)} on ${esc(o.inspection_date)} (${esc(o.source)})</div>`).join("")}`);
}

window.outcome = async (sid, o) => {
  const r = await post("/outcomes", { segment_id: sid, outcome: o });
  await refresh();
  await showSegment(sid);
  $("#detail").insertAdjacentHTML("beforeend", `<p class="card">Re-scored: urgency ${fmt(r.before.urgency, 0)} (${esc(r.before.band)}) → <b>${fmt(r.after.urgency, 0)} (${esc(r.after.band)})</b>, treatment ${esc(r.after.treatment)}.</p>`);
};

async function loadFms() {
  const recent = await api("/reports/recent?n=40");
  $("#fms-pick").innerHTML = recent.map((r) => `<option value="${r.id}">${esc(r.reported_at)} · ${esc(r.title).slice(0, 60)}</option>`).join("");
}

async function loadQueue() {
  const q = await api("/triage/queue");
  $("#qcount").textContent = q.filter((x) => x.status === "pending_approval").length || "";
  $("#queue").innerHTML = q.slice().reverse().map((w) => `<div class="card ${w.status === "merged" ? "merged" : ""}">
    <div><span class="status">${esc(w.status.replace("_", " "))}</span> · <b>${esc(w.category)}</b> (${esc(w.method)}${w.tokens ? `, ${w.tokens.total_tokens} tokens` : ""})</div>
    <div>${esc(w.title)} <span class="muted small">reported ${esc(String(w.reported_at).slice(0, 10))} · ${esc(w.report_id)}</span></div>
    <div class="small">${w.segment_id ? `Segment <a href="#" onclick="showSegment('${esc(w.segment_id)}',true);return false">${esc(w.location.name)}</a> (${fmt(w.location.segment_distance_m, 0)} m)` : esc(w.location.message || "")}
      ${w.urgency !== undefined ? ` · urgency ${fmt(w.urgency, 0)} (risk model ${fmt(w.risk_urgency, 0)})` : ""}</div>
    ${w.merged_into ? `<div class="small">Merged into ${esc(w.merged_into)}: same defect within 15 m and 14 days</div>` : ""}
    ${(w.merged_reports || []).length ? `<div class="small">${w.merged_reports.length} duplicate report(s) merged in</div>` : ""}
    ${w.hazard ? `<div class="small"><b>Possible danger:</b> <a href="${esc(w.official_report_url)}" target="_blank" rel="noopener">council reporting page</a></div>` : ""}
    <details><summary class="small">Draft work order (JSON)</summary><pre>${esc(JSON.stringify({ report_id: w.report_id, category: w.category,
      segment_id: w.segment_id, lamp_id: w.lamp_id, urgency: w.urgency, summary: w.summary, recommended_action: w.recommended_action,
      duplicate_of: w.merged_into }, null, 1))}</pre></details>
    ${w.status === "pending_approval" ? `<button class="primary" onclick="approve('${esc(w.report_id)}')">Approve work order</button>
      <button onclick="reject('${esc(w.report_id)}')">Reject</button>` : ""}</div>`).join("") || `<p class="muted">No reports triaged yet.</p>`;
}

window.approve = async (id) => { const r = await post(`/workorders/${encodeURIComponent(id)}/approve`, { officer: "officer" });
  await refresh(); if (r.segment) showSegment(r.segment.segment_id, true); };
window.reject = async (id) => { await post(`/workorders/${encodeURIComponent(id)}/reject`); loadQueue(); };
window.showSegment = showSegment;

async function triage(fmsId) {
  const btns = document.querySelectorAll("#triage-form button"); btns.forEach((b) => b.disabled = true);
  try { await post("/reports", { fms_id: Number(fmsId) }); state.lastFms = fmsId; await loadQueue(); }
  catch (e) { alert(e.message); } finally { btns.forEach((b) => b.disabled = false); }
}

async function loadLights() {
  const l = await api("/lights?" + qs({ ward: state.ward, due: !$("#dark-only").checked, dark: $("#dark-only").checked, limit: 200 }));
  $("#lights-head").innerHTML = `${l.count_due_90d} lamps due for replacement within 90 days, ${l.count_currently_dark} currently dark, as of ${esc(l.as_of)} ${badge("SYNTHETIC")}. `
    + `Report a faulty light on the <a href="${esc(l.official_report_url)}" target="_blank" rel="noopener">council's streetlight page</a>.`;
  $("#light-rows").innerHTML = l.lamps.map((x) => `<tr data-lat="${x.lat}" data-lon="${x.lon}"><td>${esc(x.lamp_id)}<div class="small muted">${esc(x.unit_type)}</div></td>
    <td>${esc(x.name)}<div class="small muted">${esc(x.ward)}</div></td><td>${fmt(x.p_fail_90d)}</td>
    <td>${esc(x.predicted_replacement_date)}</td><td>${x.currently_dark ? "<b>dark</b> since " + esc(x.dark_since) : x.replacement_overdue ? "overdue" : ""}</td></tr>`).join("");
  document.querySelectorAll("#light-rows tr").forEach((tr) => tr.onclick = () => state.map.flyTo({ center: [+tr.dataset.lon, +tr.dataset.lat], zoom: 17 }));
}

async function loadSources() {
  const s = await api("/sources");
  $("#sources").innerHTML = "<b>Data sources:</b> " + s.map((x) => `<span>${esc(x.dataset)}: ${esc(x.label)}${x.synthetic ? " " + badge(x.kind === "mock" ? "MOCK" : "SYNTHETIC", x.kind === "mock" ? "mock" : "") : ""} <span title="${esc(x.licence)}">ⓘ</span></span>`).join("")
    + `<span>Map © OpenStreetMap contributors</span>`;
}

async function refresh() { await Promise.all([loadMeta(), loadPlan(), loadMap(), loadQueue()]); }

function initMap() {
  state.map = new maplibregl.Map({ container: "map", center: [-1.40, 50.91], zoom: 12, style: {
    version: 8, sources: { osm: { type: "raster", tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"], tileSize: 256,
      attribution: "© OpenStreetMap contributors" } }, layers: [{ id: "osm", type: "raster", source: "osm", paint: { "raster-saturation": -0.6 } }] } });
  return new Promise((res) => state.map.on("load", res));
}

document.querySelectorAll(".tabs button").forEach((b) => b.onclick = () => {
  document.querySelectorAll(".tabs button").forEach((x) => x.classList.toggle("active", x === b));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("hidden", t.id !== "tab-" + b.dataset.tab));
  if (b.dataset.tab === "lights") loadLights();
});
$("#ward").onchange = (e) => { state.ward = e.target.value; refresh(); if (!$("#tab-lights").classList.contains("hidden")) loadLights(); };
$("#scenario").onchange = async (e) => { state.scenario = e.target.value; $("#plan-head").textContent = "Re-scoring…"; await Promise.all([loadPlan(), loadMap()]); };
$("#dark-only").onchange = loadLights;
$("#triage-form").onsubmit = (e) => { e.preventDefault(); triage($("#fms-pick").value); };
$("#dup-btn").onclick = () => triage(state.lastFms || $("#fms-pick").value);

(async () => {
  await loadMeta();
  await initMap();
  await Promise.all([refresh(), loadFms(), loadSources()]);
})().catch((e) => { $("#stale").textContent = "Could not reach the RoadSense API: " + e.message; $("#stale").classList.remove("hidden"); });
