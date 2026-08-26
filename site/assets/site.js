// Velencei-tó vízmérleg — chart panels, adattár browser, forrás coverage matrix.
// Loaded on every page; each section below is a no-op if its markers aren't in the DOM.

const DATA_VERSION = window.DATA_VERSION || "";
const PALETTE = ["#3366cc", "#dc3912", "#ff9900", "#109618", "#990099", "#0099c6", "#dd4477", "#66aa00"];

const chartJsonCache = new Map();
function fetchChartJson(chartId) {
  if (!chartJsonCache.has(chartId)) {
    chartJsonCache.set(chartId, fetch(`./data/charts/${chartId}.json?v=${encodeURIComponent(DATA_VERSION)}`).then((r) => r.json()));
  }
  return chartJsonCache.get(chartId);
}

function findPanel(payload, panelKey) {
  if (!payload.panels || payload.panels.length === 0) return null;
  if (!panelKey) return payload.panels[0];
  return payload.panels.find((p) => p.key === panelKey) || payload.panels[0];
}

function yearOf(label, panel) {
  if (panel && panel.label_epoch) {
    return dateFromOffset(panel.label_epoch, label).getUTCFullYear();
  }
  const m = String(label).match(/^-?\d{4}/);
  return m ? parseInt(m[0], 10) : null;
}

function dateFromOffset(epoch, offsetDays) {
  const d = new Date(epoch + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + Number(offsetDays));
  return d;
}

function formatLabel(label, panel) {
  if (panel && panel.label_epoch) {
    return dateFromOffset(panel.label_epoch, label).toISOString().slice(0, 10);
  }
  return String(label);
}

function colorFor(i) {
  return PALETTE[i % PALETTE.length];
}

// --- Chart.js construction per panel type -----------------------------

function buildChartConfig(panel) {
  if (panel.type === "bar" || panel.type === "line") {
    const datasets = panel.datasets.map((ds, i) => ({
      label: ds.label,
      data: ds.data,
      type: ds.type || panel.type,
      backgroundColor: ds.highlight ? "#dc3912" : colorFor(i) + (panel.type === "bar" ? "88" : ""),
      borderColor: ds.highlight ? "#dc3912" : colorFor(i),
      borderWidth: ds.type === "line" || panel.type === "line" ? 2 : 1,
      borderDash: ds.dashed ? [5, 4] : undefined,
      pointRadius: ds.point_radius !== undefined ? ds.point_radius : (panel.type === "line" ? 2 : 0),
      fill: !!ds.fill,
      yAxisID: ds.y_axis === "secondary" ? "y1" : "y",
      stack: panel.stacked ? "stack0" : undefined,
    }));
    const hasSecondary = panel.datasets.some((d) => d.y_axis === "secondary");
    const scales = {
      x: { stacked: !!panel.stacked, ticks: { autoSkip: true, maxTicksLimit: 24 } },
      y: { stacked: !!panel.stacked, title: { display: !!panel.y_label, text: panel.y_label || "" } },
    };
    if (hasSecondary) {
      scales.y1 = { position: "right", grid: { drawOnChartArea: false }, title: { display: true, text: "" } };
    }
    if (panel.band) {
      // rendered via annotation-free shading is out of scope without a plugin; note the band in text instead.
    }
    if (panel.label_epoch) {
      scales.x.ticks.callback = function (value) {
        return formatLabel(this.getLabelForValue(value), panel);
      };
    }
    const tooltipCallbacks = panel.label_epoch
      ? { callbacks: { title: (items) => (items.length ? formatLabel(items[0].label, panel) : "") } }
      : {};
    return {
      type: panel.type,
      data: { labels: panel.labels, datasets },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "top" }, title: { display: false }, tooltip: tooltipCallbacks },
        scales,
      },
    };
  }
  if (panel.type === "warming_stripes") {
    const tempDs = panel.datasets.find((d) => d.type === "line");
    const stripeDs = panel.datasets.find((d) => d.type === "stripes");
    const maxAbs = Math.max(...stripeDs.data.filter((v) => v !== null).map(Math.abs), 0.1);
    const stripeColors = stripeDs.data.map((v) => diverging(v, maxAbs));
    return {
      type: "bar",
      data: {
        labels: panel.labels,
        datasets: [
          {
            label: stripeDs.label,
            data: panel.labels.map(() => 1),
            backgroundColor: stripeColors,
            yAxisID: "y1",
            barPercentage: 1.0,
            categoryPercentage: 1.0,
            order: 2,
          },
          {
            label: tempDs.label,
            data: tempDs.data,
            type: "line",
            borderColor: "#212529",
            backgroundColor: "transparent",
            borderWidth: 2,
            pointRadius: 0,
            yAxisID: "y",
            order: 1,
          },
        ],
      },
      options: {
        responsive: true,
        interaction: { mode: "index", intersect: false },
        plugins: { legend: { position: "top" } },
        scales: {
          x: { ticks: { autoSkip: true, maxTicksLimit: 24 } },
          y: { position: "left", title: { display: true, text: panel.y_label || "" } },
          y1: { display: false, min: 0, max: 1 },
        },
      },
    };
  }
  return null;
}

function diverging(value, maxAbs) {
  if (value === null || value === undefined) return "#e9ecef";
  const t = Math.max(-1, Math.min(1, value / maxAbs));
  if (t >= 0) {
    const g = Math.round(255 - t * 155);
    return `rgb(220,${g},${g})`;
  }
  const g = Math.round(255 + t * 155);
  return `rgb(${g},${g},255)`;
}

function renderHeatmap(container, panel) {
  const maxAbs = Math.max(
    ...panel.matrix.flat().filter((v) => v !== null).map(Math.abs),
    0.1
  );
  const monthNames = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII"];
  let html = '<div class="table-responsive"><table class="table table-sm table-bordered heatmap"><thead><tr><th></th>';
  monthNames.forEach((m) => (html += `<th>${m}</th>`));
  html += "</tr></thead><tbody>";
  panel.years.forEach((year, ri) => {
    html += `<tr><th>${year}</th>`;
    panel.matrix[ri].forEach((v) => {
      const bg = diverging(v, maxAbs);
      const title = v === null ? "nincs adat" : v.toFixed(1);
      html += `<td style="background:${bg}" title="${title}"></td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table></div>";
  html += `<p class="text-muted small">Kék: az alapidőszak (${panel.baseline_years[0]}-${panel.baseline_years[1]}) átlaga alatt. Piros: felette.</p>`;
  container.innerHTML = html;
}

// --- Controls: year range + series toggles -----------------------------

function attachControls(panelEl, chart, panel) {
  const fullLabels = panel.labels.slice();
  const fullData = panel.datasets.map((d) => d.data.slice());
  const years = fullLabels.map((l) => yearOf(l, panel)).filter((y) => y !== null);
  if (years.length < 2) return;
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);

  const wrap = document.createElement("div");
  wrap.className = "chart-controls";
  wrap.innerHTML = `
    <button class="btn btn-sm btn-outline-secondary mb-2" type="button" data-bs-toggle="collapse" data-bs-target="#ctrl-${chart.id}">Beállítások</button>
    <div class="collapse" id="ctrl-${chart.id}">
      <div class="row g-2 align-items-center mb-2">
        <div class="col-auto"><label class="form-label small mb-0">Évtől</label>
          <input type="range" class="form-range yr-from" min="${minYear}" max="${maxYear}" value="${minYear}"></div>
        <div class="col-auto"><label class="form-label small mb-0">Évig</label>
          <input type="range" class="form-range yr-to" min="${minYear}" max="${maxYear}" value="${maxYear}"></div>
        <div class="col-auto"><span class="badge text-bg-light yr-label">${minYear}-${maxYear}</span></div>
      </div>
      <div class="series-toggles small"></div>
    </div>`;
  panelEl.insertBefore(wrap, panelEl.querySelector("canvas"));

  const toggles = wrap.querySelector(".series-toggles");
  panel.datasets.forEach((ds, i) => {
    const id = `tgl-${chart.id}-${i}`;
    const label = document.createElement("label");
    label.className = "form-check form-check-inline";
    label.innerHTML = `<input class="form-check-input" type="checkbox" id="${id}" checked> ${ds.label}`;
    toggles.appendChild(label);
    label.querySelector("input").addEventListener("change", (e) => {
      chart.getDatasetMeta(i).hidden = !e.target.checked;
      chart.update();
    });
  });

  function apply() {
    const from = parseInt(wrap.querySelector(".yr-from").value, 10);
    const to = parseInt(wrap.querySelector(".yr-to").value, 10);
    wrap.querySelector(".yr-label").textContent = `${from}-${to}`;
    const idx = fullLabels.map((l, i) => ({ y: yearOf(l, panel), i })).filter((o) => o.y !== null && o.y >= from && o.y <= to).map((o) => o.i);
    chart.data.labels = idx.map((i) => fullLabels[i]);
    chart.data.datasets.forEach((ds, di) => {
      ds.data = idx.map((i) => fullData[di][i]);
    });
    chart.update();
  }
  wrap.querySelector(".yr-from").addEventListener("input", apply);
  wrap.querySelector(".yr-to").addEventListener("input", apply);
}

// --- Panel hydration -----------------------------------------------------

function hydratePanel(panelEl) {
  const chartId = panelEl.dataset.chart;
  const panelKey = panelEl.dataset.panel;
  const withControls = panelEl.dataset.controls === "true";
  fetchChartJson(chartId).then((payload) => {
    const panel = findPanel(payload, panelKey);
    if (!panel) return;
    const noteEl = panelEl.querySelector(".chart-note");
    if (noteEl) {
      const notes = (payload.notes || []).map((n) => n.display_hu).join(" ");
      const bandNote = panel.band ? ` Sáv: ${panel.band.label} (${panel.band.low}-${panel.band.high}).` : "";
      noteEl.textContent = `Forrás: ${payload.source}.${notes ? " " + notes : ""}${bandNote}`;
    }
    if (panel.type === "heatmap") {
      const canvas = panelEl.querySelector("canvas");
      const holder = document.createElement("div");
      canvas.replaceWith(holder);
      renderHeatmap(holder, panel);
      return;
    }
    const config = buildChartConfig(panel);
    if (!config) return;
    const canvas = panelEl.querySelector("canvas");
    canvas.id = canvas.id || `chart-${chartId}-${panelKey || "main"}`;
    const chart = new Chart(canvas.getContext("2d"), config);
    if (withControls) attachControls(panelEl, chart, panel);
  }).finally(() => {
    panelEl.dataset.hydrated = "true";
  });
}

function initChartPanels() {
  const panels = document.querySelectorAll(".chart-panel");
  if (panels.length === 0) return;
  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          hydratePanel(entry.target);
          io.unobserve(entry.target);
        }
      });
    },
    { rootMargin: "200px" }
  );
  panels.forEach((p) => io.observe(p));
}

// --- Adattár: table browser ----------------------------------------------

const ADATTAR_TABLES = [
  "documents", "stations", "station_metadata_history", "monthly_balance",
  "monthly_station_obs", "evaporation_inputs", "daily_obs",
  "daily_station_extremes", "expedition_flows", "annual_climate_summary",
  "historical_monthly", "release_events",
];

const adattarCache = new Map();
const adattarState = { table: null, filter: "", sortCol: null, sortDir: 1, page: 0 };

function initAdattar() {
  const tabsEl = document.getElementById("tableTabs");
  const contentEl = document.getElementById("tableTabContent");
  if (!tabsEl || !contentEl) return;

  ADATTAR_TABLES.forEach((table, i) => {
    const li = document.createElement("li");
    li.className = "nav-item";
    li.innerHTML = `<button class="nav-link${i === 0 ? " active" : ""}" data-table="${table}" type="button">${table}</button>`;
    tabsEl.appendChild(li);
    li.querySelector("button").addEventListener("click", (e) => {
      tabsEl.querySelectorAll(".nav-link").forEach((b) => b.classList.remove("active"));
      e.target.classList.add("active");
      openTable(table, contentEl);
    });
  });
  openTable(ADATTAR_TABLES[0], contentEl);
}

function openTable(table, contentEl) {
  adattarState.table = table;
  adattarState.filter = "";
  adattarState.sortCol = null;
  adattarState.page = 0;
  contentEl.innerHTML = '<p class="text-muted">Betöltés...</p>';
  loadTable(table).then((rows) => renderAdattar(contentEl, rows));
}

function loadTable(table) {
  if (!adattarCache.has(table)) {
    adattarCache.set(
      table,
      fetch(`./data/tables/${table}.json?v=${encodeURIComponent(DATA_VERSION)}`).then((r) => r.json()).then((j) => j.rows)
    );
  }
  return adattarCache.get(table);
}

function renderAdattar(contentEl, rows) {
  const cols = rows.length ? Object.keys(rows[0]) : [];
  contentEl.innerHTML = `
    <input type="text" class="form-control form-control-sm mb-2 adattar-filter" placeholder="Szűrés (bármely oszlop)...">
    <div class="table-responsive"><table class="table table-sm table-striped" id="adattarTable">
      <thead><tr>${cols.map((c) => `<th data-col="${c}" role="button">${c}</th>`).join("")}</tr></thead>
      <tbody></tbody>
    </table></div>
    <nav class="d-flex justify-content-between align-items-center">
      <button class="btn btn-sm btn-outline-secondary adattar-prev">&larr; Előző</button>
      <span class="small adattar-pageinfo"></span>
      <button class="btn btn-sm btn-outline-secondary adattar-next">Következő &rarr;</button>
    </nav>`;

  contentEl.querySelector(".adattar-filter").addEventListener("input", (e) => {
    adattarState.filter = e.target.value.toLowerCase();
    adattarState.page = 0;
    paintAdattar(contentEl, rows, cols);
  });
  contentEl.querySelectorAll("th[data-col]").forEach((th) => {
    th.addEventListener("click", () => {
      const col = th.dataset.col;
      if (adattarState.sortCol === col) adattarState.sortDir *= -1;
      else {
        adattarState.sortCol = col;
        adattarState.sortDir = 1;
      }
      paintAdattar(contentEl, rows, cols);
    });
  });
  contentEl.querySelector(".adattar-prev").addEventListener("click", () => {
    if (adattarState.page > 0) {
      adattarState.page -= 1;
      paintAdattar(contentEl, rows, cols);
    }
  });
  contentEl.querySelector(".adattar-next").addEventListener("click", () => {
    adattarState.page += 1;
    paintAdattar(contentEl, rows, cols);
  });

  paintAdattar(contentEl, rows, cols);
}

function paintAdattar(contentEl, rows, cols) {
  const PAGE_SIZE = 50;
  let filtered = rows;
  if (adattarState.filter) {
    filtered = rows.filter((r) => cols.some((c) => String(r[c] ?? "").toLowerCase().includes(adattarState.filter)));
  }
  if (adattarState.sortCol) {
    const col = adattarState.sortCol;
    const dir = adattarState.sortDir;
    filtered = filtered.slice().sort((a, b) => {
      const av = a[col], bv = b[col];
      if (av === bv) return 0;
      if (av === null || av === undefined) return 1;
      if (bv === null || bv === undefined) return -1;
      return av > bv ? dir : -dir;
    });
  }
  const maxPage = Math.max(0, Math.ceil(filtered.length / PAGE_SIZE) - 1);
  adattarState.page = Math.min(adattarState.page, maxPage);
  const pageRows = filtered.slice(adattarState.page * PAGE_SIZE, (adattarState.page + 1) * PAGE_SIZE);
  const tbody = contentEl.querySelector("tbody");
  tbody.innerHTML = pageRows.map((r) => `<tr>${cols.map((c) => `<td>${r[c] ?? ""}</td>`).join("")}</tr>`).join("");
  contentEl.querySelector(".adattar-pageinfo").textContent = `${filtered.length} sor · ${adattarState.page + 1}/${maxPage + 1}. oldal`;
}

// --- Forrás: coverage matrix ----------------------------------------------

function initCoverage() {
  const el = document.getElementById("coverage-matrix");
  if (!el) return;
  fetch(`./data/coverage.json?v=${encodeURIComponent(DATA_VERSION)}`)
    .then((r) => r.json())
    .then((cov) => renderCoverage(el, cov));
}

function renderCoverage(el, cov) {
  let html = '<table class="table table-bordered"><thead><tr><th>Tábla</th>';
  cov.years.forEach((y) => (html += `<th>${y}</th>`));
  html += "</tr></thead><tbody>";
  cov.tables.forEach((table) => {
    html += `<tr><th>${table}</th>`;
    cov.years.forEach((y) => {
      const cell = cov.matrix[table][String(y)] || { status: "absent" };
      html += `<td class="cov-cell coverage-${cell.status}" title="${cell.status} (${cell.rows_in_db} sor)"></td>`;
    });
    html += "</tr>";
  });
  html += "</tbody></table>";
  el.innerHTML = html;
}

// --- Boot ------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initChartPanels();
  initAdattar();
  initCoverage();
});
