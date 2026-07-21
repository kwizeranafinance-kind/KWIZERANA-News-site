#!/usr/bin/env python3
"""Publish the Kwizerana daily news dashboard into this static site.

The script keeps the latest issue at index.html and preserves each edition as:

    reports/YYYY-MM-DD/index.html

It also rebuilds:

    archive/index.html
    reports/index.html
    archive/manifest.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


DEFAULT_SOURCE = Path(
    "/Users/kwizeranafinance/.gemini/antigravity/scratch/modern-dexscreener/"
    "KWIZERANA_NEWS_DASHBOARD.html"
)

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

NAV_START = "<!-- KWIZERANA_ARCHIVE_NAV_START -->"
NAV_END = "<!-- KWIZERANA_ARCHIVE_NAV_END -->"


def run(args: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, check=check)


def clean_text(raw: str) -> str:
    decoded = html.unescape(raw)
    decoded = re.sub(r"<script\b[^>]*>.*?</script>", " ", decoded, flags=re.I | re.S)
    decoded = re.sub(r"<style\b[^>]*>.*?</style>", " ", decoded, flags=re.I | re.S)
    decoded = re.sub(r"<[^>]+>", " ", decoded)
    return re.sub(r"\s+", " ", decoded)


def extract_report_date(raw: str) -> dt.date:
    text = clean_text(raw)

    version_match = re.search(r"\bv(20\d{2})-(\d{2})-(\d{2})(?:[.\s-]|$)", text, re.I)
    if version_match:
        year, month, day = map(int, version_match.groups())
        return dt.date(year, month, day)

    date_match = re.search(
        r"\b("
        r"January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
        r")\.?\s+(\d{1,2}),?\s+(20\d{2})\b",
        text,
        re.I,
    )
    if not date_match:
        raise ValueError("Could not find a report date in the source HTML.")

    month_name, day, year = date_match.groups()
    return dt.date(int(year), MONTHS[month_name.lower().rstrip(".")], int(day))


def extract_title(raw: str, fallback: str) -> str:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, re.I | re.S)
    if title_match:
        return html.unescape(re.sub(r"\s+", " ", title_match.group(1))).strip()
    return fallback


def strip_existing_nav(raw: str) -> str:
    return re.sub(
        rf"\s*{re.escape(NAV_START)}.*?{re.escape(NAV_END)}\s*",
        "\n",
        raw,
        flags=re.S,
    )


def inject_nav(raw: str, latest_href: str, archive_href: str) -> str:
    raw = strip_existing_nav(raw)
    nav = f"""
{NAV_START}
<div style="position:sticky;top:0;z-index:9999;background:#060810;border-bottom:1px solid rgba(122,150,187,.28);font-family:Arial,Helvetica,sans-serif;">
  <div style="max-width:1120px;margin:0 auto;padding:10px 18px;display:flex;gap:14px;align-items:center;justify-content:space-between;color:#9EB8D4;font-size:13px;">
    <a href="{latest_href}" style="color:#E8F0FF;text-decoration:none;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">Kwizerana Intelligence</a>
    <span style="display:flex;gap:12px;align-items:center;">
      <a href="{latest_href}" style="color:#00D4AA;text-decoration:none;font-weight:700;">Latest</a>
      <a href="{archive_href}" style="color:#9EB8D4;text-decoration:none;">Archive</a>
    </span>
  </div>
</div>
{NAV_END}
"""
    body_match = re.search(r"<body\b[^>]*>", raw, re.I)
    if body_match:
        return raw[: body_match.end()] + nav + raw[body_match.end() :]
    return nav + raw


def date_label(date_iso: str) -> str:
    date_value = dt.date.fromisoformat(date_iso)
    return f"{date_value.strftime('%A, %B')} {date_value.day}, {date_value.year}"


def rewrite_brand_paths(raw: str, prefix: str) -> str:
    """Make brand asset links correct for root or nested archive pages."""
    raw = re.sub(
        r'((?:src|href)=["\'])(?:\.\./)*brand/',
        rf"\1{prefix}brand/",
        raw,
        flags=re.I,
    )
    raw = re.sub(
        r"(url\([\"']?)(?:\.\./)*brand/",
        rf"\1{prefix}brand/",
        raw,
        flags=re.I,
    )
    return raw


def archive_entries(repo_root: Path) -> list[dict[str, str]]:
    reports_dir = repo_root / "reports"
    entries: list[dict[str, str]] = []
    for report_dir in sorted(reports_dir.glob("20??-??-??"), reverse=True):
        index_file = report_dir / "index.html"
        if not index_file.exists():
            continue
        date_iso = report_dir.name
        raw = index_file.read_text(encoding="utf-8", errors="replace")
        entries.append(
            {
                "date": date_iso,
                "label": date_label(date_iso),
                "title": extract_title(raw, f"Kwizerana Daily News - {date_iso}"),
                "url": f"../reports/{date_iso}/",
            }
        )
    return entries


def render_archive_page(
    entries: list[dict[str, str]],
    latest_href: str = "../",
    archive_href: str = "./",
) -> str:
    item_markup = "\n".join(
        f"""      <a class="archive-item" href="{entry['url']}">
        <span class="date">{entry['label']}</span>
        <strong>{html.escape(entry['title'])}</strong>
        <span class="cta">Read report</span>
      </a>"""
        for entry in entries
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kwizerana Intelligence Archive</title>
<style>
:root {{
  --bg: #060810;
  --panel: #0c1120;
  --line: #1a2340;
  --text: #e8f0ff;
  --muted: #7a96bb;
  --cyan: #00d4aa;
  --blue: #0066ff;
  --gold: #f5c542;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background:
    radial-gradient(circle at 10% 0%, rgba(0, 212, 170, .13), transparent 28rem),
    radial-gradient(circle at 90% 5%, rgba(0, 102, 255, .14), transparent 30rem),
    var(--bg);
  color: var(--text);
  font-family: Arial, Helvetica, sans-serif;
}}
.nav {{
  border-bottom: 1px solid rgba(122, 150, 187, .28);
  background: rgba(6, 8, 16, .92);
  position: sticky;
  top: 0;
  z-index: 10;
}}
.nav-inner, main {{ width: min(1120px, calc(100% - 36px)); margin: 0 auto; }}
.nav-inner {{ min-height: 52px; display: flex; align-items: center; justify-content: space-between; gap: 18px; }}
.brand {{ color: var(--text); text-decoration: none; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; font-size: 13px; }}
.nav-links {{ display: flex; gap: 14px; align-items: center; }}
.nav-links a {{ color: var(--muted); text-decoration: none; font-size: 13px; }}
.nav-links a:first-child {{ color: var(--cyan); font-weight: 700; }}
.hero {{ padding: 72px 0 36px; }}
.eyebrow {{ color: var(--cyan); letter-spacing: .22em; text-transform: uppercase; font-size: 12px; font-weight: 800; }}
h1 {{ margin: 14px 0 12px; font-size: clamp(36px, 7vw, 74px); line-height: .95; letter-spacing: 0; max-width: 900px; }}
.dek {{ margin: 0; color: var(--muted); font-size: 18px; line-height: 1.7; max-width: 760px; }}
.archive-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 14px; padding: 20px 0 72px; }}
.archive-item {{
  min-height: 180px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 20px;
  background: rgba(12, 17, 32, .82);
  text-decoration: none;
  color: var(--text);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}}
.archive-item:hover {{ border-color: rgba(0, 212, 170, .75); transform: translateY(-1px); }}
.date {{ color: var(--gold); font-size: 12px; letter-spacing: .1em; text-transform: uppercase; }}
.archive-item strong {{ margin-top: 14px; font-size: 19px; line-height: 1.35; }}
.cta {{ margin-top: 18px; color: var(--cyan); font-size: 13px; font-weight: 800; }}
@media (max-width: 640px) {{
  .nav-inner {{ align-items: flex-start; flex-direction: column; padding: 14px 0; }}
  .hero {{ padding-top: 44px; }}
}}
</style>
</head>
<body>
  <nav class="nav">
    <div class="nav-inner">
      <a class="brand" href="{latest_href}">Kwizerana Intelligence</a>
      <div class="nav-links">
        <a href="{latest_href}">Latest</a>
        <a href="{archive_href}">Archive</a>
      </div>
    </div>
  </nav>
  <main>
    <section class="hero">
      <div class="eyebrow">Daily News Archive</div>
      <h1>Past Kwizerana newsletters, preserved.</h1>
      <p class="dek">Every daily report is saved as a dated edition while the newest report stays live on the homepage.</p>
    </section>
    <section class="archive-grid">
{item_markup}
    </section>
  </main>
</body>
</html>
"""


def rebuild_archive(repo_root: Path) -> None:
    archive_dir = repo_root / "archive"
    reports_dir = repo_root / "reports"
    archive_dir.mkdir(exist_ok=True)
    reports_dir.mkdir(exist_ok=True)

    entries = archive_entries(repo_root)
    (archive_dir / "manifest.json").write_text(
        json.dumps(entries, indent=2) + "\n",
        encoding="utf-8",
    )
    archive_html = render_archive_page(entries, latest_href="../", archive_href="./")
    (archive_dir / "index.html").write_text(archive_html, encoding="utf-8")
    reports_html = render_archive_page(entries, latest_href="../", archive_href="../archive/")
    (reports_dir / "index.html").write_text(reports_html, encoding="utf-8")


def normalize_report_pages(repo_root: Path) -> None:
    reports_dir = repo_root / "reports"
    for report_file in reports_dir.glob("20??-??-??/index.html"):
        raw = report_file.read_text(encoding="utf-8", errors="replace")
        normalized = inject_nav(
            rewrite_brand_paths(raw, "../../"),
            "../../",
            "../../archive/",
        )
        if normalized != raw:
            report_file.write_text(normalized, encoding="utf-8")


def seed_history(repo_root: Path) -> int:
    result = run(["git", "log", "--format=%H", "--", "index.html"], cwd=repo_root)
    written = 0
    seen: set[str] = set()
    for commit in result.stdout.splitlines():
        show = run(["git", "show", f"{commit}:index.html"], cwd=repo_root, check=False)
        if show.returncode != 0 or not show.stdout.strip():
            continue
        try:
            report_date = extract_report_date(show.stdout)
        except ValueError:
            continue
        date_iso = report_date.isoformat()
        if date_iso in seen:
            continue
        seen.add(date_iso)
        target = repo_root / "reports" / date_iso / "index.html"
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            inject_nav(rewrite_brand_paths(show.stdout, "../../"), "../../", "../../archive/"),
            encoding="utf-8",
        )
        written += 1
    return written


def copy_brand_assets(source: Path, repo_root: Path) -> None:
    source_brand = source.parent / "brand"
    target_brand = repo_root / "brand"
    for name in ("KWIZERANA_MARK_TRANSPARENT.png", "KWIZERANA_LOGO_TRANSPARENT.png"):
        src = source_brand / name
        if src.exists():
            target_brand.mkdir(exist_ok=True)
            shutil.copy2(src, target_brand / name)


def publish(source: Path, repo_root: Path) -> str:
    if not source.exists():
        raise FileNotFoundError(source)

    raw = source.read_text(encoding="utf-8", errors="replace")
    report_date = extract_report_date(raw)
    date_iso = report_date.isoformat()

    copy_brand_assets(source, repo_root)
    (repo_root / "index.html").write_text(
        inject_nav(rewrite_brand_paths(raw, ""), "./", "archive/"),
        encoding="utf-8",
    )

    report_target = repo_root / "reports" / date_iso / "index.html"
    report_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.write_text(
        inject_nav(rewrite_brand_paths(raw, "../../"), "../../", "../../archive/"),
        encoding="utf-8",
    )

    normalize_report_pages(repo_root)
    rebuild_archive(repo_root)
    return date_iso


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--seed-history", action="store_true")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    if args.seed_history:
        count = seed_history(repo_root)
        print(f"Seeded {count} archived report(s) from Git history.")

    date_iso = publish(args.source, repo_root)
    print(f"Published report date: {date_iso}")
    print("Archive rebuilt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
