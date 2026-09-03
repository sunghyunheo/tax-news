"""세무 뉴스 수집기 — RSS/Atom 피드를 읽어 카테고리별로 분류해 data/latest.json 에 저장한다.

두 종류의 소스를 쓴다.
  * 카테고리 전용 피드 (categories[].feeds) — 수집 결과가 그 카테고리로 직행
  * 전문지 전체기사 풀 (pools)            — categories[].match 키워드로 카테고리에 배분

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


# ---------------------------------------------------------------- 피드 파싱

def fetch(url: str, timeout: int) -> bytes:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def parse_date(raw):
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


def text_of(el, *paths):
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


def parse_feed(raw: bytes) -> list:
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
            }
        )
    return items


# ---------------------------------------------------------------- 중복 제거

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


# ---------------------------------------------------------------- 분류

def _matcher(keyword: str):
    """키워드 하나를 판정 함수로 바꾼다.

    한글은 부분일치로 충분하지만(조사가 붙으므로), 영문·숫자 키워드는 단어 경계를 요구한다.
    'sk' 가 risk/task 에, 'apa' 가 japan/apartment 에 걸리는 것을 막기 위함이다.
    """
    if re.fullmatch(r"[a-z0-9.&\- ]+", keyword):
        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])")
        return lambda hay: pattern.search(hay) is not None
    return lambda hay: keyword in hay


_MATCHER_CACHE: dict = {}


def hits_of(haystack: str, keywords: list) -> list:
    """haystack 에 걸린 키워드들을 돌려준다."""
    found = []
    for k in keywords:
        if k not in _MATCHER_CACHE:
            _MATCHER_CACHE[k] = _matcher(k)
        if _MATCHER_CACHE[k](haystack):
            found.append(k)
    return found


def haystack_of(item: dict) -> str:
    return (item["title"] + " " + item["summary"]).lower()


def classify(item: dict, rules: list):
    """(카테고리 id, 걸린 키워드들) 을 돌려준다.

    rules 는 (id, match, require) 튜플의 우선순위 목록이다.
      * match   — 하나라도 걸리면 후보가 된다. ["*"] 는 catch-all.
      * require — 비어있지 않으면 이 중 하나도 함께 걸려야 배정된다.
                  계열사·업종 키워드가 세무와 무관한 기업 뉴스를 끌어오는 것을 막는 용도다.
    """
    haystack = haystack_of(item)
    for cat_id, keywords, require in rules:
        if keywords == ["*"]:
            return cat_id, []
        hits = hits_of(haystack, keywords)
        if not hits:
            continue
        if require and not hits_of(haystack, require):
            continue  # 주제는 맞지만 세무 기사가 아니다 — 다음 카테고리로 넘긴다
        return cat_id, hits
    return "", []


# ---------------------------------------------------------------- 메인

def main() -> int:
    cfg = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
    s = cfg["settings"]
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=s["max_age_days"])

    # 분류 우선순위: priority 가 작은 카테고리가 기사를 먼저 가져간다 (없으면 배열 순서).
    ranked = sorted(
        (c for c in cfg["categories"] if c.get("match")),
        key=lambda c: c.get("priority", 50),
    )
    rules = [(c["id"], c["match"], c.get("require", [])) for c in ranked]
    buckets = {c["id"]: [] for c in cfg["categories"]}
    feed_log = []
    seen = set()         # 정규화된 URL
    seen_titles = set()  # 제목 지문 (매체만 다른 동일 기사)

    def read(feed: dict, kind: str, cat_id: str) -> list:
        """피드 하나를 읽어 신선하고 중복 아닌 항목만 돌려준다. 실패는 로그로 남긴다."""
        status = {"kind": kind, "category": cat_id, "name": feed["name"], "url": feed["url"]}
        try:
            raw_items = parse_feed(fetch(feed["url"], s["request_timeout_sec"]))
        except (urllib.error.URLError, urllib.error.HTTPError, ET.ParseError, OSError) as exc:
            status.update(ok=False, count=0, error=type(exc).__name__ + ": " + str(exc))
            feed_log.append(status)
            print("  [FAIL] " + feed["name"] + ": " + status["error"], file=sys.stderr)
            return []

        fresh = []
        for item in raw_items[: s["max_items_per_feed"]]:
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
            fresh.append(item)

        status.update(ok=True, count=len(fresh), error=None)
        feed_log.append(status)
        return fresh

    # 1) 카테고리 전용 검색 피드 — 카테고리 순서대로 먼저 자리를 잡는다.
    dropped_by_require = 0
    for cat in cfg["categories"]:
        require = cat.get("require", [])
        for feed in cat.get("feeds", []):
            items = read(feed, "category", cat["id"])
            kept = 0
            for item in items:
                # 전용 검색 피드는 이미 그 주제를 겨냥한 질의라 분류 태그가 없다.
                # 다만 require 가 걸린 카테고리는 세무 무관 기사를 여기서도 걸러낸다.
                if require and not hits_of(haystack_of(item), require):
                    dropped_by_require += 1
                    continue
                item["matched"] = []
                buckets[cat["id"]].append(item)
                kept += 1
            print("  [cat ] {:8s} {}: {}/{}".format(cat["id"], feed["name"], kept, len(items)))

    # 2) 전문지 전체기사 풀 — match 키워드로 카테고리에 배분한다.
    unmatched = 0
    for feed in cfg.get("pools", []):
        items = read(feed, "pool", "-")
        spread = {}
        for item in items:
            cat_id, hits = classify(item, rules)
            if not cat_id:
                unmatched += 1
                continue
            item["matched"] = hits
            buckets[cat_id].append(item)
            spread[cat_id] = spread.get(cat_id, 0) + 1
        print("  [pool] {}: {} -> {}".format(feed["name"], len(items), spread))

    categories = []
    for cat in cfg["categories"]:
        items = sorted(buckets[cat["id"]], key=lambda x: x["published_at"], reverse=True)
        categories.append(
            {
                "id": cat["id"],
                "label": cat["label"],
                "total": len(items),
                "items": items[: s["max_items_per_category"]],
            }
        )

    payload = {
        "generated_at": now.isoformat(),
        "generated_kst": now.astimezone(KST).strftime("%Y-%m-%d %H:%M"),
        "max_age_days": s["max_age_days"],
        "total": sum(len(c["items"]) for c in categories),
        "categories": categories,
        "feeds": feed_log,
    }

    (ROOT / "data").mkdir(exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    (ROOT / "data" / "latest.json").write_text(text, encoding="utf-8")
    archive = ROOT / "data" / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / (now.astimezone(KST).strftime("%Y-%m-%d") + ".json")).write_text(text, encoding="utf-8")

    ok = sum(1 for f in feed_log if f["ok"])
    print("\n총 {}건 · 피드 {}/{} 성공 · 미분류 {}건 · 세무무관 {}건 버림".format(
        payload["total"], ok, len(feed_log), unmatched, dropped_by_require))
    return 0 if payload["total"] else 1


if __name__ == "__main__":
    sys.exit(main())
