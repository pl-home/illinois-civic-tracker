# Individual legislator bill history

October 20, 2026 owner-requested browsing extension. Click a member's name in
their homepage banner, or **More sponsorship & bill activity**, to open
`member-<id>.html`. Each page contains at most 25 entries, with newer/older,
first/oldest and back-to-homepage links. It works without JavaScript. Office,
Facebook and campaign navigation links remain available.

## Scope and evidence

`member_history.py` reads the existing `data/change-ledger.json` at build time.
It rechecks the stored scope/key, shared `validate_fact` contract and semantic
fingerprint for filing, sponsor-role and associated bill-action facts. It does
not read raw archives, scrape sites, invoke models, or create another data index.
Quiet baselines and old discoveries are included as history, never new alerts.
The existing homepage still shows its recent snapshot; history pages read the
broader accepted fact collection rather than that small snapshot's event slice.

Dated facts sort by legislative date and stable source key, newest first. Dates
after the snapshot day are excluded. Every row links official evidence and gives
its source-check date. A bill action is explicitly attributed to the associated
bill, not necessarily the member personally. Ceremonial measures are marked and
included; the homepage's noise treatment remains unchanged. Filing, additions,
removals and other-chamber roles retain their source wording and role/operation.

Unknown-date relationship listings have separate pages, ordered by measure/key,
and say **Date unknown**. Introduction is never substituted for a cosponsorship
join date. Current sponsor listings already represented by a dated filing are
not duplicated. Inactive relationships remain visible as removed when supported
by the accepted ledger, without inventing a removal date.

Coverage is GA104 or Congress119, according to the member. It is not complete
tenure history. Older imported Illinois bills may have only dated role actions
and a last bill update, rather than every intermediate action. Federal bill
actions beyond the collected filing/relationship facts are not invented. Votes, hearings and direct communications remain available on the homepage.
Each member page also has a separate 200-day news column. Collection failures/withheld
source scopes warn that prior accepted history is retained. Invalid stored facts
are withheld and counted. Absence does not establish inactivity.

## Storage and publication

The original ten-file artifact keeps its 650,000-byte budget. Generated member
HTML has a separate 3,000,000-byte budget, for a combined maximum of 3,650,000.
Each dated/undated member section is limited to 100 pages (2,500 entries); growth
past page/byte limits fails the build rather than silently truncating data.
This release currently adds about 2.3 MB of static HTML, downloaded page by page.
There is no additional browser JSON or raw evidence archive. Working JSON remains
bounded at 20 MB. See [completion receipt](evidence/member-history.json) for
measured counts, date ranges and sizes.

`browse.py` only writes explicitly named artifact files. Member IDs are fixed to
reviewed identities, page numbers are bounded, unknown files/symlinks cause a
failure, and only obsolete known generated member pages may be removed from the
output directory. Canonical history and evidence are never deleted. CSP permits
only the local stylesheet; source strings are escaped, and official URLs pass
the shared validation gate. Existing privacy checks cover every emitted page.
The stylesheet link includes its content hash so browser/CDN caches do not keep
an older homepage layout when member-page styles change.

The existing Pages/daily publication builds these pages automatically from the
latest committed accepted facts. Schedules, collector request bounds, inference
budgets, financial/source ledgers and PDF deferral are unchanged. No extra API
or model request occurs during building. This implements a display slice of the
later browsing milestone; full-tenure/topic pages and GA103 backfill remain open.

## Review and verification

Read `member_history.py`, the small `browse.py`/`dashboard.py` integration, and
`tests/test_member_history.py`. Tests cover complete pagination without duplicate
rows, older chronology, all five links, official evidence, unknown dates, removed
relationships, tamper/session/unsafe-URL withholding, escaping, failure warnings,
page/size limits, deterministic artifact contents and generated-output cleanup.
No external source code was newly copied for this extension; it uses our existing
shared fact contract. Existing adaptation notices remain in THIRD_PARTY_NOTICES.

## Member-page news column (October 20 extension)

Every dated and undated page shows up to three screened newsroom reports from
the last 200 days, alongside bill activity on desktop and below it on narrow
screens. Dates, publishers, links, source health and the expandable search
methodology use the shared homepage renderer. Homepage news keeps 90 days.
The source query uses 200 days; the same five bounded feeds, 30 candidates,
exact-case cache and existing inference spending/request guards are reused.
No full article text or new archive is stored. The three newest accepted reports
are retained across the 200-day window; this does not create a comprehensive
news archive. Older 90-day source receipts show an explicit pending-window
notice until refreshed, rather than pretending the broader search succeeded.
The generated HTML allowance rises to 3 MB, with the unchanged 650 KB base and
20 MB canonical JSON limits. See [news evidence limits](MEDIA_REPORTS.md) and
[the news-column receipt](evidence/member-news.json).
