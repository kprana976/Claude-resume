# Job Search Automation — Project Notes

This supersedes any earlier briefing doc carried over from Cowork. Current
scope and decisions, as agreed with KP (mechanical engineering student,
York University Lassonde, international student, GTA-based):

## Hard constraints (still in force — not up for silent reinterpretation)
- **Never fabricate work experience, titles, employers, or credentials.**
  Reframing real experience into a posting's language is fine and expected;
  inventing history is not. For an international student, a fabricated
  employment history surfacing in a future PGWP/PR application is a
  misrepresentation risk under IRPA s.40 (5-year inadmissibility), on top
  of the ordinary reference-check/termination risk. This was discussed and
  agreed — not revisited per request each time, but never silently crossed.
- **No LinkedIn automation.** ToS ban risk, and it doesn't help anyway now
  that the tracker below covers the same need without it.
- **Never send anything (emails, applications, submissions) without asking
  first, every time** — having access to a tool or file is not standing
  consent to use it in a given task.
- **No new third-party tools/repos without asking first and explaining
  what they do.**

## Current phase: job listing tracker
Goal: a self-updating feed of active job/co-op/internship postings across
CA, US, AU, UK, and a couple of EU markets, relevant to mechanical
engineering — as a replacement for manually browsing LinkedIn.

Architecture:
- `scripts/fetch_listings.py` — pulls listings from the Adzuna API (needs
  free `ADZUNA_APP_ID`/`ADZUNA_APP_KEY`, set as GitHub Actions repo
  secrets) and the Job Bank Canada public RSS feed (no key needed), merges
  them into `docs/listings.csv`, preserving any status/notes already set
  on existing rows.
- `.github/workflows/refresh-listings.yml` — runs the script on a cron
  schedule (twice daily) and on manual dispatch, commits the updated CSV.
  **Note:** GitHub only fires `schedule` triggers off the repo's default
  branch — this won't run automatically until merged to `main`. Use the
  manual "Run workflow" button to test on a feature branch first.
- `docs/index.html` — read-only dashboard (GitHub Pages) that renders
  `docs/listings.csv` as a filterable/sortable table.
- `docs/listings.csv` is the single source of truth for status tracking
  (New/Applied/Interviewing/Rejected/etc.) — edit it directly (Excel,
  Google Sheets, or a text editor). The dashboard does not write back to
  it; that would create two conflicting copies of the truth.

Adzuna free tier is ~1000 calls/month. Current config (6 countries × 2
search phrases × 2 runs/day) uses ~720/month. The math and the tradeoff
are documented in `config/search_config.yaml` — check it before widening
scope, or the quota silently runs out mid-month.

## Not started yet
- Resume/cover-letter tailoring per posting.
- Cold-email drafting/tracking for recruiters and company HR.
- ATS portal automation (Greenhouse/Workday).

## How to work on this project
- Build incrementally, verify each piece before adding the next.
- Don't touch or reference personal files (resume, contact info) without
  asking first, even if they're already sitting in this repo.
- Don't add scope (more sources, more automation) without checking the
  cost/tradeoff first — see the Adzuna quota note above as the template
  for that kind of check.
