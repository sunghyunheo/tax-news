"""data/latest.json 을 docs/index.html 정적 페이지로 렌더링한다."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://skn-tax.github.io/tax-news/"

TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>세무 뉴스 브리핑</title>
<meta name="description" content="SK네트웍스 세무팀 일일 브리핑 — 경정청구·세법개정·조사동향·판례를 중요도순으로 정리">
<style>
:root {
  --bg:#f7f7f5; --card:#fff; --fg:#1a1a18; --muted:#6b6b66; --line:#e3e3de;
  --accent:#1f5f4f; --accent-soft:#e6efeb; --chip:#efefeb;
  --hi:#b3261e; --hi-soft:#fbe9e7; --mid:#8a5a00; --mid-soft:#fdf3e2; --lo:#6b6b66;
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
/* 다크 토큰. 시스템 설정과 명시적 선택 양쪽에서 동일하게 적용된다.
   :root:not([data-theme="light"]) 로 감싸 명시적 라이트 선택이 OS 다크를 이긴다. */
@media (prefers-color-scheme:dark) {
  :root:not([data-theme="light"]) {
    --bg:#17181a; --card:#1f2124; --fg:#e9e9e6; --muted:#9a9a95; --line:#2e3135;
    --accent:#6fc3a8; --accent-soft:#1d2b27; --chip:#2a2d31;
    --hi:#ff8a80; --hi-soft:#3a1f1c; --mid:#e8b45c; --mid-soft:#332a17; --lo:#9a9a95;
  }
}
:root[data-theme="dark"] {
  --bg:#17181a; --card:#1f2124; --fg:#e9e9e6; --muted:#9a9a95; --line:#2e3135;
  --accent:#6fc3a8; --accent-soft:#1d2b27; --chip:#2a2d31;
  --hi:#ff8a80; --hi-soft:#3a1f1c; --mid:#e8b45c; --mid-soft:#332a17; --lo:#9a9a95;
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--fg); font-family:var(--font); line-height:1.55; }
.wrap { max-width:1000px; margin:0 auto; padding:28px 20px 64px; }
header h1 { font-size:1.6rem; margin:0 0 6px; letter-spacing:-.02em; }
.meta { color:var(--muted); font-size:.82rem; margin:0; }
.meta b { color:var(--fg); font-weight:600; }
.controls { display:flex; flex-wrap:wrap; gap:8px; align-items:center; margin:22px 0 6px; }
#q { flex:1 1 200px; min-width:160px; padding:9px 12px; border:1px solid var(--line); border-radius:8px;
     background:var(--card); color:var(--fg); font-size:.9rem; font-family:inherit; }
.sorts { display:flex; gap:0; border:1px solid var(--line); border-radius:8px; overflow:hidden; }
.sortbtn { padding:9px 14px; border:0; background:var(--card); color:var(--muted);
           font-size:.83rem; cursor:pointer; font-family:inherit; }
.sortbtn[aria-pressed="true"] { background:var(--accent-soft); color:var(--accent); font-weight:600; }
.tabs { display:flex; flex-wrap:wrap; gap:6px; margin:12px 0 20px; }
.tab { padding:6px 13px; border:1px solid var(--line); border-radius:999px; background:var(--card);
       color:var(--muted); font-size:.83rem; cursor:pointer; font-family:inherit; }
.tab[aria-selected="true"] { background:var(--accent-soft); border-color:var(--accent); color:var(--accent); font-weight:600; }
.tab b { font-weight:600; opacity:.6; }
section { margin-bottom:34px; }
section h2 { font-size:1rem; margin:0 0 4px; padding-bottom:8px; border-bottom:1px solid var(--line);
             display:flex; justify-content:space-between; align-items:baseline; }
section h2 span { color:var(--muted); font-size:.78rem; font-weight:400; }
.colhead { display:grid; grid-template-columns:88px 1fr; gap:12px; padding:6px 15px 4px;
           color:var(--muted); font-size:.67rem; letter-spacing:0; line-height:1.35; }
ul { list-style:none; margin:0; padding:0; }
li { display:grid; grid-template-columns:88px 1fr; gap:12px; align-items:start;
     background:var(--card); border:1px solid var(--line); border-radius:10px;
     padding:12px 15px; margin-bottom:8px; }
.prio { display:flex; flex-direction:column; align-items:center; gap:3px; padding-top:1px; }
.rank { font-size:1.05rem; font-weight:700; font-variant-numeric:tabular-nums; line-height:1.1; }
.lvl { font-size:.68rem; font-weight:700; border-radius:4px; padding:1px 6px; white-space:nowrap; }
.lvl-high { color:var(--hi); background:var(--hi-soft); }
.lvl-mid  { color:var(--mid); background:var(--mid-soft); }
.lvl-low  { color:var(--lo); background:var(--chip); }
li.high .rank { color:var(--hi); }
li.high { border-left:3px solid var(--hi); }
.score { font-size:.62rem; color:var(--muted); font-variant-numeric:tabular-nums; }
.body a { color:var(--fg); text-decoration:none; font-weight:600; font-size:.95rem; }
.body a:hover { color:var(--accent); text-decoration:underline; }
.sub { margin-top:5px; font-size:.78rem; color:var(--muted); display:flex; flex-wrap:wrap; gap:8px; }
.src { background:var(--chip); border-radius:4px; padding:1px 7px; }
.kw { color:var(--accent); background:var(--accent-soft); border-radius:4px; padding:1px 6px; font-size:.72rem; }
.summary { margin-top:7px; font-size:.85rem; color:var(--muted); overflow:hidden;
           display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; }
.empty { color:var(--muted); font-size:.85rem; padding:10px 0; }
footer { margin-top:40px; padding-top:16px; border-top:1px solid var(--line); color:var(--muted); font-size:.75rem; }
footer a { color:var(--accent); }
footer p { margin:6px 0; }
details.feeds summary { cursor:pointer; font-size:.75rem; color:var(--muted); }
.feedgrid { margin-top:8px; font-size:.72rem; color:var(--muted); columns:2; }
.bad { color:var(--hi); }
@media (max-width:560px) {
  li, .colhead { grid-template-columns:66px 1fr; gap:9px; }
  .prio { flex-direction:column; }
}
</style>
</head>
<body>
<div class="wrap">
<header>
  <h1>세무 뉴스 브리핑</h1>
  <p class="meta">SK네트웍스 세무팀 · 최근 <b>__DAYS__일</b> · 총 <b>__TOTAL__건</b>
     · <b>우선확인 __HIGH__건</b> · 마지막 갱신 <b>__UPDATED__ KST</b></p>
</header>

<div class="controls">
  <input id="q" type="search" placeholder="제목·출처·키워드 검색 (예: 경정청구, 워커힐)" autocomplete="off">
  <div class="sorts">
    <button class="sortbtn" id="sort-prio" aria-pressed="true">중요도순</button>
    <button class="sortbtn" id="sort-date" aria-pressed="false">최신순</button>
  </div>
</div>
<div class="tabs" role="tablist">__TABS__</div>

__SECTIONS__

<footer>
  <p><b>중요도</b>는 카테고리 · 키워드 · 최신성으로 자동 계산한 우선확인순위입니다.
     <span class="lvl lvl-high">상</span> 우선 확인 ·
     <span class="lvl lvl-mid">중</span> 확인 권장 ·
     <span class="lvl lvl-low">하</span> 참고.
     기준은 <code>sources.json</code> 의 <code>importance</code> 에서 조정합니다.</p>
  <details class="feeds"><summary>수집 소스 __FEED_OK__/__FEED_TOTAL__개 정상</summary>
    <div class="feedgrid">__FEEDLOG__</div>
  </details>
  <p>기사 본문 저작권은 각 언론사에 있습니다. 제목과 링크만 수집합니다. · <a href="__SITE__">__SITE__</a></p>
</footer>
</div>
<script>
const q = document.getElementById('q');
const tabs = [...document.querySelectorAll('.tab')];
const sections = [...document.querySelectorAll('section')];
const sortPrio = document.getElementById('sort-prio');
const sortDate = document.getElementById('sort-date');

function reorder(byDate) {
  for (const sec of sections) {
    const ul = sec.querySelector('ul');
    const rows = [...ul.children];
    rows.sort((a, b) => byDate
      ? b.dataset.date.localeCompare(a.dataset.date)
      : (+b.dataset.score - +a.dataset.score) || b.dataset.date.localeCompare(a.dataset.date));
    rows.forEach(r => ul.appendChild(r));
  }
}

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
sortPrio.addEventListener('click', () => {
  sortPrio.setAttribute('aria-pressed', 'true');
  sortDate.setAttribute('aria-pressed', 'false');
  reorder(false);
});
sortDate.addEventListener('click', () => {
  sortDate.setAttribute('aria-pressed', 'true');
  sortPrio.setAttribute('aria-pressed', 'false');
  reorder(true);
});
apply();
</script>
</body>
</html>
"""

LEVEL_CLASS = {"상": "lvl-high", "중": "lvl-mid", "하": "lvl-low"}


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
    high_total = 0

    for cat in data["categories"]:
        tabs.append(
            f'<button class="tab" role="tab" data-cat="{cat["id"]}" aria-selected="false">'
            f'{escape(cat["label"])} <b>{len(cat["items"])}</b></button>'
        )
        rows = []
        for it in cat["items"]:
            level = it.get("level", "하")
            if level == "상":
                high_total += 1
            search = escape(
                " ".join(
                    [it["title"], it["source"], *it.get("matched", []), *it.get("reasons", [])]
                ).lower(),
                quote=True,
            )
            date = escape(it["published_kst"]) + ("" if it["is_dated"] else " (추정)")
            summary = ""
            if it["summary"] and not _echoes_title(it["summary"], it["title"]):
                summary = f'<div class="summary">{escape(it["summary"])}</div>'
            tags = "".join(
                f'<span class="kw">{escape(k)}</span>'
                for k in (it.get("matched") or it.get("reasons") or [])[:3]
            )
            rows.append(
                f'<li class="{"high" if level == "상" else ""}" data-search="{search}" '
                f'data-score="{it.get("score", 0)}" data-date="{escape(it["published_at"])}">'
                f'<div class="prio">'
                f'<span class="rank">{it.get("rank", "-")}</span>'
                f'<span class="lvl {LEVEL_CLASS.get(level, "lvl-low")}" '
                f'title="{escape(it.get("level_hint", ""))}">{escape(level)}</span>'
                f'<span class="score">{it.get("score", 0)}점</span>'
                f"</div>"
                f'<div class="body">'
                f'<a href="{escape(it["url"], quote=True)}" target="_blank" rel="noopener noreferrer">'
                f'{escape(it["title"])}</a>'
                f'<div class="sub"><span class="src">{escape(it["source"])}</span>'
                f"<span>{date}</span>{tags}</div>"
                f"{summary}</div></li>"
            )
        sections.append(
            f'<section data-cat="{cat["id"]}">'
            f'<h2>{escape(cat["label"])}<span>{len(cat["items"])}건</span></h2>'
            f'<div class="colhead"><span>중요도<br>(우선확인순위)</span><span>기사</span></div>'
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
        "__HIGH__": str(high_total),
        "__DAYS__": str(data.get("max_age_days", 7)),
        "__UPDATED__": data["generated_kst"],
        "__TABS__": "".join(tabs),
        "__SECTIONS__": "".join(sections),
        "__FEEDLOG__": feedlog,
        "__FEED_OK__": str(sum(1 for f in data["feeds"] if f["ok"])),
        "__FEED_TOTAL__": str(len(data["feeds"])),
        "__SITE__": SITE_URL,
    }.items():
        html = html.replace(key, val)
    return html


def render_fragment() -> str:
    """Artifact 발행용. doctype/html/head/body 래퍼를 벗기고 title+style+본문만 남긴다.

    Artifact 는 파일을 자체 head/body 안에 감싸 발행하므로 래퍼 태그를 넣으면 중복된다.
    """
    html = render()
    head = html[html.index("<title>") : html.index("</head>")]
    body = html[html.index("<body>") + len("<body>") : html.index("</body>")]
    return head.strip() + "\n" + body.strip() + "\n"


if __name__ == "__main__":
    import sys

    if "--artifact" in sys.argv:
        target = ROOT / "artifact.html"
        target.write_text(render_fragment(), encoding="utf-8")
        print("artifact.html 생성 ({:,} bytes)".format(target.stat().st_size))
        raise SystemExit(0)

    out = ROOT / "docs"
    out.mkdir(exist_ok=True)
    (out / "index.html").write_text(render(), encoding="utf-8")
    (out / "latest.json").write_text(
        (ROOT / "data" / "latest.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (out / ".nojekyll").write_text("", encoding="utf-8")
    print("docs/index.html 생성 ({:,} bytes)".format((out / "index.html").stat().st_size))
