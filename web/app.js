/* 电气秋招整合站 · 前端逻辑（原生 JS，无依赖） */
"use strict";

// ---------------- 工具 ----------------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const esc = (s) => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;").replace(/'/g, "&#39;");

function toast(msg, ms = 2200) {
  const el = $("#toast");
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms);
}

function today() { return new Date().toISOString().slice(0, 10); }

function daysLeft(c) {
  if (!c.deadline) return null;
  const d = new Date(c.deadline + "T23:59:59");
  if (isNaN(d)) return null;
  return Math.ceil((d - new Date()) / 86400000);
}

// 兼容老内核：统一用显式判断，不用 ?. 和 ?? 语法（老版微信 X5 内核解析会整体失败）
function dlVal(c) {
  const d = daysLeft(c);
  return d === null ? 9999 : d;
}

function deadlineText(c) {
  const dl = daysLeft(c);
  if (c.deadline) {
    if (dl === null) return "截止 " + c.deadline;
    if (dl < 0) return `已于 ${c.deadline} 截止`;
    return `<span class="deadline-soon">截止 ${c.deadline}（还剩 ${dl} 天）</span>`;
  }
  return c.deadline_note ? `⏰ ${esc(c.deadline_note)}` : "⏰ 时间以官方公告为准";
}

const STATUS_CLASS = { "进行中": "green", "即将截止": "orange", "常年招聘": "green" };

// ---------------- 全局状态 ----------------
let META = null;
let COMPANIES = [];
const F = { q: "", batch: "", cat: "", sub: "", status: "", city: "", year: "", tag: "", pinned: false, sort: "recommend" };

const CITY_OPTIONS = [
  ["广东（全省）", ["广东", "广州", "深圳", "珠海", "佛山", "东莞", "中山", "惠州", "湛江", "肇庆", "江门", "汕头", "揭阳"]],
  ["湛江（粤西）", ["湛江"]],
  ["茂名（粤西）", ["茂名"]],
  ["阳江（粤西）", ["阳江"]],
  ["全国多地", ["全国"]],
  ["北京", ["北京"]], ["上海", ["上海"]], ["广州", ["广州"]], ["深圳", ["深圳"]],
  ["南京", ["南京"]], ["西安", ["西安"]], ["成都", ["成都"]], ["武汉", ["武汉"]],
  ["杭州", ["杭州"]], ["合肥", ["合肥"]], ["长沙", ["长沙"]], ["重庆", ["重庆"]],
];

// ---------------- 数据加载 ----------------
function computeStats() {
  const closing = COMPANIES.filter(c => {
    if (c.status === "即将截止") return true;
    const dl = daysLeft(c);
    return dl !== null && dl >= 0 && dl <= 14;
  }).length;
  return {
    total: COMPANIES.length,
    hiring: COMPANIES.filter(c => ["进行中", "常年招聘"].includes(c.status)).length,
    autumn: COMPANIES.filter(c => (c.batch || []).includes("秋招")).length,
    intern: COMPANIES.filter(c => (c.batch || []).includes("实习")).length,
    closing,
    pinned: COMPANIES.filter(c => c.pinned).length,
  };
}

async function loadData() {
  if (window.STATIC_DATA) {
    // 离线快照模式（分享导出的单文件网页）：无后端，数据全部内嵌
    COMPANIES = window.STATIC_DATA.companies;
    META = window.STATIC_DATA.meta;
    document.body.classList.add("static");
    renderStats(computeStats());
    $("#footer-last-refresh").textContent = "离线快照 · 生成于 " + (window.STATIC_DATA.generated || "");
    return;
  }
  const [metaRes, compRes, statsRes] = await Promise.all([
    fetch("/api/meta").then(r => r.json()),
    fetch("/api/companies").then(r => r.json()),
    fetch("/api/stats").then(r => r.json()),
  ]);
  META = metaRes;
  COMPANIES = compRes.companies;
  renderStats(statsRes);
  $("#footer-last-refresh").textContent = META.refresh.finished_at || "尚未运行过";
}

function renderStats(s) {
  $("#stats-grid").innerHTML = `
    <div class="stat-card"><div class="num">${s.total}</div><div class="lbl">企业总数</div></div>
    <div class="stat-card"><div class="num green">${s.hiring}</div><div class="lbl">正在招聘</div></div>
    <div class="stat-card"><div class="num">${s.autumn}</div><div class="lbl">含秋招</div></div>
    <div class="stat-card"><div class="num">${s.intern}</div><div class="lbl">含实习</div></div>
    <div class="stat-card"><div class="num orange">${s.closing}</div><div class="lbl">即将截止</div></div>`;
}

// ---------------- 筛选 UI ----------------
function buildFilters() {
  // 批次
  const batchBox = $("#f-batch");
  batchBox.innerHTML = '<span class="group-label">批次</span>' +
    ["", ...META.batches].map(b =>
      `<button class="chip ${F.batch === b ? "active" : ""}" data-batch="${b}">${b || "全部批次"}</button>`).join("");
  batchBox.querySelectorAll("[data-batch]").forEach(el => el.onclick = () => {
    F.batch = el.dataset.batch; buildFilters(); renderList();
  });
  // 方向
  const catBox = $("#f-cat");
  const catLabels = Object.entries(META.cats).map(([k, v]) => [k, v.label]);
  catBox.innerHTML = '<span class="group-label">方向</span>' +
    `<button class="chip ${F.cat === "" ? "active" : ""}" data-cat="">全部类型</button>` +
    catLabels.map(([k, v]) =>
      `<button class="chip ${F.cat === k ? "active" : ""}" data-cat="${k}">${v}</button>`).join("");
  catBox.querySelectorAll("[data-cat]").forEach(el => el.onclick = () => {
    F.cat = el.dataset.cat; F.sub = ""; buildFilters(); renderList();
  });
  // 状态
  const stBox = $("#f-status");
  stBox.innerHTML = '<span class="group-label">状态</span>' +
    `<button class="chip ${F.status === "" ? "active" : ""}" data-status="">全部状态</button>` +
    META.statuses.map(s =>
      `<button class="chip ${F.status === s ? "active" : ""}" data-status="${s}">${s}</button>`).join("");
  stBox.querySelectorAll("[data-status]").forEach(el => el.onclick = () => {
    F.status = el.dataset.status; buildFilters(); renderList();
  });
  // 子类
  const subs = F.cat ? META.cats[F.cat].subs
    : Object.values(META.cats).map(function (v) { return v.subs; }).reduce(function (a, b) { return a.concat(b); }, []);
  $("#f-sub").innerHTML = '<option value="">全部子类</option>' +
    subs.map(s => `<option ${F.sub === s ? "selected" : ""}>${s}</option>`).join("");
  // 城市
  $("#f-city").innerHTML = '<option value="">全部城市</option>' +
    CITY_OPTIONS.map(([label]) => `<option ${F.city === label ? "selected" : ""}>${label}</option>`).join("");
  // 届别
  $("#f-year").innerHTML = '<option value="">全部届别</option>' +
    META.years.map(y => `<option ${F.year === y ? "selected" : ""}>${y}</option>`).join("");
  // 标签筛选（对口度 + 门槛/属性类标签）
  $("#f-tag").innerHTML = '<option value="">标签不限</option>' +
    ["S级对口", "高度相关", "相关", "延伸方向", "门槛不高", "非标自动化", "广东有岗"].map(t => `<option ${F.tag === t ? "selected" : ""}>${t}</option>`).join("");
  // 排序
  $("#f-sort").innerHTML = Object.entries(META.sorts).map(([k, v]) =>
    `<option value="${k}" ${F.sort === k ? "selected" : ""}>${v}</option>`).join("");
}

function bindFilterControls() {
  $("#f-q").addEventListener("input", (e) => { F.q = e.target.value; renderList(); });
  $("#f-sub").onchange = (e) => { F.sub = e.target.value; renderList(); };
  $("#f-city").onchange = (e) => { F.city = e.target.value; renderList(); };
  $("#f-year").onchange = (e) => { F.year = e.target.value; renderList(); };
  $("#f-tag").onchange = (e) => { F.tag = e.target.value; renderList(); };
  $("#f-sort").onchange = (e) => { F.sort = e.target.value; renderList(); };
  $("#f-pinned").onchange = (e) => { F.pinned = e.target.checked; renderList(); };
  $("#btn-reset").onclick = () => {
    Object.assign(F, { q: "", batch: "", cat: "", sub: "", status: "", city: "", year: "", tag: "", pinned: false, sort: "recommend" });
    $("#f-q").value = ""; $("#f-pinned").checked = false;
    buildFilters(); renderList();
  };
  $("#btn-add").onclick = () => openAddModal();
}

function cityMatch(c) {
  if (!F.city) return true;
  const opt = CITY_OPTIONS.find(([label]) => label === F.city);
  if (!opt) return true;
  const hay = (c.cities || []).join(" ");
  return opt[1].some(sub => hay.includes(sub));
}

function filtered() {
  const q = F.q.trim().toLowerCase();
  const TAG_RANK = { "S级对口": 0, "高度相关": 1, "相关": 2, "延伸方向": 3 };
  const ST_RANK = { "进行中": 0, "即将截止": 1, "常年招聘": 2, "未开启": 3, "未知": 4, "已结束": 5 };
  let list = COMPANIES.filter(c => {
    if (q) {
      const hay = [c.name, c.alias, c.industry, c.desc, c.sub, c.ctype,
        ...(c.positions || []), ...(c.cities || []), ...(c.tags || []),
        ...(c.salary_text ? [c.salary_text] : [])].join(" ").toLowerCase();
      if (!hay.includes(q)) return false;
    }
    if (F.batch && !(c.batch || []).includes(F.batch)) return false;
    if (F.cat && c.cat !== F.cat) return false;
    if (F.sub && c.sub !== F.sub) return false;
    if (F.status && c.status !== F.status) return false;
    if (F.year && c.year !== F.year) return false;
    if (F.tag && !(c.tags || []).includes(F.tag)) return false;
    if (F.pinned && !c.pinned) return false;
    return cityMatch(c);
  });
  if (F.sort === "deadline") {
    list.sort((a, b) => dlVal(a) - dlVal(b));
  } else if (F.sort === "updated") {
    list.sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  } else if (F.sort === "name") {
    list.sort((a, b) => a.name.localeCompare(b.name, "zh"));
  } else {
    const rankOf = (c) => {
      const t = (c.tags || []).find(x => x in TAG_RANK);
      return [(c.pinned ? 0 : 1), t === undefined ? 9 : TAG_RANK[t], ST_RANK[c.status] === undefined ? 9 : ST_RANK[c.status], c.name];
    };
    list.sort((a, b) => {
      const ka = rankOf(a);
      const kb = rankOf(b);
      return ka < kb ? -1 : ka > kb ? 1 : 0;
    });
  }
  return list;
}

// ---------------- 企业卡片 ----------------
function cardTags(c) {
  const tags = [];
  if (c.auto_added) tags.push('<span class="tag rec">🤖 自动收录</span>');
  for (const b of (c.batch || [])) tags.push(`<span class="tag batch">${b}</span>`);
  tags.push(`<span class="tag cat">${esc(c.sub)}</span>`);
  if (c.ctype) tags.push(`<span class="tag">${esc(c.ctype)}</span>`);
  tags.push(`<span class="tag status-${esc(c.status)}">${esc(c.status)}</span>`);
  if (c.year) tags.push(`<span class="tag">${esc(c.year)}</span>`);
  return tags.join("");
}

function eeTag(c) {
  const tags = c.tags || [];
  if (tags.includes("S级对口")) return '<span class="tag s-ee">⚡S级对口</span>';
  if (tags.includes("高度相关")) return '<span class="tag hi-ee">⚡高度相关</span>';
  return "";
}

function cardHTML(c, idx) {
  const dl = daysLeft(c);
  const closingSoon = c.status === "即将截止" || (dl !== null && dl >= 0 && dl <= 14);
  const news = (c.news || [])[0];
  return `
  <article class="company-card ${c.pinned ? "pinned" : ""} ${closingSoon ? "closing-soon" : ""}" data-id="${c.id}">
    <div class="cc-top">
      <span class="cc-name" data-detail="${c.id}">${esc(c.name)}</span>
      ${c.pinned ? '<span class="tag rec">🏆 重点推荐</span>' : ""}
      ${c.link_status === "dead" ? '<span class="tag link-dead">⚠️ 链接失效</span>' : ""}
      ${eeTag(c)}
      <span class="cc-badges">${cardTags(c)}</span>
      <span class="cc-actions">
        <a class="btn btn-primary btn-sm" href="${esc(c.apply_url || c.official_site || "#")}" target="_blank" rel="noopener"
           onclick="${c.apply_url ? "" : "event.preventDefault();toast(\'该企业暂无投递链接，请先在编辑中补充\')"}">去投递 ↗</a>
        <button class="btn btn-sm" data-detail="${c.id}">详情</button>
        ${c.auto_added ? `<button class="btn btn-sm" data-del="${c.id}" title="删除这条自动收录">🗑</button>` : ""}
      </span>
    </div>
    <div class="cc-meta">
      📍 ${(c.cities || []).join(" / ") || "—"}<span class="sep">·</span>💼 ${(c.positions || []).slice(0, 6).join(" / ") || "—"}<span class="sep">·</span>${deadlineText(c)}
    </div>
    ${c.desc ? `<div class="cc-desc">${esc(c.desc)}</div>` : ""}
    ${c.ee_notes ? `<div class="cc-ee" data-detail="${c.id}"><span class="ee-mark">⚡电气向导</span>${esc(c.ee_notes)}</div>` : ""}
    ${c.salary_text ? `<div class="cc-news">💰 ${esc(c.salary_text)} <span style="opacity:.65">（仅供参考）</span></div>` : ""}
    ${news ? `<div class="cc-news">🆕 <a href="${esc(news.url)}" target="_blank" rel="noopener">${esc(news.title)}</a></div>` : ""}
  </article>`;
}

function renderList() {
  const list = filtered();
  $("#result-count").textContent = `共 ${list.length} 家`;
  const pinned = list.filter(c => c.pinned);
  const rest = list.filter(c => !c.pinned);
  let html = "";
  if (pinned.length && F.sort === "recommend") {
    html += `<div class="section-head"><span class="pinned-strip"></span>🏆 重点推荐·优先投递
      <span class="badge-count">${pinned.length} 家</span>
      <span class="head-note">行业公认头部，建议优先准备</span></div>` +
      pinned.map(cardHTML).join("");
    if (rest.length) {
      html += `<div class="section-head">全部企业<span class="badge-count">${rest.length} 家</span></div>` + rest.map(cardHTML).join("");
    }
  } else {
    html = list.map(cardHTML).join("");
  }
  $("#company-list").innerHTML = html || `<div class="empty-tip">没有符合条件的企业，试试放宽筛选或点「提交上新」补充 🤝</div>`;
  bindCardEvents();
}

function bindCardEvents() {
  $$("[data-detail]").forEach(el => el.onclick = () => openDetail(el.dataset.detail));
  $$("[data-del]").forEach(el => el.onclick = () => deleteCompany(el.dataset.del));
}

async function deleteCompany(id) {
  const c = COMPANIES.find(x => x.id === id);
  if (!c || !confirm(`确定删除「${c.name}」？\n（自动收录的企业可随时删除；若它来自种子库，重建数据时会回来）`)) return;
  const res = await fetch("/api/companies/" + id, { method: "DELETE" });
  if (!res.ok) { toast("删除失败"); return; }
  toast(`已删除「${c.name}」`);
  closeModal("modal-detail");
  await loadData();
  renderList();
}

// ---------------- 详情弹窗 ----------------
function detailHTML(c) {
  const dl = daysLeft(c);
  const rows = [
    ["方向 / 子类", `${esc((META.cats[c.cat] || {}).label || c.cat)} / ${esc(c.sub)}`],
    ["企业类型", `${esc(c.ctype)}${c.industry ? " · " + esc(c.industry) : ""}`],
    ["工作城市", esc((c.cities || []).join("、") || "—")],
    ["岗位方向", esc((c.positions || []).join("、") || "—")],
    ["批次 / 届别", `${esc((c.batch || []).join("、"))} · ${esc(c.year)} · <span class="tag status-${esc(c.status)}">${esc(c.status)}</span>`],
    ["报名时间", `${c.start_date ? "开始 " + esc(c.start_date) + "　" : ""}${c.deadline ? "截止 " + esc(c.deadline) + (dl !== null && dl >= 0 ? `（还剩 ${dl} 天）` : "") : ""}${c.deadline_note ? "<br>⏰ " + esc(c.deadline_note) : ""}`],
  ];
  let positions = "";
  if ((c.position_details || []).length) {
    positions = `<hr class="divider"><h3 style="font-size:15px;margin-bottom:8px">🎯 岗位级投递入口</h3>
      <table class="pos-table"><tr><th>岗位</th><th>城市</th><th>学历</th><th></th></tr>` +
      c.position_details.map(p => `<tr><td>${esc(p.title)}</td><td>${esc(p.city || "—")}</td><td>${esc(p.degree || "—")}</td>
        <td><a class="btn btn-sm btn-primary" href="${esc(p.url)}" target="_blank" rel="noopener">投递 ↗</a></td></tr>`).join("") +
      `</table>`;
  }
  const news = (c.news || []).map(n =>
    `<div>🗓 <span class="n-date">${esc(n.date || n.fetched_at || "")}</span><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.title)}</a></div>`).join("");
  const sources = (c.sources || []).map(s =>
    `<div>[${esc(s.type)} ${esc(s.date || "")}] <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a></div>`).join("");
  return `
    <h2>${esc(c.name)} ${c.pinned ? '<span class="tag rec">🏆 重点推荐</span>' : ""}</h2>
    <p class="modal-sub">${esc(c.alias || "")}${c.alias ? " · " : ""}最后核验：${c.last_verified ? esc(c.last_verified) : "⚠️ 待核验（使用前建议先打开确认）"}</p>
    <dl class="detail-grid">${rows.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>
    ${c.salary_text ? `<hr class="divider"><div class="salary-box">
      <div class="sal-main">💰 ${esc(c.salary_text)}</div>
      ${c.salary_structure ? `<div>📊 ${esc(c.salary_structure)}</div>` : ""}
      <div class="sal-note">⚠️ ${esc(c.salary_source || "公开渠道聚合，仅供参考")}</div></div>` : ""}
    ${c.ee_notes ? `<hr class="divider"><div class="ee-box"><span class="ee-mark">⚡电气向导</span>${esc(c.ee_notes)}</div>` : ""}
    ${positions}
    ${news ? `<hr class="divider"><h3 style="font-size:15px;margin-bottom:6px">🆕 抓取动态</h3><div class="news-list">${news}</div>` : ""}
    <hr class="divider"><div class="src-list">
      <div>数据来源与核验${c.verify_note ? `<br>🧾 ${esc(c.verify_note)}` : ""}${(c.manual_overrides || []).length ? `<br>✍️ 人工修正过：${esc((c.manual_overrides || []).join("、"))}` : ""}</div>
      ${sources}</div>
    <div class="modal-footer">
      ${c.official_site ? `<a class="btn" href="${esc(c.official_site)}" target="_blank" rel="noopener">🌐 官网</a>` : ""}
      <button class="btn btn-edit" onclick="openEditModal('${c.id}')">✏️ 修正</button>      <a class="btn btn-green" href="${esc(c.apply_url || c.official_site || "#")}" target="_blank" rel="noopener">去投递 ↗</a>
    </div>`;
}

async function openDetail(id) {
  const c = COMPANIES.find(x => x.id === id);
  if (!c) return;
  $("#detail-body").innerHTML = detailHTML(c);
  openModal("modal-detail");
}

// ---------------- 编辑弹窗 ----------------
function formValue(id) { const el = document.getElementById(id); return el ? el.value : ""; }

function openEditModal(id) {
  const c = COMPANIES.find(x => x.id === id);
  if (!c) return;
  closeModal("modal-detail");
  $("#edit-sub").textContent = `${c.name} · 人工修改的字段会被标记保护，爬虫更新不会覆盖`;
  const tags = c.tags || [];
  const batches = c.batch || [];
  const dates = [c.start_date, c.deadline].map(d => d || "");
  $("#edit-form").innerHTML = `
    <div class="form-item"><label>状态</label><select id="e-status">${META.statuses.map(s => `<option ${c.status === s ? "selected" : ""}>${s}</option>`).join("")}</select></div>
    <div class="form-item"><label>重点推荐</label><label class="switch-label" style="padding:9px 0"><input type="checkbox" id="e-pinned" ${c.pinned ? "checked" : ""}> 显示在重点推荐区</label></div>
    <div class="form-item"><label>报名开始日期</label><input type="date" id="e-start" value="${dates[0]}"></div>
    <div class="form-item"><label>报名截止日期</label><input type="date" id="e-deadline" value="${dates[1]}"></div>
    <div class="form-item full"><label>时间说明（如：一批约10月报名，二批次年3月）</label><input id="e-dlnote" value="${esc(c.deadline_note)}"></div>
    <div class="form-item"><label>官方投递入口</label><input id="e-apply" value="${esc(c.apply_url)}"></div>
    <div class="form-item"><label>企业官网</label><input id="e-site" value="${esc(c.official_site)}"></div>
    <div class="form-item full"><label>薪资区间（如 8-12k×13薪）</label><input id="e-salary" value="${esc(c.salary_text)}"></div>
    <div class="form-item full"><label>薪资结构说明</label><input id="e-salstruct" value="${esc(c.salary_structure)}"></div>
    <div class="form-item"><label>城市（逗号分隔）</label><input id="e-cities" value="${esc((c.cities || []).join(","))}"></div>
    <div class="form-item"><label>岗位方向（逗号分隔）</label><input id="e-positions" value="${esc((c.positions || []).join(","))}"></div>
    <div class="form-item full"><label>批次</label><div class="chip-group" style="padding:6px 0">${META.batches.map(b =>
      `<label class="switch-label"><input type="checkbox" class="e-batch" value="${b}" ${batches.includes(b) ? "checked" : ""}>${b}</label>`).join("")}</div></div>
    <div class="form-item full"><label>标签（对口度等）</label><div class="chip-group" style="padding:6px 0">${META.tags.map(t =>
      `<label class="switch-label"><input type="checkbox" class="e-tag" value="${t}" ${tags.includes(t) ? "checked" : ""}>${t}</label>`).join("")}</div></div>
    <div class="form-item full"><label>一句话说明</label><textarea id="e-desc">${esc(c.desc)}</textarea></div>
    <div class="form-item full"><label>⚡电气向导备注（笔试科目/报考建议）</label><textarea id="e-ee">${esc(c.ee_notes)}</textarea></div>`;
  $("#edit-error").textContent = "";
  openModal("modal-edit");
  $("#btn-save-edit").onclick = () => saveEdit(c);
}

async function saveEdit(c) {
  const fields = {
    status: formValue("e-status"),
    pinned: $("#e-pinned").checked,
    start_date: formValue("e-start") || null,
    deadline: formValue("e-deadline") || null,
    deadline_note: formValue("e-dlnote"),
    apply_url: formValue("e-apply"),
    official_site: formValue("e-site"),
    salary_text: formValue("e-salary"),
    salary_structure: formValue("e-salstruct"),
    cities: formValue("e-cities").split(/[,，]/).map(s => s.trim()).filter(Boolean),
    positions: formValue("e-positions").split(/[,，]/).map(s => s.trim()).filter(Boolean),
    batch: $$(".e-batch").filter(x => x.checked).map(x => x.value),
    tags: $$(".e-tag").filter(x => x.checked).map(x => x.value),
    desc: formValue("e-desc"),
    ee_notes: formValue("e-ee"),
  };
  const res = await fetch(`/api/companies/${c.id}`, {
    method: "PATCH", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields }),
  });
  if (!res.ok) {
    $("#edit-error").textContent = "保存失败：" + (await res.json().catch(() => ({}))).detail || res.status;
    return;
  }
  closeModal("modal-edit");
  toast("已保存，字段已加入爬虫保护 ✓");
  await loadData(); renderList();
}

// ---------------- 提交上新 ----------------
function catOptions() { return Object.entries(META.cats); }

function openAddModal(prefill = {}) {
  $("#add-form").innerHTML = `
    <div class="form-item"><label>企业名称 *</label><input id="a-name" value="${esc(prefill.name || "")}" placeholder="如：正泰安能"></div>
    <div class="form-item"><label>企业类型</label><select id="a-ctype">${["央企", "国企", "民企", "外企", "合资", "事业单位"].map(t => `<option ${prefill.ctype === t ? "selected" : ""}>${t}</option>`).join("")}</select></div>
    <div class="form-item"><label>方向 *</label><select id="a-cat">${catOptions().map(([k, v]) => `<option value="${k}" ${prefill.cat === k ? "selected" : ""}>${v.label}</option>`).join("")}</select></div>
    <div class="form-item"><label>子类 *</label><select id="a-sub"></select></div>
    <div class="form-item full"><label>批次</label><div class="chip-group" style="padding:6px 0">${META.batches.map(b =>
      `<label class="switch-label"><input type="checkbox" class="a-batch" value="${b}" ${b === "秋招" ? "checked" : ""}>${b}</label>`).join("")}</div></div>
    <div class="form-item full"><label>官方投递入口（投递链接）</label><input id="a-apply" value="${esc(prefill.apply_url || "")}" placeholder="https://…"></div>
    <div class="form-item"><label>企业官网</label><input id="a-site" value="${esc(prefill.official_site || "")}"></div>
    <div class="form-item"><label>城市（逗号分隔）</label><input id="a-cities" value="${esc((prefill.cities || []).join(","))}"></div>
    <div class="form-item full"><label>薪资区间（可选）</label><input id="a-salary" value="${esc(prefill.salary_text || "")}"></div>
    <div class="form-item full"><label>一句话说明</label><input id="a-desc" value="${esc(prefill.desc || "")}"></div>
    <div class="form-item full"><label>信息来源链接</label><input id="a-src" value="${esc(prefill.source_url || "")}"></div>`;
  const syncSub = () => {
    const cat = $("#a-cat").value;
    $("#a-sub").innerHTML = META.cats[cat].subs.map(s => `<option ${prefill.sub === s ? "selected" : ""}>${s}</option>`).join("");
  };
  syncSub();
  $("#a-cat").onchange = syncSub;
  $("#add-error").textContent = "";
  openModal("modal-add");
  $("#btn-save-add").onclick = () => saveAdd();
}

async function saveAdd() {
  const body = {
    name: formValue("a-name").trim(),
    cat: formValue("a-cat"), sub: formValue("a-sub"),
    ctype: formValue("a-ctype"),
    batch: $$(".a-batch").filter(x => x.checked).map(x => x.value),
    apply_url: formValue("a-apply").trim(),
    official_site: formValue("a-site").trim(),
    cities: formValue("a-cities").split(/[,，]/).map(s => s.trim()).filter(Boolean),
    salary_text: formValue("a-salary"), desc: formValue("a-desc"),
    source_url: formValue("a-src"),
  };
  const res = await fetch("/api/companies", {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    $("#add-error").textContent = err.detail || "保存失败";
    return;
  }
  const data = await res.json();
  closeModal("modal-add");
  toast(`已添加「${body.name}」✓`);
  await loadData();
  F.q = body.name; $("#f-q").value = body.name;
  renderList();
}

// ---------------- 更新数据 ----------------
let refreshTimer = null;

async function startRefresh() {
  const res = await fetch("/api/refresh", { method: "POST" });
  if (!res.ok) { toast((await res.json().catch(() => ({}))).detail || "无法开始更新"); return; }
  openModal("modal-refresh");
  $("#refresh-sub").innerHTML = '<span class="spin">⟳</span> 正在从各数据源抓取最新动态…（后台限速抓取，预计几十秒）';
  $("#refresh-results").innerHTML = "";
  $("#refresh-snapshot").textContent = "";
  pollRefresh();
}

async function pollRefresh() {
  clearTimeout(refreshTimer);
  const st = await fetch("/api/refresh/status").then(r => r.json());
  renderRefreshResults(st);
  if (st.running) { refreshTimer = setTimeout(pollRefresh, 1200); return; }
  if (st.finished_at) {
    const okN = (st.results || []).filter(r => r.ok).length;
    const failN = (st.results || []).filter(r => r.ok === false).length;
    $("#refresh-sub").textContent = `更新完成：成功 ${okN} 个源，失败 ${failN} 个，匹配 ${st.matched} 条动态` +
      (st.auto_added ? `，🤖 自动收录 ${st.auto_added} 家新企业` : "") +
      (st.inbox_new ? `，${st.inbox_new} 条进收件箱` : "");
    $("#footer-last-refresh").textContent = st.finished_at;
    await loadData(); renderList();
    toast(`更新完成：匹配 ${st.matched} 条动态${st.auto_added ? `，自动收录 ${st.auto_added} 家新企业` : ""} ✓`, 3200);
  }
}

function renderRefreshResults(st) {
  $("#refresh-results").innerHTML = (st.results || []).map(r => `
    <div class="src-result">
      <span class="src-state ${r.ok === true ? "ok" : r.ok === false ? "fail" : "off"}">${r.ok === true ? "成功" : r.ok === false ? "失败" : "未启用"}</span>
      <span style="font-weight:600">${esc(r.name)}</span>
      ${r.ok === true ? `<span style="color:var(--muted)">抓到 ${r.count} 条 · ${r.ms}ms</span>` : ""}
      ${r.error ? `<span class="src-err">${esc(r.error)}</span>` : ""}
    </div>`).join("");
  if (st.snapshot) $("#refresh-snapshot").textContent = `🗂 更新前已自动备份快照：data/snapshots/${st.snapshot}`;
}

// ---------------- 每日简报 ----------------
async function openDigest() {
  openModal("modal-digest");
  $("#digest-sub").textContent = "加载中…";
  $("#digest-body").innerHTML = "";
  let d;
  try {
    const res = await fetch("/api/digest");
    if (!res.ok) throw new Error();
    d = await res.json();
  } catch (e) {
    $("#digest-sub").textContent = "还没有简报。每天 8 点后定时任务会自动生成；也可以现在点「更新数据」再回来刷新本页。";
    return;
  }
  $("#digest-sub").textContent = `生成于 ${d.generated} · 抓取 ${d.stats.fetched} 条公告 · 匹配 ${d.stats.matched} 条` +
    (d.stats.inbox_new ? ` · 收件箱 +${d.stats.inbox_new}` : "");
  const sec = (title, items, render) => items.length
    ? `<hr class="divider"><h3 style="font-size:15px;margin-bottom:6px">${title}</h3>` + items.map(render).join("")
    : "";
  $("#digest-body").innerHTML =
    sec(`🆕 新开招企业（${d.new_companies.length}）`, d.new_companies, c => `
      <div class="inbox-item"><div class="in-title">${esc(c.name)}</div>
      <div class="in-meta">${esc(c.title)}</div>
      ${c.url ? `<div class="in-actions"><a class="btn btn-sm btn-primary" href="${esc(c.url)}" target="_blank" rel="noopener">看公告 ↗</a></div>` : ""}</div>`) +
    sec(`📰 已收录企业新动态（${d.new_news.length}）`, d.new_news, n => `
      <div class="inbox-item"><div class="in-title"><a href="${esc(n.url)}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none">${esc(n.title)}</a></div>
      <div class="in-meta">${esc(n.company)}</div></div>`) +
    sec(`⏰ 14 天内截止（${d.closing.length}）`, d.closing, c => `
      <div class="inbox-item"><div class="in-title">${esc(c.name)}
        <span class="days-left">剩 ${c.days} 天</span></div>
      <div class="in-actions"><a class="btn btn-sm btn-primary" href="${esc(c.url || "#")}" target="_blank" rel="noopener">去投递 ↗</a></div></div>`) +
    (!d.new_companies.length && !d.new_news.length && !d.closing.length
      ? '<div class="empty-tip">今天暂无增量，一切尽在掌握 😌</div>' : "");
}

// ---------------- 每日简报（含关键词订阅） ----------------
async function openDigest() {
  openModal("modal-digest");
  $("#digest-sub").textContent = "加载中…";
  $("#digest-body").innerHTML = "";
  let d = null;
  try {
    const [digestRes, kwRes] = await Promise.all([
      fetch("/api/digest").then(r => { if (!r.ok) throw 0; return r.json(); }),
      fetch("/api/keywords").then(r => r.json()),
    ]);
    d = digestRes;
    renderKeywordEditor(kwRes.keywords || []);
  } catch (e) {
    $("#digest-sub").textContent = "还没有简报。每天 8 点后定时任务会自动生成；也可以现在点「更新数据」再回来刷新本页。";
    return;
  }
  $("#digest-sub").textContent = `生成于 ${d.generated} · 抓取 ${d.stats.fetched} 条公告 · 匹配 ${d.stats.matched} 条` +
    (d.stats.inbox_new ? ` · 收件箱 +${d.stats.inbox_new}` : "");
  const sec = (title, items, render) => items.length
    ? `<hr class="divider"><h3 style="font-size:15px;margin-bottom:6px">${title}</h3>` + items.map(render).join("")
    : "";
  const kwChips = hits => hits.map(h => `<span class="tag rec">⭐${esc(h)}</span>`).join(" ");
  const starredSec = (d.starred || []).length
    ? `<hr class="divider"><h3 style="font-size:15px;margin-bottom:6px">⭐ 命中你的关键词（${d.starred.length}）</h3>` +
      d.starred.map(s => `
        <div class="inbox-item" style="border-color:var(--primary)">
          <div class="in-title">${esc(s.name || s.company)} ${kwChips(s.hits)}</div>
          <div class="in-meta">${esc(s.title)}</div>
          ${s.url ? `<div class="in-actions"><a class="btn btn-sm btn-primary" href="${esc(s.url)}" target="_blank" rel="noopener">看公告 ↗</a></div>` : ""}
        </div>`).join("")
    : "";
  $("#digest-body").innerHTML = starredSec +
    sec(`🆕 新开招企业（${d.new_companies.length}）`, d.new_companies, c => `
      <div class="inbox-item"><div class="in-title">${esc(c.name)}</div>
      <div class="in-meta">${esc(c.title)}</div>
      ${c.url ? `<div class="in-actions"><a class="btn btn-sm btn-primary" href="${esc(c.url)}" target="_blank" rel="noopener">看公告 ↗</a></div>` : ""}</div>`) +
    sec(`📰 已收录企业新动态（${d.new_news.length}）`, d.new_news, n => `
      <div class="inbox-item"><div class="in-title"><a href="${esc(n.url)}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none">${esc(n.title)}</a></div>
      <div class="in-meta">${esc(n.company)}</div></div>`) +
    sec(`⏰ 14 天内截止（${d.closing.length}）`, d.closing, c => `
      <div class="inbox-item"><div class="in-title">${esc(c.name)}
        <span class="days-left">剩 ${c.days} 天</span></div>
      <div class="in-actions"><a class="btn btn-sm btn-primary" href="${esc(c.url || "#")}" target="_blank" rel="noopener">去投递 ↗</a></div></div>`) +
    (!(d.starred || []).length && !d.new_companies.length && !d.new_news.length && !d.closing.length
      ? '<div class="empty-tip">今天暂无增量，一切尽在掌握 😌</div>' : "");
}

function renderKeywordEditor(keywords) {
  const box = $("#kw-editor");
  box.innerHTML = `<span class="group-label">🔔 订阅关键词（命中的公告会在简报置顶，改动下次生成简报时生效）</span>
    <div class="chip-group" style="margin-top:6px">
      ${keywords.map(k => `<span class="chip">${esc(k)}<span class="kw-x" data-kw="${esc(k)}" title="删除"> ✕</span></span>`).join("")}
      <input class="search-box" id="kw-input" style="flex:0 0 130px;min-width:130px;padding:5px 10px" placeholder="添加关键词">
      <button class="btn btn-sm btn-green" id="kw-add">添加</button>
    </div>`;
  const save = async (kws) => {
    const res = await fetch("/api/keywords", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ keywords: kws }),
    });
    if (res.ok) { toast("订阅已保存 ✓ 下次生成简报时生效"); renderKeywordEditor((await res.json()).keywords); }
    else toast("保存失败");
  };
  box.querySelectorAll("[data-kw]").forEach(el => el.onclick = () =>
    save(keywords.filter(k => k !== el.dataset.kw)));
  box.querySelector("#kw-add").onclick = () => {
    const v = box.querySelector("#kw-input").value.trim();
    if (v && !keywords.includes(v)) save([...keywords, v]);
  };
  box.querySelector("#kw-input").onkeydown = (e) => {
    if (e.key === "Enter") box.querySelector("#kw-add").click();
  };
}

// ---------------- 公告全文搜索 ----------------
async function openSearch() {
  openModal("modal-search");
  const q = $("#article-q");
  q.focus();
  q.onkeydown = (e) => { if (e.key === "Enter") doArticleSearch(); };
  $("#btn-article-go").onclick = doArticleSearch;
}

async function doArticleSearch() {
  const q = $("#article-q").value.trim();
  const box = $("#article-results");
  if (!q) { box.innerHTML = '<div class="empty-tip">输入关键词开始搜索</div>'; return; }
  box.innerHTML = '<div class="empty-tip">搜索中…</div>';
  const res = await fetch("/api/search?q=" + encodeURIComponent(q));
  const data = await res.json();
  if (!data.results.length) {
    box.innerHTML = `<div class="empty-tip">没有包含「${esc(q)}」的存档公告</div>`;
    return;
  }
  const qEsc = esc(q);
  box.innerHTML = `<p class="form-hint" style="margin:8px 0">命中 ${data.results.length} 篇存档公告</p>` +
    data.results.map(r => {
      const hl = esc(r.snippet).split(qEsc).join("<mark>" + qEsc + "</mark>");
      return `<div class="inbox-item">
        <div class="in-title"><a href="${esc(r.url)}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none">${esc(r.title)}</a></div>
        <div class="in-meta">${esc(r.company || "未匹配企业")} · ${esc(r.fetched_at)}</div>
        <div style="font-size:12.5px;line-height:1.7;color:var(--muted)">…${hl}…</div>
      </div>`;
    }).join("");
}

// ---------------- 链接体检 ----------------
let linkcheckTimer = null;

async function openLinkcheck() {
  openModal("modal-linkcheck");
  await renderLinkcheck();
}

async function renderLinkcheck() {
  clearTimeout(linkcheckTimer);
  const d = await fetch("/api/linkcheck").then(r => r.json());
  $("#linkcheck-sub").textContent = d.last_run
    ? `上次检查：${d.last_run.replace("T", " ")} · 正常 ${d.ok} / 共 ${d.total} 个入口`
    : "还没有检查过，点下方按钮开始";
  $("#btn-linkcheck-run").disabled = !!d.running;
  $("#btn-linkcheck-run").textContent = d.running ? "检查进行中…" : "立即检查全部链接";
  const deadList = d.dead.map(x => `
    <div class="inbox-item" style="border-color:var(--red)">
      <div class="in-title">⚠️ ${esc(x.company || x.url)} <span class="src-err">${esc(x.note)}</span></div>
      <div class="in-meta"><a href="${esc(x.url)}" target="_blank" rel="noopener" style="color:var(--muted)">${esc(x.url)}</a></div>
      <div class="in-actions"><button class="btn btn-sm" onclick="toast('请在卡片上点「详情→修正」更新链接')">怎么修？</button></div>
    </div>`).join("");
  const suspectList = d.suspect.length
    ? `<hr class="divider"><h3 style="font-size:14px;margin-bottom:6px">🟡 疑似防爬（多为 WAF 拦探测，浏览器人工一般可达，无需处理）</h3>` +
      d.suspect.map(x => `<div class="src-result"><span class="src-state off">${esc(String(x.status))}</span><span>${esc(x.company || x.url)}</span></div>`).join("")
    : "";
  $("#linkcheck-body").innerHTML =
    (d.dead.length ? `<hr class="divider"><h3 style="font-size:15px;margin-bottom:6px">⚠️ 失效入口（${d.dead.length}）—— 点卡片「详情→修正」更新链接</h3>` + deadList
      : (d.last_run ? '<hr class="divider"><div class="empty-tip">✅ 暂无失效链接</div>' : "")) + suspectList;
  if (d.running) linkcheckTimer = setTimeout(renderLinkcheck, 3000);
}

// ---------------- 收件箱 ----------------
async function openInbox() {
  const data = await fetch("/api/inbox").then(r => r.json());
  const items = data.items || [];
  $("#inbox-list").innerHTML = items.length ? items.map(i => `
    <div class="inbox-item">
      <div class="in-title"><a href="${esc(i.url)}" target="_blank" rel="noopener" style="color:var(--primary);text-decoration:none">${esc(i.title)}</a></div>
      <div class="in-meta">来源 ${esc(i.source || "—")} · ${esc(i.date || i.fetched_at || "")}</div>
      <div class="in-actions">
        <button class="btn btn-sm btn-green" onclick='promoteInbox(${JSON.stringify(JSON.stringify(i))})'>转为企业</button>
        <button class="btn btn-sm" onclick="dismissInbox('${esc(i.url)}')">忽略</button>
      </div>
    </div>`).join("") : '<div class="empty-tip">收件箱是空的。跑一次「更新数据」后，未匹配企业的公告会出现在这里。</div>';
  openModal("modal-inbox");
}

function promoteInbox(jsonStr) {
  const item = JSON.parse(jsonStr);
  closeModal("modal-inbox");
  const m = item.title.match(/([\u4e00-\u9fa5A-Za-z0-9（）()·]{2,20})(?:集团|股份|有限公司|公司)/);
  openAddModal({
    name: m ? m[0] : "",
    desc: item.title,
    source_url: item.url,
    apply_url: item.url && item.url.includes("zhaopin") ? item.url : "",
  });
}

async function dismissInbox(url) {
  await fetch("/api/inbox?url=" + encodeURIComponent(url), { method: "DELETE" });
  openInbox();
}

// ---------------- 时间线 ----------------
function monthKey(dateStr) {
  if (!dateStr) return null;
  const d = new Date(dateStr + "T00:00:00");
  if (isNaN(d)) return null;
  return `${d.getFullYear()}年${d.getMonth() + 1}月`;
}

// 从时间说明解析预计月份，如「一批约2026年10月报名」→ 2026年10月
function noteMonth(note) {
  if (!note) return null;
  const m = note.match(/(20\d{2})\s*年\s*(\d{1,2})\s*月/);
  if (m) return `${m[1]}年${parseInt(m[2])}月`;
  const m2 = note.match(/(\d{1,2})\s*月/);
  if (m2) return `2026年${parseInt(m2[1])}月`;
  return null;
}

function monthSortKey(key) {
  const m = key.match(/(20\d{2})年(\d{1,2})月/);
  if (!m) return "9999-99";
  return `${m[1]}-${String(m[2]).padStart(2, "0")}`;
}

function renderTimeline() {
  const entries = COMPANIES.filter(c => c.deadline || c.start_date || c.deadline_note);
  const groups = new Map();
  for (const c of entries) {
    let key = null, approx = false, from = null, to = null;
    if (c.deadline || c.start_date) {
      key = monthKey(c.deadline || c.start_date);
      from = c.start_date; to = c.deadline;
    } else {
      const nm = noteMonth(c.deadline_note);
      if (nm) { key = nm + "（预计）"; approx = true; }
    }
    if (!key) key = "时间待定";
    if (!groups.has(key)) groups.set(key, { approx, items: [] });
    groups.get(key).items.push({ c, from, to });
  }
  const keys = Array.from(groups.keys()).sort((a, b) =>
    monthSortKey(a).localeCompare(monthSortKey(b)));
  let html = "";
  for (const key of keys) {
    const g = groups.get(key);
    const isTbd = key === "时间待定";
    html += `<div class="timeline-month">${isTbd ? "🕘 时间待定（以官网公告为准）" : "📌 " + key + (g.approx ? "：" : "")}</div>`;
    for (const { c, to } of g.items) {
      const dl = daysLeft(c);
      const past = dl !== null && dl < 0;
      const closing = dl !== null && dl >= 0 && dl <= 14;
      html += `<div class="timeline-item">
        <div class="tl-dot ${past ? "past" : closing ? "closing" : ""}"></div>
        <div class="tl-main">
          <div class="tl-title" data-detail="${c.id}">${esc(c.name)} <span class="tag status-${esc(c.status)}">${esc(c.status)}</span></div>
          <div class="tl-date">${to ? "截止 " + esc(to) : esc(c.deadline_note || "时间以官方公告为准")}</div>
        </div>
        <div class="tl-right">
          <div class="days-left ${past ? "past" : ""}">${dl === null ? "" : past ? "已截止" : closing ? `⏳ 剩 ${dl} 天` : `剩 ${dl} 天`}</div>
          <a class="btn btn-sm btn-primary" style="margin-top:6px" href="${esc(c.apply_url || "#")}" target="_blank" rel="noopener">投递 ↗</a>
        </div>
      </div>`;
    }
  }
  $("#tl-count-badge").textContent = `${entries.length} 家有排期信息`;
  $("#timeline-content").innerHTML = html || '<div class="empty-tip">暂无时间线数据</div>';
  $$("#timeline-content [data-detail]").forEach(el => el.onclick = () => openDetail(el.dataset.detail));
}

// ---------------- 电气专区 ----------------
const GUIDE = [
  {
    icon: "🔌", title: "电网 / 发电 / 设计院 —— 电气就业基本盘",
    fit: "适合：追求稳定、想回家乡或进大城市国企、看重五险二金与长期福利的同学。",
    exam: "怎么考：国网统一考试（电路、电机学、电力系统分析、继电保护、高电压技术、电气设备 + 行测英语，专业课占比约80%）；南网结构类似；五大发电多为官网报名+分公司面试；设计院以面试+笔试专业课为主。",
    kw: "对口岗位：变电运维、继电保护、输配电设计、调度、营销服务、电气一次/二次设计。",
    tips: "节奏：国网一批约10月报名12月考试、二批次年3月；南网约9月下旬-10月；中广核「启明星」9月初。志愿策略：电网分省报名，广东考生主场是南网（广东电网），国网报湘鄂赣桂琼等邻省也常见。",
    ids: ["sgcc", "csg", "csg-sz", "chnenergy", "spic", "chng", "cgn", "gedi", "gpg"],
  },
  {
    icon: "⚙️", title: "电气设备 / 工控 —— 技术流高薪路线",
    fit: "适合：想搞技术研发、接受企业节奏、希望薪资天花板高于电网的同学。",
    exam: "怎么考：笔试以电路+模电数电+电力电子+C语言为主（继保方向加继电保护），面试重项目与基础；外企加英语环节。",
    kw: "对口岗位：硬件开发、电机控制算法、继保研发、电源工程师、测试工程师、FAE。",
    tips: "梯队：南瑞继保/国电南瑞/汇川/思源是电气研发薪资标杆；外资三菱松下平替是西门子/ABB/施耐德/伊顿（流程规范、WLB好）；继保三强竞争激烈，建议同步投中小厂保底。",
    ids: ["nari", "nrec", "inovance", "sieyuan", "tbea", "xj", "sifang", "chint", "siemens", "abb", "schneider"],
  },
  {
    icon: "🔋", title: "新能源 / 车企 / 电池 —— 扩张期机会最多",
    fit: "适合：看好行业上行、能接受较高强度、想去基地城市低成本攒钱的同学。",
    exam: "怎么考：制造/设备类笔试偏电气基础+情景题，研发类考电力电子与硬件；流程快，投递窗口短（招满即止）。",
    kw: "对口岗位：电气设计、设备工程师、厂务动力、BMS测试、储能系统集成、高压系统工程师。",
    tips: "节奏：比亚迪8月中、蔚来/小鹏8月、宁德9月初即开，秋招主线在9月前抢完第一轮；base多为宁德/常州/合肥/西安等基地城市；广东优选比亚迪（深汕/南宁）、亿纬（惠州）、明阳（中山）。",
    ids: ["byd", "catl", "eve", "nio", "xpeng", "sungrow", "mingyang", "tesla", "longi"],
  },
  {
    icon: "🛰️", title: "泛工科延伸 —— 硬件大厂与能源央企",
    fit: "适合：专业基础扎实但不设限、想冲高薪硬件岗或能源央企设备岗的同学。",
    exam: "怎么考：华为/大疆/小米等硬件岗笔试重电路+数电+C；中海油/国家管网/中烟类央企考行测+专业课；面试看项目落地能力。",
    kw: "对口岗位：电源工程师、结构/热设计、设备工程师、厂务电气、海洋平台电气、站场电气。",
    tips: "华为电源/数字能源、大疆电机驱动对电气极友好且薪资顶级；中海油（湛江/深圳基地）、宝武湛江、广州深圳地铁是广东能源央国企里的宝藏选择。",
    ids: ["huawei", "dji", "cnooc", "baowu", "guangzhou-metro", "shenzhen-metro", "crrc-zelri", "smic", "midea", "gree"],
  },
];

const GD_COMPANIES = [
  ["csg", "南方电网·广东电网"], ["csg-sz", "深圳供电局"], ["gpg", "广东省能源集团"], ["sec", "深圳能源"],
  ["cgn", "中广核"], ["cnooc", "中国海油（湛江/深圳）"], ["baowu", "宝武湛江"], ["eve", "亿纬锂能（惠州）"],
  ["mingyang", "明阳智能（中山）"], ["xpeng", "小鹏汽车（广州）"], ["gac-aion", "广汽埃安（广州）"],
  ["guangzhou-metro", "广州地铁"], ["shenzhen-metro", "深圳地铁"], ["midea", "美的（佛山）"],
  ["gree", "格力（珠海）"], ["byd", "比亚迪（深圳）"], ["huawei", "华为"], ["dji", "大疆（深圳）"],
  ["baiyun", "白云电器（广州）"], ["oppo", "OPPO（东莞）"], ["vivo", "vivo（东莞）"], ["sunwoda", "欣旺达（深圳）"],
];

const SCHEDULE = [
  ["8月下旬-9月初", "比亚迪/美的/蔚来/小鹏/华为/大疆/汇川等民企提前批已开抢；打磨简历、刷牛客面经"],
  ["9月", "南网/国网报名窗口陆续开启；中广核启明星；设计院、外企管培（西门子/ABB/施耐德）开投"],
  ["10月", "国网一批报名+确认志愿；五大发电/中核/三峡/管网集中招聘；国聘专区投递央企"],
  ["11月-12月", "国网一批笔试（12月）；面试季高峰；及时补投春招前补录"],
  ["次年3月", "国网二批 + 春招兜底；未上车的同学重点盯补录和实习转正"],
];

function renderGuide() {
  const cards = GUIDE.map(g => `
    <div class="guide-card">
      <h3>${g.icon} ${g.title}</h3>
      <p><strong>👤 ${esc(g.fit.replace("适合：", ""))}</strong></p>
      <h4>📝 怎么考</h4><p>${esc(g.exam.replace("怎么考：", ""))}</p>
      <h4>💼 对口岗位</h4><p>${esc(g.kw.replace("对口岗位：", ""))}</p>
      <h4>💡 向导建议</h4><p>${esc(g.tips.replace("节奏：", ""))}</p>
      <h4>🏢 重点企业（点击筛选）</h4>
      <div class="gd-companies">${g.ids.map(id => {
        const c = COMPANIES.find(x => x.id === id);
        return c ? `<span class="gd-chip" data-jump="${c.id}">${esc(c.name)}</span>` : "";
      }).join("")}</div>
    </div>`).join("");
  const gd = `
    <div class="guide-card" style="grid-column:1/-1">
      <h3>🌴 广东本地重点企业（地缘优势清单）</h3>
      <p>你在广东读电气，下面这些是「离家近 + 招电气量大」的优先选择，点击直达筛选结果：</p>
      <div class="gd-companies">${GD_COMPANIES.map(([id, label]) => {
        const c = COMPANIES.find(x => x.id === id);
        return c ? `<span class="gd-chip" data-jump="${c.id}">${esc(label)}</span>` : "";
      }).join("")}</div>
    </div>
    <div class="guide-card" style="grid-column:1/-1">
      <h3>🗓 大四全年节奏表（2027届）</h3>
      <ul>${SCHEDULE.map(([t, d]) => `<li><strong>${t}</strong>：${esc(d)}</li>`).join("")}</ul>
      <h4>🔗 常用官方入口</h4>
      <p>
        <a class="guide-link" href="https://gdou.jysd.com" target="_blank" rel="noopener">广海大就业网</a> ·
        <a class="guide-link" href="https://zhaopin.sgcc.com.cn" target="_blank" rel="noopener">国网招聘平台</a> ·
        <a class="guide-link" href="https://zhaopin.csg.cn" target="_blank" rel="noopener">南网招聘</a> ·
        <a class="guide-link" href="https://www.iguopin.com" target="_blank" rel="noopener">国聘</a> ·
        <a class="guide-link" href="https://www.nowcoder.com" target="_blank" rel="noopener">牛客（面经/日历）</a>
      </p>
    </div>`;
  $("#guide-content").innerHTML = `<div class="guide-grid">${cards}${gd}</div>`;
  $$("#guide-content [data-jump]").forEach(el => el.onclick = async () => {
    const c = COMPANIES.find(x => x.id === el.dataset.jump);
    if (!c) return;
    switchView("jobs");
    F.q = c.name; $("#f-q").value = c.name;
    renderList();
    window.scrollTo({ top: 0 });
  });
}

// ---------------- 分享给微信好友（全免费） ----------------
function openShareModal() { openModal("modal-share"); }

function downloadBlob(blob, name) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 2000);
}

const trunc = (s, n) => {
  const arr = Array.from(String(s || ""));
  return arr.length > n ? arr.slice(0, n - 1).join("") + "…" : arr.join("");
};

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function buildShareCanvas() {
  const list = filtered().slice(0, 25);
  const W = 1080, ROW_H = 96, HEAD_H = 236, FOOT_H = 96;
  const H = HEAD_H + list.length * ROW_H + FOOT_H;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const ctx = cv.getContext("2d");
  const bg = ctx.createLinearGradient(0, 0, W, H);
  bg.addColorStop(0, "#eef2ff"); bg.addColorStop(0.5, "#e0f2fe"); bg.addColorStop(1, "#f5f3ff");
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  const head = ctx.createLinearGradient(0, 0, W, HEAD_H);
  head.addColorStop(0, "#4f6ef7"); head.addColorStop(1, "#10b981");
  ctx.fillStyle = head; ctx.fillRect(0, 0, W, HEAD_H - 20);
  ctx.fillStyle = "#fff";
  ctx.font = "800 46px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText("⚡ 电气秋招整合 · 2027届", 60, 88);
  ctx.font = "500 24px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.globalAlpha = 0.94;
  const st = computeStats();
  ctx.fillText(`${today()} · 共收录 ${st.total} 家企业 · 本图展示当前筛选前 ${list.length} 家`, 60, 130);
  ctx.fillText(`正在招聘 ${st.hiring} · 含秋招 ${st.autumn} · 含实习 ${st.intern} · 即将截止 ${st.closing}`, 60, 168);
  ctx.globalAlpha = 1;
  ctx.font = "500 21px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText("数据为公开渠道聚合，仅供参考 · 投递前以企业官方公告为准", 60, 200);
  let y = HEAD_H;
  ctx.textBaseline = "middle";
  for (const c of list) {
    ctx.fillStyle = c.pinned ? "rgba(236,253,245,0.97)" : "rgba(255,255,255,0.93)";
    roundRect(ctx, 40, y, W - 80, ROW_H - 14, 14); ctx.fill();
    ctx.textAlign = "left";
    ctx.fillStyle = "#1e293b";
    ctx.font = "700 27px 'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.fillText(trunc(c.name, 13) + (c.pinned ? " 🏆" : ""), 66, y + 30);
    ctx.textAlign = "right";
    ctx.fillStyle = ["进行中", "常年招聘"].includes(c.status) ? "#10b981" : c.status === "即将截止" ? "#ef4444" : "#94a3b8";
    ctx.font = "600 20px 'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.fillText(c.status, W - 66, y + 30);
    ctx.textAlign = "left";
    ctx.fillStyle = "#64748b";
    ctx.font = "400 21px 'PingFang SC','Microsoft YaHei',sans-serif";
    const sal = c.salary_text ? " · 💰" + trunc(c.salary_text.split("，")[0].split("（")[0], 16) : "";
    ctx.fillText(`${trunc((c.cities || []).join("/"), 15)}${sal}`, 66, y + 62);
    ctx.textAlign = "right";
    ctx.fillStyle = c.deadline ? "#ef4444" : "#94a3b8";
    ctx.font = "400 19px 'PingFang SC','Microsoft YaHei',sans-serif";
    ctx.fillText(trunc(c.deadline ? "⏰截止 " + c.deadline : (c.deadline_note || "时间以官方为准"), 17), W - 66, y + 62);
    y += ROW_H;
  }
  ctx.textBaseline = "alphabetic";
  ctx.textAlign = "center";
  ctx.fillStyle = "#4f6ef7";
  ctx.font = "700 24px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText("⚡ 电气秋招整合站 · 电气工程及其自动化专用", W / 2, H - 58);
  ctx.fillStyle = "#64748b";
  ctx.font = "400 20px 'PingFang SC','Microsoft YaHei',sans-serif";
  ctx.fillText("含筛选 / 薪资结构 / 电气报考指南 / 一键直达官方投递入口", W / 2, H - 26);
  return cv;
}

async function exportShareImage() {
  const cv = buildShareCanvas();
  const blob = await new Promise(res => cv.toBlob(res, "image/png"));
  downloadBlob(blob, `电气秋招分享-${today()}.png`);
  toast("分享长图已生成 ✓ 在浏览器下载里，直接发到微信（图片形式好友打开最方便）", 3200);
}

async function buildOfflineHTML() {
  const [tpl, css, js] = await Promise.all([
    fetch("/static/index.html").then(r => r.text()),
    fetch("/static/style.css").then(r => r.text()),
    fetch("/static/app.js").then(r => r.text()),
  ]);
  const now = new Date();
  const pad = (n) => (n < 10 ? "0" + n : "" + n);
  const stamp = now.getFullYear() + "-" + pad(now.getMonth() + 1) + "-" + pad(now.getDate()) +
    " " + pad(now.getHours()) + ":" + pad(now.getMinutes());
  const payload = {
    generated: stamp,
    meta: { cats: META.cats, batches: META.batches, statuses: META.statuses,
            years: META.years, tags: META.tags, sorts: META.sorts },
    companies: COMPANIES,
  };
  const dataJs = "window.STATIC_DATA=" + JSON.stringify(payload).replace(/<\//g, () => "<\\/") + ";";
  // 内嵌的 js 源码里含 </script> 字面量，必须转义，否则导出页脚本块会被提前截断
  const escScript = (s) => s.replace(/<\/script>/gi, () => "<\\/script>");
  // 标签字面量用拼接构造：本文件被内嵌进导出页后，源码里不能残留完整标签
  const cssLink = "<" + "link rel=\"stylesheet\" href=\"/static/style.css\">";
  const jsTag = "<" + "script src=\"/static/app.js\">" + "</" + "script>";
  // 关键：替换串必须用「替换函数」形式！字符串替换会把 $$ 转成 $、$& 还原为匹配项，
  // 整份源码/JSON 作为替换串时会被静默改写（$$ 恰好是本文件的助手函数名，曾导致导出页 const 重复声明全站白屏）
  let html = tpl.replace(cssLink, () => "<style>\n" + css + "\n</" + "style>");
  const escJs = escScript(js);
  html = html.replace(jsTag, () =>
    "<scr" + "ipt>\n" + dataJs + "\n</scr" + "ipt>\n<scr" + "ipt>\n" + escJs + "\n</scr" + "ipt>");
  return { html: html, escJs: escJs };
}

function verifyOfflineHTML(html, escJs) {
  if (!html || !html.includes("window.STATIC_DATA=")) return "数据块缺失";
  if (html.includes("<" + "script src=")) return "外链脚本未替换干净（file:// 下无法加载，页面必然无功能）";
  const closers = html.match(/<\/script>/g) || [];
  if (closers.length !== 2) return "脚本块数量异常（" + closers.length + "，应为 2）";
  // 内嵌前先做语法编译自检：能拦住 $$ 转义之类的静默改写（曾致 const 重复声明 SyntaxError）
  try { new Function(escJs); } catch (e) { return "内嵌脚本语法校验失败：" + e.message; }
  return null;
}

async function exportOfflineHTML() {
  toast("正在打包离线网页（含全部企业数据）…");
  const built = await buildOfflineHTML();
  const err = verifyOfflineHTML(built.html, built.escJs);
  if (err) {
    toast("⚠️ 导出自检未通过：" + err + "。请刷新页面后重试；仍失败请看浏览器控制台。", 5000);
    console.error("[离线导出自检]", err);
    return;
  }
  downloadBlob(new Blob([built.html], { type: "text/html;charset=utf-8" }), `电气秋招整合站-离线完整版-${today()}.html`);
  toast("离线网页已生成 ✓ 以「文件」形式发到微信，好友点开选浏览器打开即可", 3600);
}

// ---------------- 视图切换 ----------------
function switchView(view) {
  $$(".nav-tab").forEach(t => t.classList.toggle("active", t.dataset.view === view));
  $("#view-jobs").style.display = view === "jobs" ? "" : "none";
  $("#view-timeline").style.display = view === "timeline" ? "" : "none";
  $("#view-guide").style.display = view === "guide" ? "" : "none";
  if (view === "timeline") renderTimeline();
  if (view === "guide") renderGuide();
  if (view === "jobs") renderList();
  location.hash = "#/" + view;
}

// ---------------- 弹窗控制 ----------------
function openModal(id) { document.getElementById(id).classList.add("open"); }
function closeModal(id) { document.getElementById(id).classList.remove("open"); }

// ---------------- 主题 ----------------
// 手机文件预览/微信内置查看器里 localStorage 会抛 SecurityError，必须保护
function storeGet(key) {
  try { return window.localStorage.getItem(key); } catch (e) { return null; }
}
function storeSet(key, val) {
  try { window.localStorage.setItem(key, val); } catch (e) { /* 无痕/受限环境忽略 */ }
}

function initTheme() {
  const saved = storeGet("theme") || "light";
  document.documentElement.dataset.theme = saved;
  $("#btn-theme").textContent = saved === "dark" ? "☀️" : "🌙";
  $("#btn-theme").onclick = () => {
    const cur = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = cur;
    storeSet("theme", cur);
    $("#btn-theme").textContent = cur === "dark" ? "☀️" : "🌙";
  };
}

// ---------------- 初始化 ----------------
async function init() {
  initTheme();
  await loadData();
  buildFilters();
  bindFilterControls();
  renderList();

  $$(".nav-tab").forEach(t => t.onclick = () => switchView(t.dataset.view));
  const hash = location.hash.replace("#/", "");
  if (["jobs", "timeline", "guide"].includes(hash)) switchView(hash);

  $("#btn-refresh").onclick = startRefresh;
  $("#btn-inbox").onclick = openInbox;
  $("#btn-digest").onclick = openDigest;
  $("#btn-search").onclick = openSearch;
  $("#btn-linkcheck").onclick = openLinkcheck;
  $("#btn-share").onclick = openShareModal;
  $("#btn-share-img").onclick = exportShareImage;
  $("#btn-share-html").onclick = exportOfflineHTML;
  $$(".modal-mask").forEach(m => {
    m.addEventListener("click", (e) => { if (e.target === m) m.classList.remove("open"); });
    m.querySelectorAll("[data-close]").forEach(b => b.onclick = () => m.classList.remove("open"));
  });
  window.addEventListener("hashchange", () => {
    const v = location.hash.replace("#/", "");
    if (["jobs", "timeline", "guide"].includes(v)) switchView(v);
  });
}

init().catch(err => {
  document.body.insertAdjacentHTML("beforeend",
    `<div style="position:fixed;inset:0;background:#fff;z-index:999;display:flex;align-items:center;justify-content:center;color:#ef4444;font-size:15px">加载失败：${esc(err.message)}（请确认后端已启动）</div>`);
});
