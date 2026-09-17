#!/usr/bin/env python3
"""Fetch job listings from public APIs and merge them into docs/listings.csv.

Sources:
  - Adzuna API (requires ADZUNA_APP_ID / ADZUNA_APP_KEY env vars)
  - Job Bank Canada RSS feed (no key required)

Never overwrites a status/notes value a human already set on an existing
row — only appends new rows and refreshes factual fields (title/company/
location) on rows that still exist upstream.
"""

import csv
import hashlib
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "search_config.yaml"
CSV_PATH = ROOT / "docs" / "listings.csv"
LAST_RUN_PATH = ROOT / "docs" / "last_run.txt"

CSV_FIELDS = [
    "id", "source", "title", "company", "location", "country",
    "posted_date", "first_seen", "last_seen", "salary_min", "salary_max",
    "url", "status", "notes",
]

YEARS_EXPERIENCE_RE = re.compile(r"\b([4-9]|1\d)\+?\s*(?:years|yrs)\b", re.IGNORECASE)


def load_config():
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_id(source, natural_key):
    digest = hashlib.sha1(natural_key.encode("utf-8")).hexdigest()[:16]
    return f"{source}:{digest}"


def passes_level_filter(text, exclude_terms):
    text_l = text.lower()
    if any(term.lower() in text_l for term in exclude_terms):
        return False
    if YEARS_EXPERIENCE_RE.search(text_l):
        return False
    return True


def fetch_adzuna(config):
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("Adzuna: ADZUNA_APP_ID/ADZUNA_APP_KEY not set — skipping this source.", file=sys.stderr)
        return []

    rows = []
    exclude_terms = config.get("level_exclude_terms", [])

    for country in config.get("adzuna_countries", []):
        for phrase in config.get("adzuna_search_phrases", []):
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
            params = {
                "app_id": app_id,
                "app_key": app_key,
                "what": phrase,
                "max_days_old": config.get("max_days_old", 3),
                "results_per_page": config.get("results_per_page", 50),
                "content-type": "application/json",
            }
            try:
                resp = requests.get(url, params=params, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except Exception as exc:
                print(f"Adzuna [{country} / '{phrase}'] request failed: {exc}", file=sys.stderr)
                continue

            results = data.get("results", [])
            print(f"Adzuna [{country} / '{phrase}']: {len(results)} raw results")

            for job in results:
                title = job.get("title") or ""
                description = job.get("description") or ""
                if not passes_level_filter(f"{title} {description}", exclude_terms):
                    continue

                company = (job.get("company") or {}).get("display_name", "")
                location = (job.get("location") or {}).get("display_name", "")
                link = job.get("redirect_url") or ""
                natural_key = link or f"{title}|{company}|{country}"

                rows.append({
                    "id": make_id("adzuna", natural_key),
                    "source": "adzuna",
                    "title": title,
                    "company": company,
                    "location": location,
                    "country": country.upper(),
                    "posted_date": (job.get("created") or "")[:10],
                    "salary_min": job.get("salary_min", ""),
                    "salary_max": job.get("salary_max", ""),
                    "url": link,
                })

            time.sleep(1)  # stay well clear of any burst rate limit

    return rows


def fetch_job_bank_canada(config):
    rows = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}

    for noc in config.get("job_bank_noc_codes", []):
        url = "https://www.jobbank.gc.ca/jobsearch/feed/jobSearchRSSfeed"
        params = {"fn21": noc, "sort": "D", "rows": 100}
        try:
            resp = requests.get(
                url, params=params, timeout=30,
                headers={"User-Agent": "Mozilla/5.0 (job-tracker-bot; personal use)"},
            )
            resp.raise_for_status()
            root = ElementTree.fromstring(resp.content)
        except Exception as exc:
            print(f"Job Bank Canada [NOC {noc}] request failed: {exc}", file=sys.stderr)
            continue

        entries = root.findall("atom:entry", ns)
        print(f"Job Bank Canada [NOC {noc}]: {len(entries)} raw entries")

        for entry in entries:
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            updated_el = entry.find("atom:updated", ns)

            title = (title_el.text or "").strip() if title_el is not None else ""
            link = link_el.get("href") if link_el is not None else ""
            updated = (updated_el.text or "")[:10] if updated_el is not None else ""

            if not title or not link:
                continue

            rows.append({
                "id": make_id("job_bank_canada", link),
                "source": "job_bank_canada",
                "title": title,
                "company": "",
                "location": "",
                "country": "CA",
                "posted_date": updated,
                "salary_min": "",
                "salary_max": "",
                "url": link,
            })

    return rows


def read_existing():
    if not CSV_PATH.exists():
        return {}
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["id"]: row for row in reader if row.get("id")}


def merge(existing_by_id, new_rows, today):
    for row in new_rows:
        rid = row["id"]
        existing = existing_by_id.get(rid)
        if existing:
            existing["last_seen"] = today
            existing["title"] = row["title"] or existing.get("title", "")
            existing["company"] = row["company"] or existing.get("company", "")
            existing["location"] = row["location"] or existing.get("location", "")
        else:
            row["first_seen"] = today
            row["last_seen"] = today
            row["status"] = "New"
            row["notes"] = ""
            existing_by_id[rid] = row
    return existing_by_id


def write_csv(rows_by_id):
    rows = list(rows_by_id.values())
    rows.sort(key=lambda r: r.get("first_seen", ""), reverse=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in CSV_FIELDS})


def main():
    config = load_config()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    existing = read_existing()
    print(f"Loaded {len(existing)} existing listings from {CSV_PATH}")

    new_rows = []
    new_rows.extend(fetch_adzuna(config))
    new_rows.extend(fetch_job_bank_canada(config))
    print(f"Fetched {len(new_rows)} candidate listings (post-filter) from all sources")

    merged = merge(existing, new_rows, today)
    write_csv(merged)
    print(f"Wrote {len(merged)} total listings to {CSV_PATH}")

    LAST_RUN_PATH.write_text(
        f"{datetime.now(timezone.utc).isoformat()}\ntotal_listings={len(merged)}\nfetched_this_run={len(new_rows)}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
