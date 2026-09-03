"""data/latest.json 을 docs/index.html 정적 페이지로 렌더링한다."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent

TEMPLATE = """<!doctype html>
<html lang="ko" data-theme="auto">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>세무 뉴스 브리핑</title>
<meta name="description" content="국세청·기재부 보도자료, 세무 전문지, 판례를 매일 자동 수집한 세무 뉴스 브리핑">
<style>
:root {
  --bg:#f7f7f5; --card:#fff; --fg:#1a1a18; --muted:#6b6b66; --line:#e3e3de;
  --accent:#1f5f4f; --accent-soft:#e6efeb; --chip:#efefeb;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
@media (prefers-color-scheme:dark) {
  :root { --bg:#17181a; --card:#1f2124; --fg:#e9e9e6; --muted:#9a9a95; --line:#2e3135;
          --accent:#6fc3a8; --accent-soft:#1d2b27; --chip:#2a2d31; }
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font-family:var(--font); line-height:1.55; }
.wrap { max-width:960px; margin:0 auto; padding:28px 20px 64px; }
header h1 { font-size:1.6rem; margin:0 0 6px; letter-spacing:-.02em; }
.meta { color:var(--muted); font-size:.82rem; }
.meta b { color:var(--fg); font-weight:600; }
.controls { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:22px 0 8px; }
#q { flex:1 1 200px; min-width:160px; padding:9px 12px; border:1px solid var(--line); border-radius:8px;
     background:var(--card); color:var(--fg); font-size:.9rem; font-family:inherit; }
.tabs { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 20px; }
.tab { padding:6px 13px; border:1px solid var(--line); border-radius:999px; background:var(--card);
       color:var(--muted); font-size:.83rem; cursor:pointer; font-family:inherit; }
.tab[aria-selected="true"] { background:var(--accent-soft); border-color:var(--accent); color:var(--accent); font-weight:600; }
section { margin-bottom:34px; }
section h2 { font-size:1rem; margin:0 0 12px; padding-bottom:8px; border-bottom:1px solid var(--line);
             display:flex; justify-content:space-between; align-items:baseline; }
section h2 span { color:var(--muted); font-size:.78rem; font-weight:400; }
ul { list-style:none; margin:0; padding:0; }
li { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:13px 15px; margin-bottom:8px; }
li a { color:var(--fg); text-decoration:none; font-weight:600; font-size:.95rem; }
li a:hover { color:var(--accent); text-decoration:underline; }
.sub { margin-top:5px; font-size:.78rem; color:var(--muted); display:flex; flex-wrap:wrap; gap:8px; }
.src { background:var(--chip); border-radius:4px; padding:1px 7px; }
.summary { margin-top:7px; font-size:.85rem; color:var(--muted); overflow:hidden;
           display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
.empty { color:var(--muted); font-size:.85rem; padding:10px 0; }
footer { margin-top:40px; padding-top:16px; border-top:1px solid var(--line); color:var(--muted); font-size:.75rem; }
footer a { color:var(--accent); }
details.feeds summary { cursor:pointer; font-size:.75rem; color:var(--muted); }
.feedgrid { margin-top:8px; font-size:.72rem; color:var(--muted); columns:2; }
.bad { color:#c0392b; }
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>세무 뉴스 브리핑</h1>
  <p class="meta">최근 <b>7일</b> · 총 <b>__TOTAL__건</b> · 마지막 갱신 <b>__UPDATED__ KST</b> · 매일 자동 수집</p>
</header>

<div class="controls">
  <input id="q" type="search" placeholder="제목·출처 검색 (예: 부가세, 국세청)" autocomplete="off">
</div>
<div class="tabs" role="tablist">__TABS__</div>

__SECTIONS__

<footer>
  <details class="feeds"><summary>수집 소스 __FEED_OK__/__FEED_TOTAL__개 정상</summary>
    <div class="feedgrid">__FEEDLOG__</div>
  </details>
  <p>기사 본문 저작권은 각 언론사에 있습니다. 제목과 링크만 수집합니다.</p>
</footer>
</div>
<script>
const q = document.getElementById('q');
const tabs = [...document.querySelectorAll('.tab')];
const sections = [...document.querySelectorAll('section')];

function apply() {
  const term = q.value.trim().toLowerCase();
  const cat = tabs.find(t => t.getAttribute('aria-selected') === 'true').dataset.cat;
  for (const sec of sections) {
    const catMatch = cat === 'all' || sec.dataset.cat === cat;
    let shown = 0;
    for (const li of sec.querySelectorAll('li')) {
      const hit = !term || li.dataset.search.includes(term);
      li.hidden = !(catMatch && hit);
      if (!li.hidden) shown++;
    }
    sec.hidden = !catMatch;
    const empty = sec.querySelector('.empty');
    if (empty) empty.hidden = shown > 0;
    const count = sec.querySelector('h2 span');
    if (count) count.textContent = shown + '건';
  }
}
q.addEventListener('input', apply);
tabs.forEach(t => t.addEventListener('click', () => {
  tabs.forEach(o => o.setAttribute('aria-selected', String(o === t)));
  apply();
}));
apply();
</script>
</body>
</html>
"""


def _norm(text: str) -> str:
    return "".join(ch for ch in text.lower() if ch.isalnum())


def _echoes_title(summary: str, title: str) -> bool:
    """Google News 요약문은 제목을 그대로 되풀이하는 경우가 많다 — 그럴 땐 숨긴다."""
    a, b = _norm(summary), _norm(title)
    return not a or not b or a.startswith(b[:40]) or b.startswith(a[:40])


def render() -> str:
    data = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))

    tabs = ['<button class="tab" role="tab" data-cat="all" aria-selected="true">전체</button>']
    sections = []
    for cat in data["categories"]:
        tabs.append(
            f'<button class="tab" role="tab" data-cat="{cat["id"]}" aria-selected="false">'
            f'{escape(cat["label"])}</button>'
        )
        rows = []
        for it in cat["items"]:
            search = escape(f'{it["title"]} {it["source"]}'.lower(), quote=True)
            date = escape(it["published_kst"]) + ("" if it["is_dated"] else " (추정)")
            summary = ""
            if it["summary"] and not _echoes_title(it["summary"], it["title"]):
                summary = f'<div class="summary">{escape(it["summary"])}</div>'
            rows.append(
                f'<li data-search="{search}">'
                f'<a href="{escape(it["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'{escape(it["title"])}</a>'
                f'<div class="sub"><span class="src">{escape(it["source"])}</span><span>{date}</span></div>'
                f"{summary}</li>"
            )
        sections.append(
            f'<section data-cat="{cat["id"]}">'
            f'<h2>{escape(cat["label"])}<span>{len(cat["items"])}건</span></h2>'
            f'<ul>{"".join(rows)}</ul>'
            f'<p class="empty" hidden>검색 결과가 없습니다.</p></section>'
        )

    feedlog = "".join(
        f'<div class="{"" if f["ok"] else "bad"}">{"·" if f["ok"] else "×"} '
        f'{escape(f["name"])} ({f["count"]})</div>'
        for f in data["feeds"]
    )

    html = TEMPLATE
    for key, val in {
        "__TOTAL__": str(data["total"]),
        "__UPDATED__": data["generated_kst"],
        "__TABS__": "".join(tabs),
        "__SECTIONS__": "".join(sections),
        "__FEEDLOG__": feedlog,
        "__FEED_OK__": str(sum(1 for f in data["feeds"] if f["ok"])),
        "__FEED_TOTAL__": str(len(data["feeds"])),
    }.items():
        html = html.replace(key, val)
    return html


if __name__ == "__main__":
    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(render(), encoding="utf-8")
    (out / "latest.json").write_text(
        (ROOT / "data" / "latest.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print(f"docs/index.html 생성 ({(out / 'index.html').stat().st_size:,} bytes)")
