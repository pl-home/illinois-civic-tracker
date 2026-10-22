# Stage B: committee hearing navigation and changes

> Documentation review: October 22, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

Delivered October 20, 2026, America/Chicago, within the boundaries below.
Read this with [CHANGE_FEED.md](CHANGE_FEED.md), the revision 6 vision/plan and
[the completion receipt](evidence/stage-b.json). PDF extraction and new committee
roll-call collection remain deferred. All Stage B parsing and comparisons are
deterministic; no model, paid service or new schedule was added.

## Browse and inspect

The homepage's **Find a committee hearing** section lists accepted notices for
the next calendar month, with day and committee filters and links to the relevant
member's notice. Everything remains readable without JavaScript. Filtering only
changes the hearing view; member votes, sponsorship and committee website links
remain available. No private last-reviewed cursor is published.

Member notices show the precise published committee role, Central time when a
time exists, an explicit date-only/TBA label otherwise, location, official notice,
posting/check dates, expandable bill/amendment agenda and recent observed changes.
Federal roles remain dated reviewed configuration; Illinois roster roles are
matched to the exact member ID. Membership is not attendance or participation.
HTML agenda results are context, never inferred member votes or PDF roll calls.

The new navigation and docket bodies read **accepted hearing facts** from the
shared Stage A ledger, rechecking their schema, source identity and semantic
fingerprint. They do not bypass a withheld scope by rendering its latest raw
snapshot. Last-good notices retain their evidence date and failure warning.
Withheld current observations are disclosed even when no accepted notice remains
inside the month. Existing non-hearing member activity retains its separate
snapshot validation; Stage B does not claim a retroactive universal audit.

## Identity and source coverage

| Source | Stable identity and limits |
| --- | --- |
| Illinois | GA104 + chamber + committee ID + hearing ID from the official detail URL. Date/time/room changes stay on that identity. The detail heading must explicitly name GA104, and agenda bill URLs must match both bill and session. |
| U.S. House | Congress119 + official EventID from the published calendar link. Detail navigation points to that notice; bill-level agenda is not collected from this weekly-listing adapter. |
| U.S. Senate | The checked XML feed has no durable hearing ID. A unique committee-code/subject identity excludes time/room, but duplicate subjects in one feed are ambiguous. A later feed changing the time/date for the same fallback identity is also withheld: it may be a recurring business meeting, not a reschedule. No automatic identity guess, cancellation or merge. Committee sources remain available for unresolved entries. |

The collector uses existing public GET clients, verified TLS and the shared
sequential ILGA-main request gate at least ten seconds apart. The scheduled run
still targets 01:00 Central. Initial Stage B projections use a quiet calendar
adapter migration; historical baselines do not become new activity.

`config/hearings.json` bounds detail attempts at 24 per run (including failures),
missing-hearing rechecks at 12, agenda rows at 200 per detail and separately
verified witness forms at 12. Existing HTTP transient retries remain bounded
inside the same rate gate; a detail-attempt limit is not a promise of only one
wire request per retrying GET. Failed detail attempts are memoized during the run
so another member cannot multiply them. These limits do not expand into a crawler.

Previously tracked recent/upcoming Illinois IDs are rechecked when absent from a
successful listing. A tracked ID still listed but moved outside the display month
is also read, so its old date is corrected rather than left on the calendar.
Recent prior dates have a seven-day lookback; undated tracked notices remain
bounded recheck candidates. Missing/failed listings and page bounds retain old
facts and unfinished source cursors. No absence-based removal of hearing history.

## Exact change meanings

- **Agenda added / removed from published agenda:** a bill/amendment identity
  appears/disappears between two completely parsed agenda tables. Reordering,
  whitespace and repeated mobile/desktop views are quiet. Removal never means
  postponement. Multiple motions on one amendment remain separate compact contexts.
- **Bill explicitly postponed:** an agenda item's official result changes to an
  affirmative postponement. A proposed motion to postpone, a failed motion or the
  word in unrelated prose is insufficient. It does not postpone the whole hearing.
- **Hearing time/date or location changed:** the same stable hearing ID has a new
  published value. A time change alone never establishes an explicit postponement.
- **Canceled / postponed / rescheduled:** an affirmative assertion in an official
  status/notice field, dedicated alert/heading or matching listing row. The source
  assertion and exact hearing ID are retained. Negative statements and generic
  cancellation-policy text do not qualify. A canceled/postponed notice may omit
  its date or agenda without inventing them.
- **Unconfirmed:** an earlier ID disappeared from the checked schedule but its
  detail page still lacks an explicit cancellation/postponement. Missing rows,
  HTTP errors and the end of the date horizon never become cancellation.

These differences are attached to the shared event's stable ID/revision lineage,
source-date precision, first observation and current observation. The new feed,
JSON, Atom and hearing history share the same revision validation. The public
history shows at most three revisions per notice; complete compact history is
retained in `data/change-ledger.json`. Observation time does not establish when
the committee edited a page. An older initial date does not hide a later correction.

## Witness slips

Historical results links are always separate from creation links. A published
creation URL must have a live supported form with the required fields, enabled
submit control and no recognized closed/login-required notice. The tool never
submits that form. An authenticated or signup-only page is not collected.

An open-form link needs a timestamped verification within 24 hours of the source
snapshot, a current matching accepted hearing receipt, a scheduled/rescheduled
status and successful source coverage. Failed, canceled, postponed, unconfirmed
or retained notices suppress it. Whole-calendar failures clear old claims too.
The browser replaces verification older than 24 hours with an official-notice
link even when a saved/static page is stale. The visible label says when the
form was verified; availability may change after that check. No claim is live
account state or a guarantee that a submission will still be accepted.

The known historical examples have witness **results**, not a presently open
form. Synthetic form checks pass; a genuine upcoming open-form acceptance example
remains pending until the sources publish one. Do not present that live gate as
passed merely because empty calendars, fixtures or historical pages parse.

## Operation and handoff

```sh
python -m civic_tracker.calendar_refresh
python -m civic_tracker.changes collect
python -m civic_tracker.privacy
python -m unittest discover -s tests -v
python -m civic_tracker.browse --output .local/site
```

The first command is a manual **calendar-only** refresh/recovery using existing
official sources; it preserves bill/vote archives, media decisions and financial
ledgers. It does not request Congress.gov bill APIs or send mail. The existing
daily/Illinois recovery commands use the same collector. Official changes are
recorded before optional media inference; a later second pass records separately
attributed publications. Source-state workflow locking, once-per-day scheduling,
reservation-before-paid-call and publication stale-revision guards remain intact.
Do not run overlapping manual collectors or bypass their host rate gate.

Troubleshoot `data/calendar-refresh-report.json` for a manual run,
`data/daily-report.json` for scheduled source coverage, and
`data/change-quality-report.json` for withheld scopes. The existing bounded error
journal preserves safe hearing failure codes and official detail IDs; source
bodies and model answers are not logged. A successful build is not proof of a
complete calendar, a live slip form or a new committee vote.

Review code in this order: `hearing_changes.py` (identity/normalization/deltas),
`hearing_collect.py` (bounded paced reads), `hearings.py`/`dashboard_sources.py`
(source shapes), `change_sources.py`/`changes.py` (acceptance/revisions),
`hearing_view.py` (navigation/detail) and `tests/test_hearing_changes.py`.
The small reviewed HTML fixtures come from committees assigned to both Fritts
and Arellano. Their raw-page hashes and historical status are retained; they
establish supported HTML shape, not new activity or current opportunities.

No new external source code was copied for Stage B. It extends our existing
parsers and Stage A shared publication layer; prior attribution remains in
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md). No full HTML/PDF archive is
committed. Public hearing views have a 45 KB budget, at most twelve agenda entries
per displayed notice, and official links for omitted detail. The total browser
artifact retains its 650 KB runtime ceiling and working JSON its 20 MB ceiling.
Year-growth and rollover acceptance remain Stage E; broad county coverage and
digest delivery remain separate stages.
