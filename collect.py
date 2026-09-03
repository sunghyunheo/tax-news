"""세무 뉴스 수집기 — RSS/Atom 피드를 읽어 data/latest.json 으로 정규화 저장.

표준 라이브러리만 사용한다 (GitHub Actions 에서 pip install 없이 돌기 위함).
"""
from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (compatible; tax-news-bot/1.0; +https://github.com/)"

# Atom / Dublin Core 네임스페이스
NS = {"atom": "http://www.w3.org/2005/Atom", "dc": "http://purl.org/dc/elements/1.1/"}


def fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def parse_date(raw: str | None) -> datetime | None:
    if not raw:
        return None
    raw = raw.strip()
    try:
        return parsedate_to_datetime(raw).astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%Y.%m.%d"):
        try:
            dt = datetime.strptime(raw.replace("+09:00", "+0900"), fmt)
            return (dt if dt.tzinfo else dt.replace(tzinfo=KST)).astimezone(timezone.utc)
        except ValueError:
            continue
    return None


def text_of(el, *paths: str) -> str | None:
    for path in paths:
        found = el.find(path, NS)
        if found is None:
            continue
        if found.text and found.text.strip():
            return found.text.strip()
        href = found.get("href")
        if href:
            return href.strip()
    return None


def parse_feed(raw: bytes) -> list[dict]:
    root = ET.fromstring(raw)
    entries = root.findall(".//item") or root.findall(".//atom:entry", NS)
    items = []
    for el in entries:
        title = strip_html(text_of(el, "title", "atom:title") or "")
        link = text_of(el, "link", "atom:link[@rel='alternate']", "atom:link", "guid")
        if not title or not link:
            continue
        items.append(
            {
                "title": title,
                "url": link,
                "summary": strip_html(text_of(el, "description", "atom:summary", "atom:content") or "")[:400],
                "published": text_of(el, "pubDate", "atom:published", "atom:updated", "dc:date"),
                "author": strip_html(text_of(el, "dc:creator", "author", "atom:author/atom:name") or ""),
            }
        )
    return items


def canonical(url: str) -> str:
    """추적 파라미터를 떼어 중복 판정을 안정화한다."""
    url = re.sub(r"[?&](utm_[^=]+|fbclid|gclid)=[^&]*", "", url)
    return url.rstrip("?&/").lower()


def title_key(title: str) -> str:
    """같은 기사가 여러 매체로 실릴 때를 잡는다.

    Google News 제목은 "본문 제목 - 매체명" 꼴이라 뒤쪽 매체명을 떼고,
    공백·기호를 지운 뒤 앞 40자로 비교한다.
    """
    title = re.sub(r"\s+[-–|]\s+[^-–|]{2,20}$", "", title)
    return "".join(ch for ch in title.lower() if ch.isalnum())[:40]


def main() -> int:
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    s = cfg["settings"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=s["max_age_days"])

    categories, feed_log = [], []
    seen: set[str] = set()        # 정규화된 URL
    seen_titles: set[str] = set()  # 제목 지문 (매체만 다른 동일 기사)

    for cat in cfg["categories"]:
        collected = []
        for feed in cat["feeds"]:
            status = {"category": cat["id"], "name": feed["name"], "url": feed["url"]}
            try:
                items = parse_feed(fetch(feed["url"], s["request_timeout_sec"]))
            except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as exc:
                status.update(ok=False, count=0, error=f"{type(exc).__name__}: {exc}")
                feed_log.append(status)
                print(f"  [FAIL] {feed['name']}: {status['error']}", file=sys.stderr)
                continue

            kept = 0
            for item in items[: s["max_items_per_feed"]]:
                key, tkey = canonical(item["url"]), title_key(item["title"])
                if key in seen or (len(tkey) > 12 and tkey in seen_titles):
                    continue
                dt = parse_date(item["published"])
                if dt and dt < cutoff:
                    continue
                seen.add(key)
                seen_titles.add(tkey)
                item["source"] = feed["name"]
                item["published_at"] = (dt or now).isoformat()
                item["published_kst"] = (dt or now).astimezone(KST).strftime("%Y-%m-%d %H:%M")
                item["is_dated"] = dt is not None
                collected.append(item)
                kept += 1

            status.update(ok=True, count=kept, error=None)
            feed_log.append(status)
            print(f"  [ OK ] {feed['name']}: {kept}건")

        collected.sort(key=lambda x: x["published_at"], reverse=True)
        categories.append(
            {
                "id": cat["id"],
                "label": cat["label"],
                "items": collected[: s["max_items_per_category"]],
            }
        )

    payload = {
        "generated_at": now.isoformat(),
        "generated_kst": now.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "total": sum(len(c["items"]) for c in categories),
        "categories": categories,
        "feeds": feed_log,
    }

    (ROOT / "data").mkdir(exist_ok=True)
    (ROOT / "data" / "latest.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    archive = ROOT / "data" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / f"{now.astimezone(KST):%Y-%m-%d}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    ok = sum(1 for f in feed_log if f["ok"])
    print(f"\n총 {payload['total']}건 수집 · 피드 {ok}/{len(feed_log)} 성공")
    return 0 if payload["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
