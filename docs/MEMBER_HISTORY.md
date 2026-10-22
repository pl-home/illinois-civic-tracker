# Individual legislator bill history

> Documentation review: October 22, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

**October 20 pagination follow-up:** member news now shows five articles per page
with older/newer navigation and a bounded rolling cache of up to 100 screened
reports per member, covering 200 days. Homepage news remains three within 90 days.
This supersedes the earlier three-result member-column limit below. Read
[NEWS_PAGINATION.md](NEWS_PAGINATION.md) for exact-cache checks, gradual screening,
storage bounds and coverage limits. Model request and spending caps are unchanged.

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

## Member-page news and pagination — current October 20 follow-up

Each dated/undated activity page has a five-report news column with navigation to
older coverage within 200 days. The dedicated news pages paginate the same
screened cache, at most 100 metadata records/member. Homepage news remains three
within 90 days. The five queries, 30 candidates, exact-case cache and paid-call
bounds stay unchanged. No full article or complete archive is claimed; old
90-day receipts keep their original window. The 3 MB member/news HTML and 650 KB
base ceilings remain separate. See [NEWS_PAGINATION.md](NEWS_PAGINATION.md),
[MEDIA_REPORTS.md](MEDIA_REPORTS.md) and [the earlier layout receipt](evidence/member-news.json).
