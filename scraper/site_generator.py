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
<style>
:root {{
  --bg: #f5f5f5;
  --card: #fff;
  --primary: #2563eb;
  --new: #ea580c;
  --4zida: #2563eb;
  --halo: #16a34a;
  --kp: #ea580c;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: #333; }}
.container {{ max-width: 960px; margin: 0 auto; padding: 16px; }}
header {{ background: linear-gradient(135deg, #1e40af, #3b82f6); color: white; padding: 24px 16px; text-align: center; }}
header h1 {{ font-size: 1.5rem; margin-bottom: 8px; }}
header .stats {{ font-size: 0.9rem; opacity: 0.9; }}
header .stats span {{ margin: 0 8px; }}
.filters {{ display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 0; }}
.filters select, .filters input {{ padding: 8px 12px; border: 1px solid #ddd; border-radius: 8px; font-size: 0.9rem; }}
.listings {{ display: grid; gap: 12px; }}
.card {{ background: var(--card); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); display: flex; gap: 12px; position: relative; }}
.card img {{ width: 120px; height: 90px; object-fit: cover; border-radius: 8px; flex-shrink: 0; background: #eee; }}
.card-body {{ flex: 1; min-width: 0; }}
.card-body h3 {{ font-size: 1rem; margin-bottom: 4px; }}
.price {{ font-size: 1.4rem; font-weight: 700; color: var(--primary); }}
.details {{ font-size: 0.85rem; color: #666; margin: 4px 0; }}
.source-tag {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; color: white; }}
.tag-new {{ background: var(--new); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }}
.url-link {{ display: inline-block; margin-top: 4px; font-size: 0.8rem; color: var(--primary); text-decoration: none; }}
.url-link:hover {{ text-decoration: underline; }}
.empty {{ text-align: center; padding: 48px; color: #999; }}
@media (max-width: 600px) {{
  .card {{ flex-direction: column; }}
  .card img {{ width: 100%; height: 160px; }}
}}
</style>
</head>
<body>
<header>
  <h1>🏠 贝尔格莱德房源监控</h1>
  <div class="stats">
    <span>更新: {update_time}</span>
    <span>总房源: {total}</span>
    <span>今日新增: <strong style="color:#fde047;">{new_today}</strong></span>
  </div>
</header>
<div class="container">
<div class="filters">
  <select id="sourceFilter" onchange="applyFilters()">
    <option value="all">所有来源</option>
    <option value="4zida">4zida.rs</option>
    <option value="halo_oglasi">Halo Oglasi</option>
    <option value="kupujemprodajem">KupujemProdajem</option>
    <option value="cityexpert">Cityexpert</option>
  </select>
  <input type="number" id="minPrice" placeholder="最低价 €" oninput="applyFilters()" style="width:100px">
  <input type="number" id="maxPrice" placeholder="最高价 €" oninput="applyFilters()" style="width:100px">
  <input type="number" id="minArea" placeholder="最小面积 m²" oninput="applyFilters()" style="width:110px">
</div>
<div class="listings" id="listings"></div>
</div>
<script>
const DATA = {data_json};

function sourceColor(s) {{
  if (s === '4zida') return 'var(--4zida)';
  if (s === 'halo_oglasi') return 'var(--halo)';
  if (s === 'cityexpert') return 'var(--kp)';
  return 'var(--kp)';
}}
function sourceName(s) {{
  if (s === '4zida') return '4zida';
  if (s === 'halo_oglasi') return 'Halo';
  if (s === 'cityexpert') return 'Cityexpert';
  return 'KP';
}}

function applyFilters() {{
  const src = document.getElementById('sourceFilter').value;
  const minP = parseFloat(document.getElementById('minPrice').value) || 0;
  const maxP = parseFloat(document.getElementById('maxPrice').value) || Infinity;
  const minA = parseFloat(document.getElementById('minArea').value) || 0;

  const today = new Date().toISOString().slice(0, 10);
  const filtered = DATA.filter(d => {{
    if (src !== 'all' && d.source !== src) return false;
    if (d.price_eur < minP || d.price_eur > maxP) return false;
    if ((d.area_sqm || 0) < minA) return false;
    return true;
  }});

  const container = document.getElementById('listings');
  if (!filtered.length) {{
    container.innerHTML = '<div class="empty">没有符合条件的房源</div>';
    return;
  }}
  container.innerHTML = filtered.map(d => {{
    const isNew = d.first_seen === today;
    return `<div class="card">
      <img src="${d.image_url || ''}" alt="" onerror="this.style.display='none'">
      <div class="card-body">
        <h3>${d.title}</h3>
        <div class="price">€${d.price_eur.toLocaleString()} ${d.area_sqm ? `· ${d.area_sqm} m²` : ''} ${d.rooms ? `· ${d.rooms}` : ''}</div>
        <div class="details">${d.location} <span class="source-tag" style="background:${sourceColor(d.source)}">${sourceName(d.source)}</span> ${isNew ? '<span class="tag-new">今日新增</span>' : ''}</div>
        <a class="url-link" href="${d.url}" target="_blank" rel="noopener">查看原网页 →</a>
      </div>
    </div>`;
  }}).join('');
}}

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
