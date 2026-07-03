import json
from datetime import datetime
from pathlib import Path


DATA_DIR = Path("site")
TEMPLATE = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>贝尔格莱德房源监控</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4"></script>
<style>
:root {
  --bg: #f5f5f5;
  --card: #fff;
  --primary: #2563eb;
  --new: #ea580c;
  --4zida: #2563eb;
  --halo: #16a34a;
  --kp: #ea580c;
  --nekretnine: #8b5cf6;
  --cityexpert: #ea580c;
  --star: #f59e0b;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: #333; }
.container { max-width: 960px; margin: 0 auto; padding: 16px; }
header { background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 24px 16px; text-align: center; }
header h1 { font-size: 1.5rem; margin-bottom: 8px; }
header .stats { font-size: 0.9rem; opacity: 0.9; }
header .stats span { margin: 0 8px; }

.source-stats { display: flex; gap: 8px; flex-wrap: wrap; padding: 10px 0; }
.source-stat { padding: 6px 14px; border-radius: 20px; font-size: 0.8rem; color: white; display: flex; align-items: center; gap: 6px; }
.source-stat .num { font-weight: 700; font-size: 1rem; }

.filters { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 0; }
.filters select, .filters input { padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 0.9rem; }

.listings { display: grid; gap: 12px; }
.card { background: var(--card); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; gap: 12px; position: relative; }
.card.watched { box-shadow: 0 0 0 2px var(--star); }
.card img { width: 120px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #eee; }
.card-body { flex: 1; min-width: 0; }
.card-body h3 { font-size: 1rem; margin-bottom: 4px; padding-right: 24px; }
.price { font-size: 1.4rem; font-weight: 700; color: var(--primary); }
.details { font-size: 0.85rem; color: #666; margin: 4px 0; }
.source-tag { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: white; }
.tag-new { background: var(--new); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
.url-link { display: inline-block; margin-top: 4px; font-size: 0.8rem; color: var(--primary); text-decoration: none; }
.url-link:hover { text-decoration: underline; }
.empty { text-align: center; padding: 48px; color: #999; }

.star-btn { position: absolute; top: 8px; right: 8px; background: none; border: none; font-size: 1.3rem; cursor: pointer; color: #ccc; padding: 2px 6px; line-height: 1; border-radius: 4px; z-index: 1; }
.star-btn:hover { background: #f0f0f0; }
.star-btn.active { color: var(--star); }

.price-change { font-size: 0.8rem; margin-top: 2px; }
.price-change.up { color: #ef4444; }
.price-change.down { color: #16a34a; }
.price-change.flat { color: #999; }

.chart-wrapper { margin-top: 10px; border-top: 1px solid #eee; padding-top: 10px; }
.chart-wrapper canvas { max-height: 100px; }

.first-seen-date { font-size: 0.75rem; color: #999; margin-top: 2px; }

@media (max-width: 600px) {
  .card { flex-direction: column; }
  .card img { width: 100%; height: 160px; }
}
</style>
</head>
<body>
<header>
  <h1>🏠 贝尔格莱德房源监控</h1>
  <div class="stats">
    <span>更新: {update_time}</span>
    <span>总房源: <strong id="totalCount">{total}</strong></span>
    <span>今日新增: <strong style="color:#fde047;" id="newToday">{new_today}</strong></span>
  </div>
</header>

<div class="container">
<div id="sourceStats" class="source-stats"></div>

<div class="filters">
  <select id="sourceFilter" onchange="applyFilters()">
    <option value="all">所有来源</option>
    <option value="4zida">4zida.rs</option>
    <option value="halo_oglasi">Halo Oglasi</option>
    <option value="kupujemprodajem">KupujemProdajem</option>
    <option value="nekretnine">Nekretnine.rs</option>
    <option value="cityexpert">Cityexpert</option>
  </select>
  <select id="daysFilter" onchange="applyFilters()">
    <option value="0">所有时间</option>
    <option value="1">1天内</option>
    <option value="3">3天内</option>
    <option value="5">5天内</option>
    <option value="7">7天内</option>
    <option value="14">14天内</option>
    <option value="30">30天内</option>
  </select>
  <select id="watchFilter" onchange="applyFilters()">
    <option value="all">所有房源</option>
    <option value="watched">已关注</option>
  </select>
  <input type="number" id="minPrice" placeholder="最低价 €" oninput="applyFilters()" style="width:100px">
  <input type="number" id="maxPrice" placeholder="最高价 €" oninput="applyFilters()" style="width:100px">
  <input type="number" id="minArea" placeholder="最小面积 m²" oninput="applyFilters()" style="width:110px">
</div>

<div class="listings" id="listings"></div>
</div>

<script>
const DATA = {data_json};

const SOURCE_CONFIG = {
  '4zida': { label: '4zida.rs', color: 'var(--4zida)', short: '4zida' },
  'halo_oglasi': { label: 'Halo Oglasi', color: 'var(--halo)', short: 'Halo' },
  'kupujemprodajem': { label: 'KupujemProdajem', color: 'var(--kp)', short: 'KP' },
  'nekretnine': { label: 'Nekretnine.rs', color: 'var(--nekretnine)', short: 'Nekretnine' },
  'cityexpert': { label: 'Cityexpert', color: 'var(--cityexpert)', short: 'Cityexpert' },
};

const WATCH_KEY = 'serbia_watchlist';

function getWatchlist() {
  try { return JSON.parse(localStorage.getItem(WATCH_KEY) || '[]'); } catch { return []; }
}
function saveWatchlist(list) {
  localStorage.setItem(WATCH_KEY, JSON.stringify(list));
}
function toggleWatch(id) {
  let w = getWatchlist();
  if (w.includes(id)) { w = w.filter(x => x !== id); }
  else { w.push(id); }
  saveWatchlist(w);
  applyFilters();
}

function daysAgo(N) {
  const d = new Date();
  d.setDate(d.getDate() - N);
  return d.toISOString().slice(0, 10);
}

function updateStats(filtered) {
  const today = new Date().toISOString().slice(0, 10);
  document.getElementById('totalCount').textContent = filtered.length;
  document.getElementById('newToday').textContent = filtered.filter(d => d.first_seen === today).length;

  // Per-source breakdown (always based on full filtered set)
  const container = document.getElementById('sourceStats');
  const counts = {};
  filtered.forEach(d => {
    const s = d.source || 'unknown';
    counts[s] = (counts[s] || 0) + 1;
  });
  container.innerHTML = Object.entries(SOURCE_CONFIG)
    .filter(([key]) => counts[key])
    .map(([key, cfg]) => {
      const count = counts[key] || 0;
      return `<div class="source-stat" style="background:${cfg.color}"><span class="num">${count}</span>${cfg.short}</div>`;
    }).join('');
}

function renderCharts() {
  const watched = getWatchlist();
  watched.forEach(id => {
    const canvas = document.getElementById('chart-' + id);
    if (!canvas) return;
    const d = DATA.find(x => x.id === id);
    if (!d || !d.price_history || d.price_history.length < 2) return;

    new Chart(canvas, {
      type: 'line',
      data: {
        labels: d.price_history.map(p => p.date.slice(5)),
        datasets: [{
          data: d.price_history.map(p => p.price),
          borderColor: '#2563eb',
          backgroundColor: 'rgba(37,99,235,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#2563eb',
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { font: { size: 9 } }, grid: { display: false } },
          y: { ticks: { font: { size: 9 }, callback: v => '€' + v.toLocaleString() }, grid: { color: '#eee' } }
        },
      }
    });
  });
}

function applyFilters() {
  const src = document.getElementById('sourceFilter').value;
  const days = parseInt(document.getElementById('daysFilter').value) || 0;
  const watchFilter = document.getElementById('watchFilter').value;
  const minP = parseFloat(document.getElementById('minPrice').value) || 0;
  const maxP = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minA = parseFloat(document.getElementById('minArea').value) || 0;
  const watchedList = getWatchlist();

  const today = new Date().toISOString().slice(0, 10);
  const cutoff = days > 0 ? daysAgo(days) : '';

  let filtered = DATA.filter(d => {
    if (src !== 'all' && d.source !== src) return false;
    if (d.price_eur < minP || d.price_eur > maxP) return false;
    if ((d.area_sqm || 0) < minA) return false;
    if (cutoff && d.first_seen < cutoff) return false;
    return true;
  });

  // Sort: watched first, then by price
  filtered.sort((a, b) => {
    const aW = watchedList.includes(a.id) ? 0 : 1;
    const bW = watchedList.includes(b.id) ? 0 : 1;
    if (aW !== bW) return aW - bW;
    return a.price_eur - b.price_eur;
  });

  // Apply watch-filter AFTER sorting (so we show all as base for stats)
  let displayData = filtered;
  if (watchFilter === 'watched') {
    displayData = filtered.filter(d => watchedList.includes(d.id));
  }

  // Update stats based on pre-watch-filter set
  updateStats(filtered);

  const container = document.getElementById('listings');
  if (!displayData.length) {
    container.innerHTML = '<div class="empty">没有符合条件的房源</div>';
    return;
  }

  container.innerHTML = displayData.map(d => {
    const isNew = d.first_seen === today;
    const isWatched = watchedList.includes(d.id);

    // Price change indicator
    let priceChangeHtml = '';
    if (d.price_history && d.price_history.length >= 2) {
      const first = d.price_history[0].price;
      const last = d.price_history[d.price_history.length - 1].price;
      const diff = last - first;
      const pct = ((diff / first) * 100).toFixed(1);
      if (Math.abs(diff) > 0.01) {
        const cls = diff < 0 ? 'down' : 'up';
        const arrow = diff < 0 ? '↓' : '↑';
        priceChangeHtml = `<div class="price-change ${cls}">${arrow} €${Math.abs(diff).toLocaleString()} (${pct}%)</div>`;
      } else {
        priceChangeHtml = `<div class="price-change flat">价格未变</div>`;
      }
    }

    // Chart placeholder for watched items
    let chartHtml = '';
    if (isWatched && d.price_history && d.price_history.length >= 2) {
      chartHtml = `<div class="chart-wrapper"><canvas id="chart-${d.id}" style="height:80px"></canvas></div>`;
    }

    return `<div class="card${isWatched ? ' watched' : ''}">
      <button class="star-btn${isWatched ? ' active' : ''}" onclick="toggleWatch('${d.id}')" title="${isWatched ? '取消关注' : '关注'}">${isWatched ? '★' : '☆'}</button>
      <img src="${d.image_url || ''}" alt="" onerror="this.style.display='none'">
      <div class="card-body">
        <h3>${d.title}</h3>
        <div class="price">€${d.price_eur.toLocaleString()} ${d.area_sqm ? `· ${d.area_sqm} m²` : ''} ${d.rooms ? `· ${d.rooms}` : ''}</div>
        ${priceChangeHtml}
        <div class="details">${d.location} <span class="source-tag" style="background:${sourceColor(d.source)}">${sourceName(d.source)}</span> ${isNew ? '<span class="tag-new">今日新增</span>' : ''}</div>
        <div class="first-seen-date">收录于 ${d.first_seen}</div>
        <a class="url-link" href="${d.url}" target="_blank" rel="noopener">查看原网页 →</a>
        ${chartHtml}
      </div>
    </div>`;
  }).join('');

  // Render charts in next tick (after DOM update)
  setTimeout(renderCharts, 50);
}

function sourceColor(s) {
  return SOURCE_CONFIG[s]?.color || 'var(--kp)';
}
function sourceName(s) {
  return SOURCE_CONFIG[s]?.short || 'KP';
}

applyFilters();
</script>
</body>
</html>"""


def generate_site(data: dict):
    today = datetime.now().strftime("%Y-%m-%d")
    listings = data.get("listings", [])
    new_today = sum(1 for l in listings if l.get("first_seen") == today)

    html = TEMPLATE
    html = html.replace("{update_time}", datetime.now().strftime("%Y-%m-%d %H:%M"))
    html = html.replace("{total}", str(len(listings)))
    html = html.replace("{new_today}", str(new_today))
    html = html.replace("{data_json}", json.dumps(listings, ensure_ascii=False))

    with open(DATA_DIR / "index.html", "w") as f:
        f.write(html)
    print(f"Site generated: {len(listings)} listings, {new_today} new today")


if __name__ == "__main__":
    with open(DATA_DIR / "listings.json") as f:
        data = json.load(f)
    generate_site(data)
