# Browsing page and historical archive

The October 17 homepage revision is documented in [DASHBOARD.md](DASHBOARD.md). The five-member activity dashboard is now the main page; the original export described below is preserved at `archive.html`. This document describes that historical collection.

On October 17, 2026 the owner brought a basic read-only browser forward into the first release. This supersedes the earlier M1 exclusion of all public-site work. It does not authorize production collection, email schedules, or inference before their gates pass. Full-tenure and topic pages remain later work.

## Initial collection and limits

The initial page renders the already-reviewed 134-item Fritts sponsorship export. All export titles, chief-sponsor columns, last-action dates/chambers/descriptions are retained. The exact 24 ceremonial flags are hidden by default and available with one checkbox. Technical-title flags do not claim a bill was rewritten. No topic labels are inferred from short titles.

Inclusion in this export does not prove original filing or Fritts's exact role. Both remain explicitly unknown, even when a chief-sponsor column names him. This snapshot is historical; importing or rebuilding it creates no new activity, alert or delivery event. October 16 is its review date, not an established retrieval timestamp. Official XML links can show changes newer than the export.

The archive coverage section describes the limits of this export; the separate homepage now includes bounded member activity and committee schedules. Party-site items and Capitol Fax are not displayed. An empty filter result cannot establish inactivity. Public browsing requires no account. Obsidian notes and credentials are never part of the artifact.

## Access and operation

- Public URL after successful GitHub Pages deployment: `https://pl-home.github.io/illinois-civic-tracker/`.
- Search bill number, title, listed sponsor or action. Select a measure type, include ceremonial items, or reset filters. Expand rows for the source fields and official XML link.
- Search/filter state is shareable in the URL. Each item has a stable anchor. An explicit item link reveals that item even if filters would hide it.
- The complete list and details remain usable without JavaScript. JavaScript adds filtering only. There are no external scripts, fonts, analytics, browser storage, model calls or API keys.
- `records.json` is a compact public download with provenance, baseline status, unknown fields and the export hash. It is not a current source feed.

Build from the repository root:

```sh
python -m pip install -e .
python -m civic_tracker.browse --output .local/site
python -m http.server 8765 --bind 127.0.0.1 --directory .local/site
```

Open `http://127.0.0.1:8765/`. The static page also works from a downloaded directory, though browsers may restrict URL state on file URLs. Build output is ignored. Rendering makes no network requests and uses no credentials.

## Implementation and deployment

`config/browse.json` defines this reviewed seed and explicit coverage. `browse.py` validates IDs/dates/counts, rejects duplicate or empty data, escapes all source text, renders static HTML and writes only eight allowlisted files (including the homepage dashboard and its public data). An existing output directory with other files is rejected, preventing an accidental repository or vault upload. `web/` holds the template, styles and small enhancement script. The output contains no copies of source PDFs or raw HTML.

The Pages workflow tests and privacy-checks the source, builds the allowlisted output, and uploads that directory only. Only the deploy job has Pages-write/OIDC permission. It receives no Gmail or OpenRouter secrets, writes no data state and starts no collection schedule. Production collection and delivery remain gated separately in M0_FINDINGS.md.

Tests cover the 134/24 invariants, exact export fields, absent role claims, joint-resolution source links, deterministic builds, size, privacy, escaping, malformed/duplicate/empty imports and output-directory isolation. Browser checks cover filtering, deep links, keyboard/mobile access and coverage notices. Extend the public record schema deliberately when validated production records arrive; do not silently turn this baseline adapter into a live collector.
