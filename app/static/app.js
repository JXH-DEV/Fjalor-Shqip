const form = document.querySelector("#search-form");
const input = document.querySelector("#q");
const suggestBox = document.querySelector("#suggest");
const statusEl = document.querySelector("#status");
const resultsEl = document.querySelector("#results");
const wotdEl = document.querySelector("#wotd");
const trendingEl = document.querySelector("#trending");

let suggestTimer = 0;

form.addEventListener("submit", (event) => {
  event.preventDefault();
  lookup(input.value.trim());
});

document.querySelectorAll(".chip").forEach((button) => {
  button.addEventListener("click", () => lookup(button.dataset.word));
});

input.addEventListener("input", () => {
  const value = input.value.trim();
  window.clearTimeout(suggestTimer);
  if (value.length < 2) {
    suggestBox.hidden = true;
    return;
  }
  suggestTimer = window.setTimeout(() => loadSuggestions(value), 220);
});

document.addEventListener("click", (event) => {
  if (!suggestBox.contains(event.target) && event.target !== input) {
    suggestBox.hidden = true;
  }
});

async function loadSuggestions(query) {
  try {
    const data = await getJSON(`/api/v1/suggest?q=${encodeURIComponent(query)}`);
    renderSuggestions(data.suggestions || []);
  } catch {
    suggestBox.hidden = true;
  }
}

function renderSuggestions(items) {
  if (!items.length) {
    suggestBox.hidden = true;
    return;
  }
  suggestBox.innerHTML = items
    .map((word) => `<li><button type="button" data-word="${escapeAttr(word)}">${escapeHtml(word)}</button></li>`)
    .join("");
  suggestBox.hidden = false;
  suggestBox.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => lookup(button.dataset.word));
  });
}

async function lookup(word) {
  if (!word) return;
  input.value = word;
  suggestBox.hidden = true;
  resultsEl.hidden = true;
  setStatus("Duke kërkuar…", "");
  try {
    const [data, quotes] = await Promise.all([
      getJSON(`/api/v1/lookup?q=${encodeURIComponent(word)}`),
      getJSON(`/api/v1/quotes?q=${encodeURIComponent(word)}`).catch(() => ({ quotes: [] })),
    ]);
    renderResults(data, quotes.quotes || []);
  } catch (error) {
    setStatus(error.message || "Kërkimi dështoi.", "error");
  }
}

function renderResults(data, quotes) {
  if (!data.found) {
    const extra = data.suggestions?.length
      ? ` Provo: ${data.suggestions.slice(0, 6).map((word) => `<button type="button" class="word-link" data-word="${escapeAttr(word)}">${escapeHtml(word)}</button>`).join(", ")}.`
      : "";
    setStatus(`Fjala «${escapeHtml(data.query)}» nuk u gjet.${extra}`, "empty");
    resultsEl.hidden = true;
    bindWordLinks(statusEl);
    return;
  }

  statusEl.className = "status";
  statusEl.innerHTML = `U gjet <strong>${escapeHtml(data.canonical || data.query)}</strong> në ${data.sources.filter((s) => s.found).length} burim(e).`;

  const merged = data.merged;
  const senses = (merged.senses || [])
    .map((sense) => {
      const labels = sense.labels?.length ? `<span class="labels">${escapeHtml(sense.labels.join(", "))}</span>` : "";
      const examples = sense.examples?.length ? `<span class="examples">${escapeHtml(sense.examples.join(" · "))}</span>` : "";
      return `<li>${labels}${escapeHtml(sense.gloss)}${examples}</li>`;
    })
    .join("");

    const pills = [
      ...(merged.pos || []).map((item) => `<span class="pill">${escapeHtml(item)}</span>`),
      ...(merged.part_of_speech || []).slice(0, 3).map((item) => `<span class="pill">${escapeHtml(item)}</span>`),
      ...(merged.synonyms || []).slice(0, 6).map((item) => `<span class="pill">sin. ${escapeHtml(item)}</span>`),
    ].join("");

  const translations = Object.entries(merged.translations || {})
    .map(([lang, words]) => `<p><strong>${escapeHtml(lang)}:</strong> ${escapeHtml(words.join(", "))}</p>`)
    .join("");

  const related = (merged.related || [])
    .slice(0, 10)
    .map((word) => `<button type="button" class="word-link" data-word="${escapeAttr(word)}">${escapeHtml(word)}</button>`)
    .join(" · ");

  const sourceCards = data.sources.map(renderSourceCard).join("");
  const quoteBlock = quotes.length
    ? `<div class="quotes">${quotes
        .slice(0, 2)
        .map((quote) => `<p>«${escapeHtml(quote.excerpt)}»${quote.author ? ` — ${escapeHtml(quote.author)}` : ""}${quote.title ? `, <em>${escapeHtml(quote.title)}</em>` : ""}</p>`)
        .join("")}<p class="fineprint">Citimet vijnë nga Fjalorthi.</p></div>`
    : "";

  resultsEl.innerHTML = `
    <article class="entry">
      <div class="headword">${escapeHtml(merged.headword)}</div>
      <div class="meta-row">${pills}</div>
      <ol class="senses">${senses}</ol>
      ${translations}
      ${related ? `<p><strong>Shih edhe:</strong> ${related}</p>` : ""}
      ${quoteBlock}
    </article>
    <h2>Sipas burimit</h2>
    <div class="source-grid">${sourceCards}</div>
  `;
  resultsEl.hidden = false;
  bindWordLinks(resultsEl);
}

function renderSourceCard(source) {
  if (source.error) {
    return `<article class="source-card"><h3>${escapeHtml(source.title)}</h3><p class="miss">${escapeHtml(source.error)}</p></article>`;
  }
  if (!source.found) {
    return `<article class="source-card"><h3>${escapeHtml(source.title)}</h3><p class="miss">Nuk u gjet në këtë burim.</p>${source.url ? `<p><a href="${escapeAttr(source.url)}" rel="noreferrer">Hape burimin</a></p>` : ""}</article>`;
  }
  const first = source.entries[0];
  const items = (first.senses || [])
    .slice(0, 3)
    .map((sense) => `<li>${escapeHtml(sense.gloss)}</li>`)
    .join("");
  return `<article class="source-card">
    <h3>${escapeHtml(source.title)}</h3>
    <p class="pos">${escapeHtml((first.part_of_speech || []).join(" · "))}</p>
    <ol>${items}</ol>
    <p><a href="${escapeAttr(source.url || source.homepage)}" rel="noreferrer">Burimi origjinal</a></p>
  </article>`;
}

async function loadSidebar() {
  try {
    const wotd = await getJSON("/api/v1/word-of-the-day");
    wotdEl.innerHTML = `<p><button type="button" class="word-link" data-word="${escapeAttr(wotd.word)}">${escapeHtml(wotd.word)}</button></p><p>${escapeHtml(wotd.definition || "")}</p>`;
    bindWordLinks(wotdEl);
  } catch {
    wotdEl.textContent = "Fjala e ditës nuk u ngarkua. Provo përsëri më vonë.";
  }

  try {
    const trending = await getJSON("/api/v1/trending");
    trendingEl.innerHTML = `<ul class="trend-list">${(trending.words || [])
      .map((item) => `<li><button type="button" class="word-link" data-word="${escapeAttr(item.word)}">${escapeHtml(item.word)}</button><span class="views">${item.views ? `${item.views} shikime` : ""}</span></li>`)
      .join("")}</ul>`;
    bindWordLinks(trendingEl);
  } catch {
    trendingEl.textContent = "Lista e fjalëve të kërkuara nuk u ngarkua.";
  }
}

function bindWordLinks(root) {
  root.querySelectorAll("[data-word]").forEach((node) => {
    node.addEventListener("click", () => lookup(node.dataset.word));
  });
}

function setStatus(html, kind) {
  statusEl.className = `status ${kind || ""}`.trim();
  statusEl.innerHTML = html;
}

async function getJSON(url) {
  const response = await fetch(url);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll("'", "&#39;");
}

loadSidebar();

const params = new URLSearchParams(window.location.search);
if (params.get("q")) {
  lookup(params.get("q"));
}
