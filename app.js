const DATA_URL = "data/vocab.csv";
const STORE_KEY = "hbs-vocab-progress-v1";
const DEFAULT_TODAY_PLAN = 40;
const MIN_TODAY_PLAN = 5;
const MAX_TODAY_PLAN = 300;
const KIND_ORDER = ["必考词", "基础词", "超纲词"];
const KIND_WEIGHTS = {
  "必考词": 0.6,
  "基础词": 0.3,
  "超纲词": 0.1,
};

const viewEl = document.querySelector("#view");
const tabs = [...document.querySelectorAll(".tab")];
const helpDialog = document.querySelector("#helpDialog");
const installHelp = document.querySelector("#installHelp");

const app = {
  payload: null,
  words: [],
  byId: new Map(),
  view: "today",
  activeWord: null,
  activeModule: null,
  todayQueue: [],
  todayIndex: 0,
  answerVisible: false,
  progress: loadProgress(),
};

function loadProgress() {
  try {
    return normalizeProgress(JSON.parse(localStorage.getItem(STORE_KEY)));
  } catch {
    return normalizeProgress(null);
  }
}

function normalizeProgress(value) {
  const progress = value && typeof value === "object" ? value : {};
  progress.reviews = progress.reviews && typeof progress.reviews === "object" ? progress.reviews : {};
  progress.completed = progress.completed || 0;
  progress.settings = progress.settings && typeof progress.settings === "object" ? progress.settings : {};
  progress.settings.todayPlan = clampPlan(progress.settings.todayPlan || DEFAULT_TODAY_PLAN);
  return progress;
}

function saveProgress() {
  localStorage.setItem(STORE_KEY, JSON.stringify(app.progress));
}

function clampPlan(value) {
  const number = Number.parseInt(value, 10);
  if (!Number.isFinite(number)) return DEFAULT_TODAY_PLAN;
  return Math.min(MAX_TODAY_PLAN, Math.max(MIN_TODAY_PLAN, number));
}

function todayPlan() {
  return clampPlan(app.progress.settings?.todayPlan || DEFAULT_TODAY_PLAN);
}

function setTodayPlan(value) {
  app.progress.settings.todayPlan = clampPlan(value);
  saveProgress();
  app.answerVisible = false;
  buildTodayQueue();
  renderToday();
}

function todayKey() {
  return new Date().toISOString().slice(0, 10);
}

function daysFromNow(days) {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function escapeHtml(value = "") {
  return String(value).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[ch]));
}

function getReview(id) {
  return app.progress.reviews[id] || {};
}

function reviewWord(id, score) {
  const old = getReview(id);
  const streak = score === 2 ? (old.streak || 0) + 1 : 0;
  const delay = score === 2 ? Math.min(30, [2, 4, 7, 14, 30][Math.min(streak, 4)]) : score === 1 ? 1 : 0;
  app.progress.reviews[id] = {
    seen: (old.seen || 0) + 1,
    streak,
    score,
    wrong: score < 2,
    last: todayKey(),
    due: daysFromNow(delay),
  };
  app.progress.completed = (app.progress.completed || 0) + 1;
  saveProgress();
  app.todayIndex += 1;
  app.answerVisible = false;
  renderToday();
}

function shuffle(items) {
  const result = [...items];
  for (let i = result.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

function pickRandom(items) {
  const index = Math.floor(Math.random() * items.length);
  const [item] = items.splice(index, 1);
  return item;
}

function availableTodayWords() {
  const now = todayKey();
  const groups = Object.fromEntries(KIND_ORDER.map((kind) => [kind, { due: [], fresh: [] }]));
  for (const word of app.words) {
    const review = getReview(word.id);
    const bucket = groups[word.kind] || groups["超纲词"];
    if (review.seen && review.due <= now) {
      bucket.due.push(word);
    } else if (!review.seen) {
      bucket.fresh.push(word);
    }
  }
  for (const bucket of Object.values(groups)) {
    bucket.due = shuffle(bucket.due);
    bucket.fresh = shuffle(bucket.fresh);
  }
  return groups;
}

function groupCount(bucket) {
  return bucket.due.length + bucket.fresh.length;
}

function pullFromBucket(bucket) {
  if (bucket.due.length) return pickRandom(bucket.due);
  return pickRandom(bucket.fresh);
}

function adjustedKindWeights(groups, slotsLeft) {
  const weights = {};
  let carry = 0;
  for (const kind of KIND_ORDER) {
    const available = groupCount(groups[kind]);
    const target = (KIND_WEIGHTS[kind] || 0) + carry;
    const cap = slotsLeft > 0 ? available / slotsLeft : 0;
    const assigned = Math.max(0, Math.min(target, cap));
    weights[kind] = assigned;
    carry = Math.max(0, target - assigned);
  }

  const total = Object.values(weights).reduce((sum, value) => sum + value, 0);
  if (total > 0) return weights;

  for (const kind of KIND_ORDER) {
    weights[kind] = groupCount(groups[kind]) > 0 ? 1 : 0;
  }
  return weights;
}

function chooseKind(groups, slotsLeft) {
  const weights = adjustedKindWeights(groups, slotsLeft);
  const availableKinds = KIND_ORDER.filter((kind) => groupCount(groups[kind]) > 0 && weights[kind] > 0);
  const total = availableKinds.reduce((sum, kind) => sum + weights[kind], 0);
  let point = Math.random() * total;
  for (const kind of availableKinds) {
    point -= weights[kind];
    if (point <= 0) return kind;
  }
  return availableKinds[availableKinds.length - 1];
}

function buildTodayQueue() {
  const groups = availableTodayWords();
  const queue = [];
  const plan = todayPlan();
  while (queue.length < plan && KIND_ORDER.some((kind) => groupCount(groups[kind]) > 0)) {
    const kind = chooseKind(groups, plan - queue.length);
    if (!kind) break;
    queue.push(pullFromBucket(groups[kind]));
  }
  app.todayQueue = queue;
  app.todayIndex = 0;
}

function stats() {
  const reviews = Object.values(app.progress.reviews);
  return {
    learned: reviews.filter((item) => item.seen).length,
    wrong: reviews.filter((item) => item.wrong).length,
    due: app.todayQueue.length,
    plan: todayPlan(),
  };
}

function field(label, value, className = "") {
  if (!value) return "";
  return `
    <div class="field">
      <div class="label">${label}</div>
      <div class="value ${className}">${escapeHtml(value)}</div>
    </div>
  `;
}

function posDefsHtml(word) {
  const defs = Array.isArray(word.pos_defs) ? word.pos_defs : [];
  if (!defs.length) {
    return field("释义", word.definition || "待生成：词性及中文释义");
  }
  return `
    <div class="field">
      <div class="label">释义</div>
      <div class="value">
        <ol class="def-list">
          ${defs.map((item) => `
            <li>
              <strong>${escapeHtml(item.pos || "")}</strong>
              <span>${escapeHtml(Array.isArray(item.defs) ? item.defs.join("；") : item.definition || "")}</span>
            </li>
          `).join("")}
        </ol>
      </div>
    </div>
  `;
}

function examplesHtml(word) {
  const examples = Array.isArray(word.examples) ? word.examples : [];
  if (examples.length) {
    return `
      <div class="field">
        <div class="label">例句</div>
        <div class="value">
          <ol class="example-list">
            ${examples.map((item) => `
              <li>
                <p class="example">${escapeHtml(item.en || "")}</p>
                <p>${escapeHtml(item.zh || "")}</p>
              </li>
            `).join("")}
          </ol>
        </div>
      </div>
    `;
  }
  return `
    ${field("例句", word.example, "example")}
    ${field("译文", word.translation)}
  `;
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    const next = text[index + 1];
    if (inQuotes) {
      if (char === '"' && next === '"') {
        field += '"';
        index += 1;
      } else if (char === '"') {
        inQuotes = false;
      } else {
        field += char;
      }
      continue;
    }
    if (char === '"') {
      inQuotes = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function csvToObjects(text) {
  const rows = parseCsv(text);
  const headers = (rows.shift() || []).map((header) => String(header).replace(/^\uFEFF/, "").trim());
  return rows
    .filter((row) => row.some((field) => String(field).trim()))
    .map((row) => Object.fromEntries(headers.map((header, index) => [header, row[index] || ""])));
}

function kindOf(source) {
  if (source.startsWith("必考词")) return "必考词";
  if (source.startsWith("基础词")) return "基础词";
  return "超纲词";
}

function moduleSortKey(name) {
  const match = name.match(/^(必考词|基础词) Unit (\d+)$/);
  if (!match) return [KIND_ORDER.indexOf(name) >= 0 ? KIND_ORDER.indexOf(name) : 99, 999];
  return [KIND_ORDER.indexOf(match[1]), Number(match[2])];
}

function slugSource(source) {
  const match = source.match(/^(必考词|基础词) Unit (\d+)$/);
  if (!match) return "chaogangci";
  return `${match[1] === "必考词" ? "bikaoci" : "jichuci"}_unit_${String(Number(match[2])).padStart(2, "0")}`;
}

function parsePosDefs(meaning) {
  const posPattern = /^(vt|vi|v|n|adj|adv|prep|pron|conj|num)\.\s*(.*)$/;
  const chunks = String(meaning || "")
    .split(/\n/)
    .flatMap((line) => line.split(/[；;]\s*(?=(?:vt|vi|v|n|adj|adv|prep|pron|conj|num)\.)/))
    .map((item) => item.trim())
    .filter(Boolean);
  const groups = [];
  let current = null;
  for (const chunk of chunks) {
    const match = chunk.match(posPattern);
    if (match) {
      const pos = `${match[1]}.`;
      if (!groups.length || groups[groups.length - 1].pos !== pos) {
        groups.push({ pos, defs: [] });
      }
      current = groups[groups.length - 1];
      if (match[2]) current.defs.push(match[2]);
    } else if (current) {
      current.defs.push(chunk);
    }
  }
  return groups.filter((group) => group.defs.length);
}

function parseExamples(text) {
  return String(text || "")
    .split(/\n/)
    .map((line) => line.trim().replace(/^\d+\.\s*/, ""))
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^(.*?)（(.*?)）$/);
      return match ? { en: match[1].trim(), zh: match[2].trim() } : { en: line, zh: "" };
    });
}

function payloadFromCsv(text) {
  const rows = csvToObjects(text);
  const moduleCounts = new Map();
  const moduleOrders = new Map();
  const words = rows.map((row) => {
    const source = row["来源"].trim();
    const unitOrder = (moduleOrders.get(source) || 0) + 1;
    moduleOrders.set(source, unitOrder);
    moduleCounts.set(source, (moduleCounts.get(source) || 0) + 1);
    return {
      id: `${slugSource(source)}:${unitOrder}`,
      word: row["单词"].trim(),
      module: source,
      kind: kindOf(source),
      source: "data/vocab.csv",
      definition: row["释义"].replace(/\s*\n\s*/g, " / ").trim(),
      pos_defs: parsePosDefs(row["释义"]),
      etymology: row["词源"].trim(),
      formation_semantic: "",
      examples: parseExamples(row["例句"]),
      content_status: row["释义"].trim() && row["词源"].trim() ? "complete" : "partial",
      order: {
        global: Number(row["序号"]),
        unit: unitOrder,
      },
    };
  });
  const modules = [...moduleCounts.entries()]
    .map(([name, count]) => ({ name, kind: kindOf(name), count }))
    .sort((left, right) => {
      const a = moduleSortKey(left.name);
      const b = moduleSortKey(right.name);
      return a[0] - b[0] || a[1] - b[1];
    });
  return {
    version: 5,
    schema: "hbs-vocab-csv-runtime-v1",
    source: DATA_URL,
    total: words.length,
    modules,
    words,
  };
}

function wordFieldsHtml(word) {
  const formationSemantic = word.formation_semantic || [word.formation, word.semantic].filter(Boolean).join(" ");
  return `
    ${posDefsHtml(word)}
    ${field("词源", word.etymology)}
    ${field("构词", formationSemantic)}
    ${field("记忆", word.memory)}
    ${examplesHtml(word)}
  `;
}

function reviewActionsHtml() {
  return `
    <div class="actions">
      <button class="review-btn" data-score="0" type="button">不认识</button>
      <button class="review-btn" data-score="1" type="button">模糊</button>
      <button class="review-btn" data-score="2" type="button">认识</button>
    </div>
  `;
}

function wordHtml(word, options = {}) {
  const { withActions = false, hidden = false } = options;
  return `
    <article class="word-entry ${hidden ? "is-hidden-answer" : ""}">
      <div class="word-head">
        <h2>${escapeHtml(word.word)}</h2>
        <span class="module-chip">${escapeHtml(word.module)}</span>
      </div>
      ${hidden ? `
        <button class="blank-answer" id="revealAnswer" type="button" aria-label="显示释义">
          <span>释义已隐藏</span>
          <strong>轻点屏幕查看释义、词源、构词和例句</strong>
        </button>
      ` : `
        ${wordFieldsHtml(word)}
        ${withActions ? reviewActionsHtml() : ""}
      `}
    </article>
  `;
}

function todayStatsHtml(s) {
  const done = Math.min(app.todayIndex, s.plan);
  return `
    <section class="stats">
      <div class="stat"><strong>${s.learned}</strong><span>已见过</span></div>
      <div class="stat"><strong>${s.wrong}</strong><span>错词</span></div>
      <div class="stat"><strong>${done}/${s.plan}</strong><span>今日计划</span></div>
    </section>
  `;
}

function planControlHtml() {
  return `
    <section class="plan-control" aria-label="今日计划设置">
      <label for="todayPlanInput">今日计划目标</label>
      <input id="todayPlanInput" class="plan-input" type="number" min="${MIN_TODAY_PLAN}" max="${MAX_TODAY_PLAN}" step="5" value="${todayPlan()}">
      <span>词</span>
    </section>
  `;
}

function bindPlanControl() {
  const input = document.querySelector("#todayPlanInput");
  if (!input) return;
  input.addEventListener("change", () => setTodayPlan(input.value));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") input.blur();
  });
}

function setView(name) {
  app.view = name;
  app.activeWord = null;
  tabs.forEach((tab) => tab.classList.toggle("is-active", tab.dataset.view === name));
  if (name === "today") renderToday();
  if (name === "units") renderUnits();
  if (name === "search") renderSearch();
  if (name === "mistakes") renderMistakes();
}

function renderToday() {
  if (!app.todayQueue.length) buildTodayQueue();
  const s = stats();
  const word = app.todayQueue[app.todayIndex];
  if (!word) {
    viewEl.innerHTML = `
      ${todayStatsHtml(s)}
      ${planControlHtml()}
      <section class="empty">
        <h2>今天完成了</h2>
        <p>可以去错词本再过一遍，或者从 Unit 里继续学习。</p>
        <button class="primary-btn" id="moreToday" type="button">今日计划增加 40 个</button>
      </section>
    `;
    bindPlanControl();
    document.querySelector("#moreToday")?.addEventListener("click", () => {
      Object.values(app.progress.reviews).forEach((item) => {
        if (item.due === todayKey() && item.score === 2) item.due = daysFromNow(1);
      });
      setTodayPlan(todayPlan() + 40);
    });
    return;
  }
  viewEl.innerHTML = `
    ${todayStatsHtml(s)}
    ${planControlHtml()}
    ${wordHtml(word, { withActions: true, hidden: !app.answerVisible })}
  `;
  bindPlanControl();
  document.querySelector("#revealAnswer")?.addEventListener("click", () => {
    app.answerVisible = true;
    renderToday();
  });
  viewEl.querySelectorAll(".review-btn").forEach((btn) => {
    btn.addEventListener("click", () => reviewWord(word.id, Number(btn.dataset.score)));
  });
}

function renderUnits() {
  const modules = app.payload.modules;
  if (app.activeModule) {
    const words = app.words.filter((word) => word.module === app.activeModule);
    viewEl.innerHTML = `
      <div class="toolbar">
        <button class="ghost-btn" id="backUnits" type="button">返回</button>
        <h2>${escapeHtml(app.activeModule)}</h2>
      </div>
      <div class="list">
        ${words.map((word) => rowHtml(word)).join("")}
      </div>
    `;
    document.querySelector("#backUnits").addEventListener("click", () => {
      app.activeModule = null;
      renderUnits();
    });
    bindRows();
    return;
  }
  viewEl.innerHTML = `
    <section>
      <h2>模块学习</h2>
      <p class="muted">按 PDF 的 Unit 顺序浏览，适合系统复习。</p>
      <div class="unit-grid">
        ${modules.map((item) => `
          <button class="unit-btn" data-module="${escapeHtml(item.name)}" type="button">
            <strong>${escapeHtml(item.name)}</strong>
            <span>${item.count} 词</span>
          </button>
        `).join("")}
      </div>
    </section>
  `;
  viewEl.querySelectorAll(".unit-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      app.activeModule = btn.dataset.module;
      renderUnits();
    });
  });
}

function rowHtml(word) {
  const review = getReview(word.id);
  const flag = review.wrong ? "错词" : review.seen ? "已学" : word.kind;
  return `
    <button class="row-btn" data-id="${escapeHtml(word.id)}" type="button">
      <strong>${escapeHtml(word.word)}</strong>
      <span>${escapeHtml(flag)}</span>
    </button>
  `;
}

function bindRows() {
  viewEl.querySelectorAll(".row-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const word = app.byId.get(btn.dataset.id);
      renderDetail(word);
    });
  });
}

function renderDetail(word) {
  app.activeWord = word;
  viewEl.innerHTML = `
    <div class="toolbar">
      <button class="ghost-btn" id="backDetail" type="button">返回</button>
      <button class="small-btn" id="markWrong" type="button">加入错词</button>
    </div>
    ${wordHtml(word)}
  `;
  document.querySelector("#backDetail").addEventListener("click", () => setView(app.view));
  document.querySelector("#markWrong").addEventListener("click", () => {
    const old = getReview(word.id);
    app.progress.reviews[word.id] = { ...old, seen: old.seen || 1, wrong: true, score: 0, last: todayKey(), due: todayKey() };
    saveProgress();
    renderDetail(word);
  });
}

function renderSearch() {
  viewEl.innerHTML = `
    <section>
      <h2>搜索</h2>
      <input class="search-input" id="searchBox" type="search" placeholder="输入英文单词，例如 radiate" autocomplete="off">
      <div id="searchResults" class="list"></div>
    </section>
  `;
  const box = document.querySelector("#searchBox");
  const results = document.querySelector("#searchResults");
  box.addEventListener("input", () => {
    const query = box.value.trim().toLowerCase();
    if (!query) {
      results.innerHTML = "";
      return;
    }
    const matches = app.words
      .filter((word) => word.word.toLowerCase().includes(query))
      .slice(0, 80);
    results.innerHTML = matches.length ? matches.map((word) => rowHtml(word)).join("") : '<div class="empty">没有找到</div>';
    bindRows();
  });
  setTimeout(() => box.focus(), 50);
}

function renderMistakes() {
  const words = app.words.filter((word) => getReview(word.id).wrong);
  viewEl.innerHTML = `
    <section>
      <h2>错词本</h2>
      <p class="muted">点击词条查看解释；在今日复习中点“认识”后会逐步延后复习。</p>
      <div class="list">
        ${words.length ? words.map((word) => rowHtml(word)).join("") : '<div class="empty">还没有错词</div>'}
      </div>
    </section>
  `;
  bindRows();
}

async function boot() {
  const res = await fetch(DATA_URL);
  app.payload = payloadFromCsv(await res.text());
  app.words = app.payload.words;
  app.byId = new Map(app.words.map((word) => [word.id, word]));
  buildTodayQueue();
  setView("today");
}

tabs.forEach((tab) => tab.addEventListener("click", () => setView(tab.dataset.view)));
installHelp.addEventListener("click", () => helpDialog.showModal());

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch(() => {});
  });
}

boot().catch((error) => {
  viewEl.innerHTML = `
    <section class="empty">
      <h2>载入失败</h2>
      <p>${escapeHtml(error.message)}</p>
    </section>
  `;
});
