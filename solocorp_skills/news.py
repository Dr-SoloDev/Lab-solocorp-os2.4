"""News Fetcher — ดึงข่าวจาก watchlist ไปเป็น digest

ใช้ได้ 2 โหมด:
  * ``rss`` — ดึง RSS/Atom ตรง ๆ (เร็ว ไม่กิน Chromium เลย · 0 RAM เพิ่ม)
  * ``web`` — ใช้ Chromium (carbonyl) เพื่อ render JS — สำหรับเว็บที่ไม่มี RSS

ข้อมูลที่ได้จะถูกหนีซ้ำด้วย URL + หัวข้อ แล้วส่งต่อผ่าน
FactsService → ``POST /v1/context`` (ดู ADR-020)
"""

from __future__ import annotations

import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

__all__ = [
    "NewsSource",
    "NewsItem",
    "load_watchlist",
    "fetch_source",
    "dedupe",
    "load_seen",
    "save_seen",
    "build_digest",
    "WATCHLIST_PATH",
    "SEEN_PATH",
]

ROOT = Path(__file__).resolve().parent.parent
WATCHLIST_PATH = ROOT / "bus" / "news" / "watchlist.md"
SEEN_PATH = ROOT / "bus" / "news" / "seen.json"

_UA = "Mozilla/5.0 (compatible; SoloCorpOS/2.4; +news_daily)"
_FETCH_TIMEOUT = 20
_MAX_SEEN = 500


@dataclass
class NewsSource:
    """แหล่งข่าว 1 แถวใน watchlist"""
    dept: str
    name: str
    url: str
    mode: str = "rss"          # rss | web
    active: bool = True
    max_items: int = 15


@dataclass
class NewsItem:
    """ข่าว 1 ชิ้น"""
    title: str
    url: str
    summary: str = ""
    source: str = ""
    dept: str = ""
    published: str = ""

    def key(self) -> str:
        """คีย์สำหรับกันข่าวซ้ำ"""
        t = re.sub(r"[^\w฀-๿]+", "", self.title.lower())
        return f"{t[:60]}|{self.url.split('?')[0]}"


# ══════════════════════════════════════════════════════════════════════
# Watchlist
# ══════════════════════════════════════════════════════════════════════


def load_watchlist(path: Optional[Path] = None) -> list[NewsSource]:
    """อ่าน watchlist (markdown table) → list[NewsSource]

    รูปแบบแถว:
        | # | แผนก | ชื่อ | URL | โหมด | สถานะ |
    ข้ามแถวที่ไม่มี URL หรือสถานะไม่ใช่ ✅
    """
    p = path or WATCHLIST_PATH
    if not p.exists():
        return []

    sources: list[NewsSource] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cols = [c.strip() for c in line.strip("|").split("|")]
        if len(cols) < 4:
            continue
        # ข้ามแถว header + separator
        if cols[0].lower() in ("#", "ลำดับ") or set("".join(cols)) <= set("-: "):
            continue
        if not cols[0].isdigit():
            continue
        dept, name, url = cols[1], cols[2], cols[3]
        mode = cols[4].lower() if len(cols) > 4 and cols[4] else "rss"
        status = cols[5] if len(cols) > 5 else "✅ active"
        if not url or not url.startswith("http"):
            continue
        if "✅" not in status:
            continue
        sources.append(NewsSource(
            dept=dept, name=name, url=url,
            mode="web" if mode.startswith("web") else "rss",
            active=True,
        ))
    return sources


# ══════════════════════════════════════════════════════════════════════
# Fetchers
# ══════════════════════════════════════════════════════════════════════


def _clean(text: str, limit: int = 400) -> str:
    """ล้าง HTML + whitespace"""
    if not text:
        return ""
    t = re.sub(r"<[^>]+>", " ", text)
    t = re.sub(r"&[a-zA-Z#0-9]+;", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:limit]


def _safe_url(url: str) -> str:
    """เข้ารหัสอักขระไม่-ASCII ใน URL (เช่น คำค้นภาษาไทยใน Google News)

    urllib ส่ง request line เป็น ASCII เท่านั้น → ต้อง encode ก่อน
    ทำให้ Owner พิมพ์คำค้นไทยใน watchlist ได้ตรง ๆ โดยไม่ต้อง encode เอง
    """
    from urllib.parse import quote
    return quote(url, safe=":/?&=%+#@!$'()*+,;~[]")


def fetch_rss(url: str, limit: int = 15) -> list[NewsItem]:
    """ดึง RSS 2.0 / Atom — เร็ว ไม่ใช้ Chromium"""
    req = urllib.request.Request(_safe_url(url), headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
        raw = resp.read()
    root = ET.fromstring(raw)

    items: list[NewsItem] = []

    # RSS 2.0
    for node in root.findall(".//item")[:limit]:
        title = _clean((node.findtext("title") or "").strip())
        link = (node.findtext("link") or "").strip()
        desc = _clean(node.findtext("description") or "")
        pub = (node.findtext("pubDate") or "").strip()
        if not title or not link:
            continue
        items.append(NewsItem(title=title, url=link, summary=desc, published=pub))

    if items:
        return items

    # Atom
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for node in root.findall(".//a:entry", ns)[:limit]:
        title = _clean((node.findtext("a:title", "", ns) or "").strip())
        link = ""
        for ln in node.findall("a:link", ns):
            if ln.get("rel") in (None, "alternate"):
                link = ln.get("href", "")
                break
        desc = _clean(node.findtext("a:summary", "", ns) or "")
        pub = (node.findtext("a:updated", "", ns) or "").strip()
        if not title or not link:
            continue
        items.append(NewsItem(title=title, url=link, summary=desc, published=pub))
    return items


def fetch_web(url: str, limit: int = 15) -> list[NewsItem]:
    """ดึงจากเว็บที่ต้อง render JS — ใช้ Chromium ใน container (47.5MB)"""
    from solocorp_skills.web import WebError, read_url

    try:
        r = read_url(url, wait=14, cols=160, rows=50)
    except WebError as e:
        raise RuntimeError(f"web fetch ล้มเหลวว: {e}") from e

    text = r.get("text", "")
    items: list[NewsItem] = []
    for line in text.splitlines():
        line = line.strip()
        if len(line) < 12 or line.startswith("[") or line.startswith("http"):
            continue
        if len(line) > 200:
            continue
        # เก็บบรรทัดที่ดูเป็นพาดหัวข่าว (มีตัวอักษรผสมไทย/อังกฤษ + เว้นวรรค)
        if len(line.split()) >= 3:
            items.append(NewsItem(title=line, url=r.get("url", url), summary=""))
        if len(items) >= limit:
            break
    return items


def fetch_source(src: NewsSource) -> list[NewsItem]:
    """ดึงข่าวจากแหล่งเดียว (เลือกโหมดตาม watchlist)"""
    if src.mode == "web":
        items = fetch_web(src.url, limit=src.max_items)
    else:
        items = fetch_rss(src.url, limit=src.max_items)
    for it in items:
        it.source = src.name
        it.dept = src.dept
    return items


# ══════════════════════════════════════════════════════════════════════
# Dedupe
# ══════════════════════════════════════════════════════════════════════


def load_seen(path: Optional[Path] = None) -> list[str]:
    """โหลดรายการข่าวที่เคยเห็นแล้ว"""
    p = path or SEEN_PATH
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return list(data.get("seen", []))
    except Exception:
        return []


def save_seen(seen: list[str], path: Optional[Path] = None) -> None:
    """บันทึกรายการข่าวที่เห็นแล้ว (เก็บแค่ N ล่าสุด)"""
    p = path or SEEN_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    trimmed = seen[-_MAX_SEEN:]
    p.write_text(json.dumps({
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "seen": trimmed,
    }, ensure_ascii=False, indent=2), encoding="utf-8")


def dedupe(items: list[NewsItem], seen: list[str]) -> tuple[list[NewsItem], list[str]]:
    """ตัดข่าวซ้ำ — คืน (ข่าวใหม่, seen_ใหม่)"""
    seen_set = set(seen)
    fresh: list[NewsItem] = []
    for it in items:
        k = it.key()
        if k in seen_set:
            continue
        seen_set.add(k)
        fresh.append(it)
    return fresh, list(seen_set)


# ══════════════════════════════════════════════════════════════════════
# Digest
# ══════════════════════════════════════════════════════════════════════


def build_digest(items: list[NewsItem], dept: str = "") -> str:
    """สร้าง digest แบบ markdown (ไม่ใช้ LLM — เร็วและไม่เผาเครดิต)"""
    lines: list[str] = []
    if dept:
        lines.append(f"# ข่าวสาขา {dept} — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    else:
        lines.append(f"# ข่าววันนี้ — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}")
    lines.append("")
    for i, it in enumerate(items, 1):
        src = f" · {it.source}" if it.source else ""
        lines.append(f"{i}. **{it.title}**{src}")
        lines.append(f"   {it.url}")
        if it.summary:
            lines.append(f"   {it.summary[:200]}")
    return "\n".join(lines)


def group_by_dept(items: list[NewsItem]) -> dict[str, list[NewsItem]]:
    """แยกข่าวตามแผนก"""
    out: dict[str, list[NewsItem]] = {}
    for it in items:
        out.setdefault(it.dept or "general", []).append(it)
    return out
