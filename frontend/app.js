const logEl = document.getElementById("log");
const profileEl = document.getElementById("profile");
const metersEl = document.getElementById("meters");
const recsEl = document.getElementById("recs");
const evidenceEl = document.getElementById("evidence");
const chainsEl = document.getElementById("chains");
const graphEl = document.getElementById("graph");
const sendBtn = document.getElementById("send");

let sessionId = localStorage.getItem("biointel.session") || "";

const EXAMPLES = {
  decline: "Biodiversity is declining on my land",
  brief: `Soil organic carbon: 0.3%
Rainfall: low
Crop: monoculture wheat
Region: semi-arid`,
  json: `{
  "soil_organic_carbon": 0.3,
  "rainfall": "low",
  "crop": "monoculture wheat",
  "region": "semi-arid"
}`,
  geo: "Peri-urban mixed farm with high pesticide use and almost no hedgerows. Native cover around 8%.",
};

document.querySelectorAll(".tabs button").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tabs button").forEach((b) => b.classList.remove("active"));
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(`tab-${btn.dataset.tab}`).classList.add("active");
  });
});

document.getElementById("examples").addEventListener("click", (event) => {
  const btn = event.target.closest("button");
  if (!btn) return;
  document.getElementById("message").value = EXAMPLES[btn.dataset.example];
  document.getElementById("message").focus();
  if (btn.dataset.example === "geo") {
    document.getElementById("lat").value = "-1.2921";
    document.getElementById("lon").value = "36.8219";
    document.querySelector(".geo").open = true;
  }
});

function md(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/_([^_]+)_/g, "<em>$1</em>")
    .replace(/\n/g, "<br>");
}

function addBubble(role, text) {
  const li = document.createElement("li");
  li.className = `bubble ${role}`;
  li.innerHTML = md(text);
  logEl.appendChild(li);
  logEl.scrollTop = logEl.scrollHeight;
}

function filledRows(profile) {
  const rows = [];
  const walk = (obj) => {
    Object.entries(obj || {}).forEach(([key, value]) => {
      if (value && typeof value === "object" && !Array.isArray(value)) {
        walk(value);
      } else if (Array.isArray(value) && value.length) {
        rows.push([key.replace(/_/g, " "), value.join("; ")]);
      } else if (value !== null && value !== undefined && value !== "") {
        rows.push([key.replace(/_/g, " "), String(value)]);
      }
    });
  };
  walk(profile);
  return rows;
}

function renderProfile(profile) {
  const rows = filledRows(profile);
  if (!rows.length) {
    profileEl.className = "empty";
    profileEl.textContent = "No site data yet. Three variables — soil, climate, land use — unlock recommendations.";
    return;
  }
  profileEl.className = "kv";
  profileEl.innerHTML = rows
    .map(([k, v]) => `<div><dt>${k}</dt><dd>${v}</dd></div>`)
    .join("");
}

function toggleEmpty(id, show) {
  const el = document.getElementById(id);
  if (el) el.style.display = show ? "block" : "none";
}

function renderDiagnosis(pack) {
  metersEl.innerHTML = "";
  recsEl.innerHTML = "";
  const has = pack && ((pack.metric_status || []).length || (pack.recommendations || []).length);
  toggleEmpty("diagnosis-empty", !has);
  if (!pack) return;
  (pack.metric_status || []).forEach((item) => {
    const row = document.createElement("div");
    row.className = "meter";
    row.innerHTML = `<div><strong>${item.metric}</strong><div class="hint">${item.value || ""}</div></div>
      <span class="pill ${item.severity}">${item.severity}</span>`;
    metersEl.appendChild(row);
  });
  (pack.recommendations || []).forEach((rec) => {
    const card = document.createElement("article");
    card.className = "rec-card";
    card.innerHTML = `<h3>${rec.title}</h3>
      <p>${rec.action}</p>
      <p style="margin-top:8px">${rec.time_horizon} · ${rec.confidence} confidence</p>`;
    recsEl.appendChild(card);
  });
}

function renderEvidence(pack) {
  evidenceEl.innerHTML = "";
  if (!pack) {
    toggleEmpty("evidence-empty", true);
    return;
  }
  const items = [...(pack.retrieved_evidence || [])];
  (pack.recommendations || []).forEach((rec) => items.push(...(rec.evidence || [])));
  const seen = new Set();
  items.forEach((ev) => {
    const key = ev.citation + ev.snippet;
    if (seen.has(key)) return;
    seen.add(key);
    const li = document.createElement("li");
    li.innerHTML = `<strong>${ev.source}</strong> ${ev.year || ""}<span>${ev.citation}</span>`;
    evidenceEl.appendChild(li);
  });
  toggleEmpty("evidence-empty", !evidenceEl.children.length);
}

function renderGraph(pack) {
  chainsEl.innerHTML = "";
  graphEl.innerHTML = "";
  const chains = pack?.causal_chains || [];
  toggleEmpty("graph-empty", !chains.length);
  graphEl.classList.toggle("has-nodes", chains.length > 0);
  chains.forEach((chain) => {
    const li = document.createElement("li");
    li.textContent = chain.path.join(" → ");
    chainsEl.appendChild(li);
  });
  const nodes = [];
  chains.forEach((chain) => chain.path.forEach((n) => { if (!nodes.includes(n)) nodes.push(n); }));
  nodes.forEach((name, i) => {
    const x = 70 + (i % 3) * 140;
    const y = 50 + Math.floor(i / 3) * 95;
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.setAttribute("cx", x);
    circle.setAttribute("cy", y);
    circle.setAttribute("r", 8);
    circle.setAttribute("fill", "#2f5d45");
    graphEl.appendChild(circle);
    const label = document.createElementNS("http://www.w3.org/2000/svg", "text");
    label.setAttribute("x", x);
    label.setAttribute("y", y + 28);
    label.setAttribute("text-anchor", "middle");
    label.setAttribute("fill", "#1c241f");
    label.setAttribute("font-size", "11");
    label.setAttribute("font-family", "DM Sans, sans-serif");
    label.textContent = name;
    graphEl.appendChild(label);
  });
}

async function loadHealth() {
  const res = await fetch("/api/health");
  const data = await res.json();
  const status = document.getElementById("status");
  if (status) status.textContent = `${data.corpus_docs} papers · ${data.interventions} interventions`;
}

async function send(message) {
  addBubble("user", message);
  sendBtn.disabled = true;
  const lat = document.getElementById("lat").value;
  const lon = document.getElementById("lon").value;
  const payload = { session_id: sessionId || null, message };
  if (lat && lon) payload.coordinates = [Number(lat), Number(lon)];
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    sessionId = data.session_id;
    localStorage.setItem("biointel.session", sessionId);
    addBubble("assistant", data.assistant_message);
    renderProfile(data.profile);
    renderDiagnosis(data.pack);
    renderEvidence(data.pack);
    renderGraph(data.pack);
  } catch (err) {
    addBubble("assistant", `Request failed: ${err}`);
  } finally {
    sendBtn.disabled = false;
  }
}

document.getElementById("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  const message = document.getElementById("message").value.trim();
  if (!message) return;
  document.getElementById("message").value = "";
  send(message);
});

document.getElementById("message").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    document.getElementById("composer").requestSubmit();
  }
});

addBubble(
  "assistant",
  "**Ask about a place, not a slogan.** I retrieve a scientific corpus and will wait for soil, climate, and land use before recommending anything."
);
loadHealth().catch(() => {});
