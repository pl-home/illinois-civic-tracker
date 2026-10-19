# Daily website refresh

**Latest October 17 scope update:** the owner authorized recent media reports for all five members and narrow routine Qwen3 32B / DeepInfra relevance screening, with USD 0.02 daily, USD 0.20 weekly and USD 20 lifetime limits. [MEDIA_REPORTS.md](MEDIA_REPORTS.md) describes operation and evidence limits. Older statements excluding routine inference are superseded only for this task; party and legislative inference remain disabled.


The owner authorized daily website updates at **01:00 America/Chicago** on October 17, 2026. This supersedes the earlier 23:00 collection target for the public website. It is a staged daily dashboard release, separate from the still-gated complete M1 digest and later inference activation. The [first hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39043392873) completed and deployed on October 17. Illinois and calendars passed; federal coverage was partial (House Clerk HTTP 503 and one incomplete Congress.gov pagination sequence). Prior facts were retained and failures were published. This is an operational deployment with visible source gaps, not a claim that every source passed. `data/daily-report.json` is the current receipt.

## Operation

`.github/workflows/daily.yml` runs without an AI session or local computer. UTC wakes at 06:00 and 07:00 cover daylight and standard time. `daily.due` uses the Chicago timezone and a persisted local-date ledger: the second wake is skipped after a completed attempt, including the repeated fall-back hour. It also provides catch-up until 06:00 Chicago if a run starts late. GitHub may delay or drop scheduled jobs; the target is collection start, and publication follows collection. Failed/partial attempts publish explicit health, retain prior source facts and are not silently called a clean refresh. Hard workflow failure leaves the last published dates visible. GitHub Actions exposes the failure; no extra email sender or AI monitor is enabled.

The workflow serializes with existing source-state writers, checks out current main inside that gate, tests before source access, scans privacy, builds the eight-file allowlisted artifact, commits source state, then deploys it. A failed state push prevents publication. Both Pages workflows compare the artifact SHA to current main immediately before deployment under the shared Pages lock, preventing an older queued artifact from overwriting newer data. The daily artifact uses the post-refresh commit SHA; push-only publication uses its event SHA.

## Source scope and explicit gaps

- **Illinois bills:** compact public baseline, then the official FTP directory's new/changed entry tokens. Every changed supported measure is examined for the two target members, rather than restricting discovery to the Fritts export. At most 300 changed XML files per run; failures/unprocessed entries retain their old token and are retried on the next run. Historical import is never an event today. Listing tokens are a change-discovery heuristic; corrections that do not change the listing metadata remain a source limitation.
- **Illinois floor votes:** one conditional GET of the official GA104 CSV. Nay counts use the complete file; only monitored choices are retained. Historical PDF baseline remains intact. CSV-derived rows after the verified May 31 baseline use stable source identities; a seven-day overlap around the last CSV date handles corrections. Replaced/removed CSV identities remain in a compact superseded ledger. Unknown choices and source date/motion conflicts are not silently repaired. The choice links to the CSV when an individual roll-call PDF is not yet resolved.
- **Illinois committee votes:** prior verified PDF records remain available. Daily new committee-vote PDF discovery is **not implemented**; this gap is stated on the page. Upcoming meetings, explicit roles and public open-slip checks refresh through the bounded existing committee collectors. Historical/failed schedule evidence does not establish an open submission opportunity; retained hearings have stale submission flags cleared.
- **Federal sponsorship:** Congress.gov member sponsored/cosponsored lists are paginated completely, then filtered to Congress119. A global 500 API-attempt bound and sequential spacing apply. Incomplete pages retain prior relationships and visible failure status. Unknown cosponsorship join dates stay undated. `CONGRESS_API_KEY` is used only in the collection step; no key or authenticated URL is logged or committed.
- **Federal floor votes:** official House/Senate current-session indexes, newly discovered roll-call XML and the last five existing records per chamber. Totals and member identities must reconcile. At most 100 vote-source requests; pending work is partial coverage, never success. Prior-session history remains imported; routine old-session correction sweeps are not provided.
- **Parties, Capitol Fax and email:** not part of this daily website job yet. Routine inference and the weekly digest remain disabled. Facebook/campaign URLs are navigation, not additional crawler targets.

All ILGA/main slip-host requests share the ten-second sequential gate. FTP is preferred. No logged-in pages, outreach, witness-slip submissions or model calls occur. The January 3, 2027 review boundary blocks refresh under stale office/session identities until configuration/source assumptions are reviewed.

## Small persistent state

`data/illinois-index.json` and `federal-index.json` retain selected public bill fields and monitored vote choices, without raw HTML/XML, PDF text or contact details. The initial baselines are approximately 3.9 MB and 2.1 MB. `collection-state.json` holds listing tokens, CSV validators/corrections and the local-date ledger. The total JSON working-state cap is 20 MB; the larger project budget remains below 100 MB. Raw responses are temporary runner scratch, not Git history or the Pages artifact. Only the bounded dashboard snapshot is served on Pages; the public repository also holds the compact source indexes for reproducibility.

`daily-report.json` contains the latest bounded health report; Git history preserves prior committed reports. Source observation, legislative date, compilation date and daily-attempt time remain distinct. A fresh check does not mean a new action occurred. Per-source failure preserves last-good facts; partial calendar failures retain upcoming prior meetings with a warning. Empty/regressed CSV responses cannot poison the watermark. No source ledgers are reset to obtain a clean result.

## Review and next work

Read `daily.py`, then `daily_state.py` / `daily_federal.py`, `dashboard_collect.py` and one `daily-report.json`. Tests cover DST/catch-up/date deduplication, pagination failure isolation, identity/tally reconciliation, corrected CSV evidence/retired identities, malformed CSV watermark protection and partial calendar retention. The full suite currently has 105 tests. Production M1 acceptance is still qualified: daily committee votes, live upcoming/slip evidence, exact role/index review, post-veto cadence, deterministic topic reasons, digest rendering/delivery idempotency and growth simulation remain open.

## Initial deployment evidence

Implementation `d808aa0`; persisted daily records `2ad84a3`. The first run processed 24 changed/recheck FTP entries, fetched the official floor CSV (latest vote still May 31), made 44 Congress.gov API requests and seven federal vote-source requests, and refreshed 37 committee/calendar source receipts. No matching upcoming meetings were posted. All five member cards retained source-specific dates. Working JSON state was 7,043,154 bytes, with no raw source dumps published. Both refresh and Pages deploy jobs succeeded. Two federal failures remain qualified; no second collection was launched just to replace that receipt. The next scheduled attempt will recheck them. Per-source timing/progress logs were added for later runs.

The 105-test suite and privacy scan pass. Regression examples are frozen test inputs, so a later vote or changed committee role does not make CI depend on an old homepage row remaining in the rolling window. Compact validation is in `docs/evidence/daily-refresh-validation.json`.


## Federal source recovery (October 17)

The daily workflow and manual `federal.yml` prefer the repository secret
`CONGRESSGOV_API`, with `CONGRESS_API_KEY` retained as a legacy fallback. Values
are available only inside the official-source step; never include them in a
report or authenticated source URL in a log.

`python -m civic_tracker.daily federal` rechecks federal sources and rebuilds
only the three federal members' activity. It preserves calendar/news/AI usage
metadata and the once-per-day ledger. The prior Federal failure receipt and the
new report are retained in `data/federal-recheck-report.json`; the detailed
report also replaces only Federal in the current daily health report. The
original whole-run timestamp remains unchanged, with `source_recheck_at`
recording the later targeted check. Old failures remain in Git history.

The Clerk's unpaged MemberVotes endpoint returned HTTP 503. Discovery now starts
at explicit `Page=1` and reads every official ten-card page. Each page must match
its stated range, stable total and year-specific vote links; the combined IDs
must be unique and contiguous before any roll-call XML is selected. A changed
page size or inconsistent index fails closed. The first, second and final page
were checked against the live 314-result listing before hosted recovery.

All network attempts, including at most three retries, count against the same
500 Congress.gov / 100 vote-request bounds. Transient transport failures and
HTTP 408/429/500/502/503/504 receive bounded backoff. Permanent errors are not
retried. Retry-After integer delays above 60 seconds stop retries. Reports show
safe error codes plus member-role/page context, without transport messages or
API query strings. Recovered retries remain in `recovered_requests`.

Congress.gov member lists have no documented Congress filter, so collection
still reads the complete career list and filters Congress 119 locally. Stable
integer pagination counts, matching total rows and validated legislation IDs are
required before removing an absent prior sponsorship association. An exact-payload
duplicate within one page is deduplicated and recorded in `duplicate_source_rows`;
conflicting records or records repeated across pages fail closed. Incomplete
responses retain prior links. The federal-only workflow shares the source lock,
checks unchanged financial/collection ledgers, runs tests/privacy checks and
publishes its own SHA-guarded Pages artifact. It has no model or email secret.


The first hosted recovery (run 39050646833) completed all 32 House index pages
(314 rolls), revalidated five House and five Senate XML records, and completed
Durbin's 43-page career cosponsorship list. It retained Duckworth's roles after
the stronger guard found a duplicate. A separate read-only diagnostic (run
39051429275) verified Congress.gov repeated the identical Congress 118 S38 row
inside page 1 of Duckworth's sponsored list. No source body or credential was
stored in that diagnostic; only identity and equality checks were reported.

Manual recovery can use `python -m civic_tracker.daily federal --failed-only`.
It reuses sibling checks only if the six named role lists and two complete vote
indexes are present, the report is at most six hours old, and every error belongs
to an incomplete API role. Otherwise it performs a full federal refresh. Reused
sources retain their check times; whole-report/archive freshness stays at the
oldest source check. `latest_attempt_at`, `attempt_scope` and `reused_sources`
describe the targeted attempt. Request counts describe this attempt, while the
prior report is preserved in the recheck receipt. The daily schedule always
runs a full federal collection. The workflow's optional diagnostics input calls
`python -m civic_tracker.daily_federal diagnose` with read-only repository access
and does not publish or write source records.


Recovery completed and deployed in [run 39051718651](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39051718651).
All six member-role sources and both vote indexes are complete; overall source
health is `ok`. The targeted retry used three free API requests and reused the
seven successful sibling checks with their original timestamps. Financial and
once-per-day collection files are byte-identical to before recovery. The live
homepage displays Illinois/Federal/Calendars `ok` and neither original error.
The full 153-test suite and privacy guard passed. See
[evidence/federal-recovery-validation.json](evidence/federal-recovery-validation.json).


## October 19 Illinois source recovery

The October 18 hosted run retained records after the floor CSV and both Illinois
member pages failed. Their old diagnostics contained only `HTTPError`, so the
original HTTP statuses cannot be reconstructed from that receipt. On October 19
all three endpoints returned HTTP 200 from the development computer; a separate
hosted recovery verifies runner access before claiming resolution.

The shared HTTP client now makes at most three attempts for temporary network
errors and HTTP 408/429/500/502/503/504. Every attempt re-enters the same source
rate gate; main-site spacing remains at least ten seconds. A Retry-After above
60 seconds stops retries, and permanent 403/404 responses are not bypassed.
Reports preserve safe `HTTP_NNN` codes and successful request-attempt counts.

The `illinois-recovery.yml` manual workflow refreshes Illinois facts and calendars,
retains the previous health receipt, and restores prior calendars after failures
with witness-slip submission flags cleared. Federal API records and financial
ledgers must remain unchanged. It refreshes the displayed usage period without
making model calls. It does not enable the unfinished committee code.

Hosted recovery completed and deployed in [run 39334966772](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39334966772).
Illinois and Calendars are both `ok` with zero source errors as of
2026-10-19T22:26:42Z. The floor CSV returned HTTP 200 on its first attempt; the
member pages and committee calendars completed successfully. The previous
October 18 receipt remains in `data/illinois-recovery-report.json`.
Federal source timestamps remain unchanged. Historical committee PDF coverage
is retained; daily committee roll-call collection is still pending.
