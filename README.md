# KWIZERANA News Site

Daily KWIZERANA Intelligence newsletter dashboard with a dated archive.

## Structure

- `index.html` is the latest published dashboard.
- `archive/index.html` is the public archive page.
- `archive/manifest.json` is the machine-readable archive index.
- `reports/YYYY-MM-DD/index.html` stores each dated newsletter.
- `reports/index.html` mirrors the archive page for convenience.
- `brand/` contains approved Kwizerana logo assets derived from `kwizeranalogo A.pdf`.
- `scripts/publish_daily_news.py` publishes the latest local dashboard and rebuilds the archive.

## Daily Update

The daily automation runs at 10:00 AM America/New_York and publishes:

```bash
python3 -B scripts/publish_daily_news.py \
  --source /Users/kwizeranafinance/.gemini/antigravity/scratch/modern-dexscreener/KWIZERANA_NEWS_DASHBOARD.html
```

The script:

1. Reads the report date from the newsletter HTML.
2. Updates `index.html` as the latest live report.
3. Saves a dated archive copy under `reports/YYYY-MM-DD/index.html`.
4. Rebuilds `archive/index.html`, `reports/index.html`, and `archive/manifest.json`.
5. Keeps archive pages linked back to `Latest` and `Archive`.

After the script runs, commit and push the changed files.
