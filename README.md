# Claude-resume

Job search automation project. See `CLAUDE.md` for full project notes and constraints.

## Job listing tracker

A self-updating feed of active mechanical-engineering-relevant job/co-op/
internship postings across Canada — built as a LinkedIn-browsing
replacement, using public job-board APIs instead of any LinkedIn
automation (which carries ToS ban risk).

- **Data**: `docs/listings.csv` — the single source of truth. Open it in
  Excel/Google Sheets and use the `status`/`notes` columns to track what
  you've applied to. The automation never overwrites those.
- **Dashboard**: `docs/index.html` — a read-only, filterable/sortable view
  of the same CSV, meant to be served via GitHub Pages (Settings → Pages →
  source: `main` / `/docs`, once this is merged).
- **Refresh**: `.github/workflows/refresh-listings.yml` runs the fetch
  script twice daily and commits the updated CSV. Scheduled triggers only
  fire from the default branch — use the manual "Run workflow" button to
  test before merging.

### One-time setup required
1. Sign up for a free Adzuna developer account: https://developer.adzuna.com/
   (gives you an `app_id` and `app_key` — free tier is ~1000 calls/month).
2. Add them as repo secrets: **Settings → Secrets and variables → Actions →
   New repository secret** → `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`.
3. Job Bank Canada's feed needs no key — it works as soon as this is merged.

Without step 1–2, the tracker still runs on Job Bank Canada data alone;
Adzuna adds broader private-sector Canadian job-board coverage on top of
that (scope is Canada-only for now — see `config/search_config.yaml` to
widen it later).
