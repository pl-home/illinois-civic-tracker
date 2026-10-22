# Stage A: shared changes and quality checks

> Documentation review: October 22, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

Delivered October 19, 2026, America/Chicago. Start review with `changes.py`,
`change_sources.py`, `change_feed.py`, `tests/test_changes.py` and the dated
`docs/evidence/stage-a.json` receipt. Attribution is in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). No PDF collection/extraction,
model request, email, account or new schedule is introduced.

## Data flow and contract

Existing official indexes / publisher receipts → offline adapters → per-source
QA → atomic `data/change-ledger.json` → one `public_events()` selection →
homepage recent changes, `changes.json` and `changes.atom`. A future digest must
consume that same accepted selection and its revision IDs; sending remains
disabled. These three outputs share event IDs and labels. Existing member cards
remain their separate legacy snapshot views; Stage A does not retroactively
claim their entire historical archive passed the new gate.

The ledger is version 1 / policy `stage-a-1`; projections and completion scopes
carry explicit adapter versions. See [the contract](schemas/changes-v1.schema.json).
`validate_fact`, `reconcile` and `public_events` implement the runtime policy;
the JSON schema describes structural interchange, not factual validation.

| Object | Important fields |
| --- | --- |
| Fact | Source-qualified `key`, kind, jurisdiction, GA/Congress, member references, measure/committee, source date and precision, compact detail, evidence |
| Evidence | Exact official or publisher URL, source retrieval timestamp, raw SHA-256 when retained, adapter binding type |
| Accepted state | Fact semantic fingerprint, current compact fact, active flag, revision reference, first observation |
| Event revision | Stable event ID, unique revision ID, supersedes, prior fingerprint/fact, observed and first-observed times, reason, eligibility, validation/policy |
| Completion scope | Source identity, adapter, jurisdiction/session, checked-at watermark, semantic scope fingerprint, count, initial baseline, removal capability |

Raw hashes, fetch times and cosmetic whitespace do not generate activity.
Historical action fingerprints exclude the current bill title; associated-bill
actions exclude mutable current member associations. Title changes have their
own reviewable fact and never establish a shell-bill finding automatically.
Corrections preserve prior values and stable IDs; returning to an earlier value
creates another revision rather than erasing the intermediate one. Baseline
revision `r0` is quiet; the first correction retains its original fact.

Multiple dated actions on the same day remain distinct. Illinois action history
has no durable action-row ID: normalized date/chamber/text is its conservative
identity. A changed tuple is another source observation; we do **not** guess that
two differently worded actions are one correction or silently erase the older
one. The last-action-only legacy imports remain qualified. Successful future
XML reads now retain full action tuples; the per-bill adapter migration is quiet.

## Completion and coverage boundaries

| Source | Acceptance scope and limits |
| --- | --- |
| Illinois XML | Each successfully parsed bill's own hash/retrieval receipt. FTP listing success alone does not refresh every bill. New bills after the established XML baseline can produce events. Older archive schemas migrate quietly. |
| Illinois floor CSV | Full successful conditional CSV receipt. Nays-only totals remain partial tallies. Historical PDF rows are not recollected or promoted as fresh Stage A facts. Current bounded CSV correction discovery is inherited, not expanded. |
| Congress.gov | Complete member/role pagination receipt; exact bill/amendment URL and session. Unknown cosponsorship join dates stay unknown. Only these complete relationship lists permit absence-based removals, whose effective date remains unknown. |
| Federal floor rolls | Individual successfully parsed official roll/hash receipt. A failed index or detail cannot advance an unfinished detail scope. Historical rows retain their old receipt dates; only the collector's bounded recheck set is fresh. No absence-based vote deletion. Candidate-name ballots are withheld until a separate enum/context adapter exists. |
| Calendars | Parsed official meeting/feed receipt and committee references. Stable official source URLs identify observations. Stage B adds normalized agenda/amendment identities, explicit notice status and reschedule history; see HEARING_TRACKING.md. Senate recurring/changed fallback identities are withheld, not guessed. Missing/expired meetings never imply cancellation. |
| Direct communications | Successful publisher listing, dated exact item URL, configured member association and office/campaign/party attribution. Mixed jurisdictions are separate. Partial/failed and carried items do not advance the source. Link-only sources establish no content baseline. This is not broad county website coverage (Stage C). |
| Media | Current successful feed plus complete relevance screening and matching candidate metadata. No new screening is performed by Stage A. This is attributed headline metadata, not verification of article content or publisher claims. Incomplete screening remains withheld. |

Initial source baselines, parser migrations and exact replay generate no alerts.
Newly observed source dates before the baseline, or indistinguishable on its day
at day precision, remain history. Timestamped posts use their exact instant;
same-day posts after the baseline remain eligible. Other newly found records
older than 30 days are retained as historical discoveries. Undated relationships
are explicitly new *listings*, never asserted to be actions taken today. A new
bill-title inventory entry alone is quiet; a later title correction is reviewable.

## Quality, failure and storage

Checks cover duplicate scope/fact identities, member/jurisdiction/session and
measure references, exact measure/roll URL binding, unknown kinds/roles/choices,
missing evidence, nonnegative compatible tally fields, conflicting replay,
regressed source timestamps and coverage-count changes and disappearance of previously observed scopes. One invalid observation
withholds its entire scope; unrelated sources continue. The previous facts and
successful cursor remain. The bounded exception queue stores hashed scope IDs
and allowlisted codes, never source bodies or model answers. The quality report
gives all current scope outcomes/counts; the existing 96 KiB error journal records
quality recurrence/recovery, keeping these operational failures out of the
activity feed. Missing source rows alone are never deletions of dated history.

`adapter-bound` means validated output of a known source parser with identity
and provenance checks. It is not independent human factual review. Source
hashes are raw receipt identifiers; semantic fingerprints are separate. Changing
an event payload without updating its fingerprint fails the shared publication
gate. This is an integrity contract, not cryptographic protection against an
authorized repository editor falsifying both records and checksums.

The accepted facts, events and cursors commit in **one atomic ledger rename**.
A separate quality report may lag if interrupted; replay regenerates it without
duplicates. Proposed total JSON size is checked before either write against the
existing 20 MB working-data limit; ledger hard limit is 10 MB. On overflow fail
closed with the old ledger retained, requiring a deliberate sharding review,
never history deletion. Exceptions keep 64 entries; accepted revisions are not
pruned. Only 20 latest eligible current revisions reach JSON/Atom and ten HTML
rows, with a shared 32 KB entry / 90 KB combined-view budget that also accounts
for HTML/XML escaping; omitted-size counts remain visible; full history remains compact in the repository. Generated browser artifact
has a runtime 650 KB ceiling. No full articles, HTML, PDFs or duplicate archive
downloads are stored. Longer-term storage growth acceptance remains Stage E.

## Operation

```sh
python -m civic_tracker.changes collect
python -m civic_tracker.privacy
python -m unittest discover -s tests -v
python -m civic_tracker.browse --output .local/site
```

The first command is offline and reads existing data only. Source workflows
daily/federal/Illinois recovery/media invoke it after their existing collection
and before publication, under the existing shared state lock. Pages/CI builds
are read-only and never mutate ledgers or spending. No daily job was dispatched
for this release; live source access and paid media screening were not needed.
Manual direct collector-module calls alone are not transactions: run the offline
changes command before publishing if working outside the workflows.

Troubleshoot `data/change-quality-report.json` first, then match its scope ID to
the detailed scope count or hash it as `digest(scope_id)[:20]`. Review original
source receipts and parser code; do not reset the ledger or relax validation to
turn the status green. Repair unknown adapters with fixtures and bump their
version intentionally. Read-only baseline/replay tests cover all five members.
No private review cursor or user stance is stored publicly.
