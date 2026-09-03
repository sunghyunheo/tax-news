"""data/latest.json 을 메일 발송용 HTML 로 만든다.

메일 클라이언트(특히 Outlook)는 <style> 블록과 CSS 변수를 자주 지우므로
모든 서식을 인라인 style 속성으로 넣는다. 자바스크립트·다크모드 토큰은 쓰지 않는다.

  python email_digest.py            -> mail/digest.html, mail/subject.txt 생성
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SITE_URL = "https://sunghyunheo.github.io/tax-news/"

# 메일에는 전부 넣지 않는다 — 등급이 '상'/'중' 인 것만, 카테고리마다 최대 6건.
MAX_PER_CATEGORY = 6
INCLUDE_LEVELS = ("상", "중")

FG = "#1a1a18"
MUTED = "#6b6b66"
LINE = "#e3e3de"
ACCENT = "#1f5f4f"
HI = "#b3261e"
HI_SOFT = "#fbe9e7"
MID = "#8a5a00"
MID_SOFT = "#fdf3e2"
FONT = "'Malgun Gothic','맑은 고딕',-apple-system,'Apple SD Gothic Neo',sans-serif"


def level_style(level: str) -> str:
    color, bg = (HI, HI_SOFT) if level == "상" else (MID, MID_SOFT)
    return (
        "display:inline-block;font-size:11px;font-weight:bold;border-radius:3px;"
        "padding:1px 6px;color:{};background:{};".format(color, bg)
    )


def build() -> tuple:
    data = json.loads((ROOT / "data" / "latest.json").read_text(encoding="utf-8"))

    blocks = []
    picked_total = 0
    high_total = 0

    for cat in data["categories"]:
        picks = [it for it in cat["items"] if it.get("level") in INCLUDE_LEVELS][:MAX_PER_CATEGORY]
        if not picks:
            continue
        picked_total += len(picks)
        high_total += sum(1 for it in picks if it.get("level") == "상")

        rows = []
        for it in picks:
            tags = " · ".join(escape(k) for k in (it.get("matched") or it.get("reasons") or [])[:2])
            tag_html = (
                '<span style="color:{};font-size:11px;"> · {}</span>'.format(ACCENT, tags)
                if tags
                else ""
            )
            rows.append(
                '<tr>'
                '<td valign="top" style="padding:7px 10px 7px 0;white-space:nowrap;">'
                '<span style="font-size:13px;font-weight:bold;color:{rank_color};">{rank}</span>'
                '&nbsp;<span style="{lvl}">{level}</span>'
                "</td>"
                '<td valign="top" style="padding:7px 0;">'
                '<a href="{url}" style="color:{fg};font-size:14px;font-weight:bold;'
                'text-decoration:none;">{title}</a><br>'
                '<span style="color:{muted};font-size:11px;">{source} · {date}</span>{tag}'
                "</td>"
                "</tr>".format(
                    rank_color=HI if it.get("level") == "상" else MUTED,
                    rank=it.get("rank", "-"),
                    lvl=level_style(it.get("level", "중")),
                    level=escape(it.get("level", "")),
                    url=escape(it["url"], quote=True),
                    fg=FG,
                    title=escape(it["title"]),
                    muted=MUTED,
                    source=escape(it["source"]),
                    date=escape(it["published_kst"]),
                    tag=tag_html,
                )
            )

        blocks.append(
            '<h2 style="font-size:15px;color:{fg};margin:26px 0 6px;padding-bottom:6px;'
            'border-bottom:1px solid {line};">{label}'
            '<span style="color:{muted};font-size:11px;font-weight:normal;"> '
            "&nbsp;{shown}건 / 전체 {total}건</span></h2>"
            '<table cellpadding="0" cellspacing="0" border="0" width="100%">{rows}</table>'.format(
                fg=FG,
                line=LINE,
                muted=MUTED,
                label=escape(cat["label"]),
                shown=len(picks),
                total=cat["total"],
                rows="".join(rows),
            )
        )

    date_label = data["generated_kst"].split(" ")[0]
    subject = "[세무 브리핑] {} · 우선확인 {}건 / 총 {}건".format(
        date_label, high_total, data["total"]
    )

    html = (
        '<div style="font-family:{font};background:#f7f7f5;padding:22px 0;">'
        '<div style="max-width:680px;margin:0 auto;background:#ffffff;'
        'border:1px solid {line};border-radius:8px;padding:24px 26px;">'
        '<h1 style="font-size:19px;color:{fg};margin:0 0 4px;">세무 뉴스 브리핑</h1>'
        '<p style="color:{muted};font-size:12px;margin:0 0 2px;">'
        "SK네트웍스 세무팀 · {date} 기준 · 최근 {days}일 수집 {total}건 중 "
        "우선확인 대상 {picked}건</p>"
        '<p style="color:{muted};font-size:11px;margin:0;">'
        '중요도 <span style="{lvl_hi}">상</span> 우선 확인 · '
        '<span style="{lvl_mid}">중</span> 확인 권장 &nbsp;|&nbsp; 숫자는 카테고리 내 순위</p>'
        "{blocks}"
        '<p style="margin:30px 0 0;padding-top:14px;border-top:1px solid {line};'
        'color:{muted};font-size:11px;">'
        '전체 목록: <a href="{site}" style="color:{accent};">{site}</a><br>'
        "기사 본문 저작권은 각 언론사에 있습니다. 제목과 링크만 수집합니다.</p>"
        "</div></div>"
    ).format(
        font=FONT,
        line=LINE,
        fg=FG,
        muted=MUTED,
        accent=ACCENT,
        date=data["generated_kst"],
        days=data.get("max_age_days", 14),
        total=data["total"],
        picked=picked_total,
        lvl_hi=level_style("상"),
        lvl_mid=level_style("중"),
        blocks="".join(blocks) or '<p style="color:#6b6b66;">오늘은 우선확인 대상 기사가 없습니다.</p>',
        site=SITE_URL,
    )
    return subject, html


if __name__ == "__main__":
    subject, html = build()
    out = ROOT / "mail"
    out.mkdir(exist_ok=True)
    (out / "digest.html").write_text(html, encoding="utf-8")
    (out / "subject.txt").write_text(subject, encoding="utf-8")
    print(subject)
    print("mail/digest.html 생성 ({:,} bytes)".format((out / "digest.html").stat().st_size))
