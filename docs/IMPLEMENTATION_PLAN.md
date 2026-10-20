# Illinois Civic Tracker: implementation plan

Revision 7 — October 20, 2026, America/Chicago. Read with
[PRODUCT_VISION.md](PRODUCT_VISION.md), revision 7. This replaces the initial
October 15 plan as current delivery guidance. Earlier plans/build briefs remain
historical acceptance evidence; their obsolete schedule, private-server proposal,
M1 exclusions and exactly-once-mail claims do not override this revision or later
owner instructions.

The [published planning copy](https://github.com/pl-home/illinois-civic-tracker/blob/main/docs/IMPLEMENTATION_PLAN.md)
and workspace copy share the same content. This plan sequences work; it does not
declare proposals implemented or enable any workflow/model task. Code, current
configuration and dated collection reports establish actual operating state.

## 1. Baseline and remaining scope

As of the October 19 release, the public website, GitHub-hosted daily official
collection, limited media screening and direct-communications sections are
implemented. State/federal source health, configured calendars/roles, budgets and
privacy checks are visible. A structured error journal has recurrence/recovery
tracking and a 96 KiB live cap. The pre-Stage A implementation had 198 passing offline tests
in the latest recorded local validation; that dated count is not a substitute
for future CI or full product acceptance.

| Area | Verified implementation boundary | Remaining work |
| --- | --- | --- |
| Illinois | Session-wide changed XML discovery; selected member roles/actions; floor CSV; retained history; shared Stage A changes | Stronger relevance/coverage acceptance and correction sweeps within source bounds |
| Federal | Congress.gov relationships and official current-session floor XML, with retained prior history | Service/session transition and deeper historical/committee coverage |
| Individual member history | October 20 owner request: paginated accepted current-session bill activity, names linked from homepage; separate undated relationship listings | Full-tenure/topic pages, applicable GA103 backfill and deeper source completeness remain M5 |
| Hearings | Stage B: day/committee navigation; accepted agenda/amendment history, explicit status changes, bounded missing-ID rechecks and stale-slip protection | Genuine upcoming/open-form live acceptance; stronger Senate hearing IDs and broader federal agenda coverage |
| Media/communications | Visible discovery policy; up to three dated eligible newsroom items; separate attributed first-party sources | Remaining source gaps/reprints and dedicated Capitol Fax/Lee County mention acceptance |
| County parties | Legacy bounded watcher; selected member-filtered party feeds in current communications | Port broad hosted website change coverage with equal rules and baseline suppression |
| Health | Source reports, privacy checks, bounded error journal and usage accounting | Cross-record integrity, coverage and withheld-record QA |
| Notifications | One-time Gmail transport/inbox proof, not a recurring digest | Preview, event selection, conservative send ledger and weekly acceptance |
| PDF/committee extraction | Historical records plus failed, separately versioned manual trial receipts | Deferred by owner; no routine activation or further paid trial in this workstream |

The current codebase is the public `pl-home/illinois-civic-tracker` repository.
The previous Obsidian implementation is a read-only historical/private resource,
not the active scheduled runner. Preserve paused work and archives; do not copy
the vault or secrets into the public repository.

## 2. Current architecture to preserve

Use small Python adapters, compact public JSON and a generated static website.
Keep existing modules as working inputs rather than replacing all collectors:

| Responsibility | Current implementation starting points |
| --- | --- |
| Scheduling/source orchestration | `daily.py`, `config/daily.json`, `.github/workflows/daily.yml` |
| Illinois/federal normalization | `daily_state.py`, `daily_federal.py`, `vote_csv.py` |
| Hearing parsing/display | `hearings.py`, `dashboard_collect.py`, `dashboard.py` |
| Media and direct statements | `media.py`, `communications.py`, reviewed source configs |
| Build/privacy/health/accounting | `browse.py`, `privacy.py`, `error_journal.py`, `usage.py` |

Implemented Stage A flow: source adapters → validated compact facts → material-change ledger
→ shared website/JSON/Atom gate. Broader inclusion rules, digest rendering and
gated delivery remain planned.
One event may appear in several views; it must not become several notifications.
Private positions and annotations remain separate from refreshed public facts.

Keep 01:00 America/Chicago collection and existing source/Pages locks. Do not add
a second collector schedule, reactivate Codex/Windows tasks, or switch to a new
hosted database to implement the following stages. The Monday 06:00 digest target
is still a planned channel, not an active schedule.

## 3. Delivery sequence and acceptance gates

Stages A and B are delivered within their coverage boundaries below. The next
implementation slice is **Stage C hosted party coverage and relevance**, while
genuine live hearing/slip acceptance remains source-dependent. PDF work stays deferred.
Stage C can prepare independent source coverage
without waiting for PDF work. Stage D consumes the same accepted events. Session
review in Stage E is date-sensitive and must not wait for M1 completion.

### Stage A: common change contract, ledger and publication gate

**Delivered October 19:** the source-scoped ledger, shared homepage/JSON/Atom gate,
quiet baseline/replay, revision/removal history, exception queue, journal hook and
size checks are implemented. See [CHANGE_FEED.md](CHANGE_FEED.md) and the
[completion receipt](evidence/stage-a.json). Existing member cards remain legacy
snapshot views; the new shared gate covers the new feed. Candidate-name House
ballots are withheld; complete historical correction coverage, detailed hearing
revision acceptance and broad county website monitoring remain later work. No
model calls, PDF retry, digest or new schedule was enabled. Actual adapted source
is now disclosed in [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).

**Outcome:** a durable, explainable feed of changes from existing verified sources.
This implements the earlier “Since my last review” idea and the core M1 digest
input. Existing indexes/snapshots remain authoritative facts while this layer is
introduced and checked in parallel.

1. Define versioned fact, event, evidence and coverage schemas. Use jurisdiction,
   session and source-qualified identities; bill number alone is insufficient.
   A stable event identity must survive revisions. Keep semantic fingerprints
   separate from raw-source hashes and observation time.
2. Record event type, related member/measure/committee, occurred date/time and
   precision, first observation, source references, validation outcome, inclusion
   reason, and revision/supersession links. Do not invent dates or a unique match
   when source identity is ambiguous.
3. Compare successful source observations to produce filing, sponsor-role changes,
   recorded choices, hearing updates and separately attributed publication events.
   Preserve multiple meaningful same-day actions. Unknown changes go to a small
   exception queue; a missing field is not silently normalized away.
4. Track completion/watermarks per source. Incomplete pagination, missing files or
   failed parsing cannot remove prior relationships or advance unfinished work.
   Confirmed removals create history; they do not erase covered-service facts.
5. Suppress initial imports, parser migrations and unchanged observations as new
   activity. Meaningful title/subject changes need reviewable rules; do not copy
   Hawaii's title-only suppression without considering our rewrite requirement.
6. Introduce one validation/publication policy used by website, exports and digest.
   Distinguish import/structural checks from factual source validation, reporting
   and publisher attribution. A manually set status or URL prefix cannot establish
   truth. Keep last-good facts visible with their dates; explain withheld items.
7. Render a source-dated recent-changes view, then deterministic Atom/RSS and compact
   JSON slices if useful. Keep event IDs stable across feed rebuilds and labels
   consistent. A private “last reviewed” cursor must not become public user data.

**Required QA:** duplicate identities, broken internal references, source/session/
member mismatches, incompatible choices/tallies, missing roles, unknown enums,
source regression and coverage changes. Check before publishing replacement facts.
Keep operational errors in the existing journal; don't dump source bodies or
model answers into a new diagnostics channel. Nonzero counts alone are not a
complete/healthy result. Some unexpected changes should warn or quarantine, not
prevent unrelated healthy sources from updating.

**Acceptance:** reviewed examples for both Illinois members and federal sources;
initial baseline emits no “today” events; unchanged replay adds no events/feed
items/mail; multi-action and role-removal histories survive; corrected source
updates remain linked; duplicates across views share one identity; a failed source
retains its facts and unfinished watermark. Health/run timestamps may change on
an unchanged run without representing legislative activity. All shared publication
paths reject the same invalid examples.

### Stage B: hearing navigation and revision history

**Delivered October 20:** day/committee filters and source-validated notice detail;
normalized bill/amendment agenda deltas; same-ID time/location revisions; explicit
hearing cancellation/postponement and item-level postponement; bounded missing-ID
rechecks; retained last-good facts; timestamped/expiring witness-form claims.
See [HEARING_TRACKING.md](HEARING_TRACKING.md) and [the receipt](evidence/stage-b.json).
The paced October 19 calendar check returned zero matching upcoming hearings and
zero source errors; historical HTML from both Illinois members' committees and
synthetic transitions establish parser/replay behavior. A genuine upcoming open
form and real live status transition remain pending, not silently passed. Senate
feed identities with ambiguous recurrence/time changes are withheld. No PDF,
new model task, paid call, digest or schedule was enabled.

**Outcome:** actionable next-month hearings with reliable evidence and update history.

1. Extend existing HTML/calendar adapters; PDF extraction is not a prerequisite.
   Use official hearing identifiers where available. If no durable source identity
   is exposed, document a conservative fallback and ambiguity behavior; time/room
   alone must not create a new hearing when rescheduled.
2. Store compact hearing revisions and agenda bill/amendment identities. Distinguish
   agenda additions/removals, changed room/time, bill postponement and meeting
   cancellation. Mere reordering or cosmetic edits should not generate false alerts.
3. Generate day/committee navigation and compact detail with member role, notice,
   local time/room, agenda, official bill links and source-specific health. Source
   precision/unknown time remains explicit; do not invent a duration or attendance.
4. Verify public witness submission forms separately from results links. Clear an
   open-submission claim on stale/failed validation. Never submit a slip.

**Acceptance:** fixtures for new baseline, unchanged agenda, added/removed item,
amendment identity, rescheduled same hearing, explicit postponed/canceled notice,
failed/empty listing and stale slip flag. A missing row from incomplete coverage
does not become cancellation. A genuine upcoming submission example must be
validated when available; historical results alone cannot pass that gate.

### Stage C: hosted party coverage and deterministic relevance

**Outcome:** both Lee County organizations receive equivalent, bounded monitoring,
with attributed changes suitable for the same feed and digest.

Port reviewed page lists/parsers, not the old runner, full archives or local-model
review. Keep first-party feed and broad website coverage distinct. Suppress new
page baselines and cosmetic/parser changes. Preserve genuine officer/contact,
event/meeting, candidate/endorsement and position-statement changes with source
and observation dates. Bound any exceptional snapshots under Tier C; an image
change requiring human review remains unresolved without inventing its content.

Finish deterministic topic/inclusion reasons: committee/statute structure before
keywords, ceremony/noise audits and a visible show-hidden path. Keep topic and
stance separate. Preserve news versus direct communications and dedicate a bounded
mention-coverage check for Capitol Fax/Lee County if general news discovery does
not establish it. No full articles or new model classification are required.

**Acceptance:** equivalent party fixtures/rules, baseline/parser/cosmetic silence,
meaningful attributed changes, stale/failure recovery and exact inclusion reasons.
The 134-item Fritts export is a historical regression fixture, not a discovery
whitelist. Arellano monitoring must not depend on obtaining an equivalent export.

### Stage D: digest preview, then safe delivery

**Outcome:** the planned Monday 06:00 Central owner digest, using accepted events.

1. Build HTML plus plain text from the shared ledger and source coverage, not an
   independent summary scraper. Include the next roughly ten days of verified
   opportunities, noteworthy member activity, attributed parties/media and health.
   Every inclusion needs a reason and source link. Quiet weeks still report checks.
2. Separate source-event date, first observation, digest eligibility and delivery
   state. A recovered source's old backfill must not flood the digest as new action.
   Record the exact event/revision selection and window used by each preview.
3. Render deterministic previews with sending disabled. Validate sections, dates,
   HTML escaping, link targets, partial-source language, sparse news and privacy.
4. Implement an owner/period delivery ledger with durable reservation before send,
   attempt identity, sent/failed/uncertain outcomes and an acknowledgment/recovery
   procedure. Retain original attempts. Commit failure must prevent an unreserved
   send. Repeated triggers must not rebuild “not sent” state for the same digest.
5. Use the already selected Gmail transport and configured recipient secrets.
   SMTP acceptance is not inbox confirmation; a crash can leave an uncertain
   outcome. Do not automatically retry uncertainty or promise exactly-once SMTP.
   Do not replace this ledger with BILLinois' user boolean, RepWatchr's queue row
   or FloorVote's last-digest timestamp.
6. Enable a recurring workflow only after preview and controlled delivery gates
   pass. This reconciliation does not deploy or run it. Preserve shared source
   locking, Chicago/DST/delay behavior and no-outreach boundaries.

**Acceptance:** normal/quiet/partial-source previews; unchanged/repeated trigger;
concurrent trigger; failure before reservation push; provider rejection; accepted
send with failed acknowledgment; controlled inbox proof; recovery without silently
replaying uncertainty. Log no recipient/sender values, keys or raw provider text.
No message goes to a legislator, campaign, party or third party automatically.

### Stage E: measured storage, correction coverage and rollover

Keep permanent compact Tier A/B history; window/shard generated detail instead of
copying Hawaii's destructive three-year retention. Measure working JSON, browser
payload, evidence retention and cumulative Git growth in a simulated year against
existing limits. Git releases/snapshots are a possible later export mechanism,
not permission to delete history or add a raw local mirror.

The October 20 owner-requested member-history pages implement one bounded display
slice now, without moving M5 discovery/backfill forward. Accepted existing facts
are paginated 25 per page, with a separate undated section and evidence/coverage
labels. Base public files retain their 650,000-byte ceiling; generated member
HTML has a separate 2,000,000-byte ceiling (2,650,000 combined), at most 100 pages
per member/section. Canonical working JSON stays at 20 MB. Size growth fails
closed; no raw files, old evidence or financial/source ledgers are deleted.
See [MEMBER_HISTORY.md](MEMBER_HISTORY.md) and its completion receipt. No workflow,
schedule, collector, PDF task or model permission changes are part of this slice.

Plan bounded deeper correction sweeps where current source discovery heuristics
miss unchanged listing metadata or old records. Incomplete sweeps remain explicit
and respect access budgets. Retain raw-value conflicts; do not improve comparison
rates by discarding amendment/motion identity or equating unknown vote codes.

Before the January 3 review guard, verify configured service/session/committee
identities and source shapes for the transition. Preserve outgoing members and
their history; add successors only from verified configuration. Do not reenable
the old schedules or postpone rollover behind a later feature milestone.

## 4. Reuse register and implementation boundaries

Permission to adapt code with disclosure is recorded from the owner's instruction.
The following remain candidates except the specific Stage A feed adaptation
recorded in [the attribution register](../THIRD_PARTY_NOTICES.md).
For each actual adaptation add a provenance entry containing repository, source
path, full revision, applicable notices, changes and our acceptance tests. Keep
third-party code separated enough for a programmer to identify and review it.

| Reference | Candidate contribution | Exclude or redesign |
| --- | --- | --- |
| [Hawaii Tracker](https://github.com/Hawaii-Appleseed/Tracker), reviewed b244e82 | `tracker/legislative/db.py` change log; `feeds.py`; small search/history payloads | Three-year canonical-history deletion; local launchd/WAF assumptions; blanket title-edit suppression |
| [GovTrack](https://github.com/govtrack/govtrack.us-web), 074043e | Stable event/source relationship and multiple feed views | Full Django stack; deletion on incomplete event regeneration; coarse grouped changes |
| [BILLinois](https://github.com/CaitlinCP/BILLinois), a1cd722 | Bill timeline/watchlist UI, email templates, optional pure keyword helper | Open States as primary authority; latest-action-only notifications; queue reset/resend; transport/key logging |
| [RepWatchr](https://github.com/RealRyanNichols/RepWatchr), 4d40d29 | Evidence labels, withheld-record reasons, source gaps and corroboration checks | Inconsistent loader gates, URL/status-as-proof, political scoring, broad commercial infrastructure and unclaimed mail sends |
| [Alaska Legislative Data](https://github.com/ShipCreekGroup/alaska-legislative-data), 33e044c | Identity/reference QA and reusable compact exports | Private database dependency, statewide mirroring and destructive source reconciliation |
| [Chicago Councilmatic](https://github.com/datamade/chi-councilmatic), 0f3c9d5; [scrapers](https://github.com/datamade/chicago-council-scrapers), f142a76 | Hearing/agenda navigation, member/committee feeds, independent QA checks | Large server/database stack, unlimited scraping and summary-model jobs |
| [Open States scrapers](https://github.com/openstates/openstates-scrapers), bafdd90 | Illinois action vocabulary, source-linked adapters and comparison examples | Disabled TLS verification; time/location-based meeting identities; current-list-as-history assumptions |
| [OLIS dashboard](https://github.com/bphelps1/olis-daily-dashboard), ac75335 | Agenda drilldown and explicit deterministic flag definitions | Oregon API/browser-fetch assumptions, invented meeting duration and inappropriate party thresholds |
| [PolicyEngine tracker](https://github.com/PolicyEngine/state-legislative-tracker), 1017ae8 | Explicit processing stages and ordinary-rerun deduplication | Session-less first-pass bill identity, aggregator-as-official URL, automatic AI scores and simulation/database stack |
| [FloorVote](https://github.com/floorvote/floorvote), a6ba0d2 | Separate shared ingestion from subscriber presentation | New cloud/AI stack or advertised cost estimate; timestamp-only delivery acknowledgment |
| [unitedstates/congress](https://github.com/unitedstates/congress), 8184bcb | Selected official federal calendar/identity parsers | Bulk archives, outdated endpoint assumptions and time-based reschedule identity |

Use our source access client, verified TLS, sanitization and spending rules around
any adapted component. Attribution does not establish factual accuracy or acceptance.
No new accounts, paid services, AI classifiers or public issue-creation bot are
required to complete Stages A–D.

## 5. Milestone mapping and deferred work

Stages A–D complete the still-open core M1 product; Stage E supplies ongoing
storage/coverage acceptance and M3 transition readiness. M0 evidence remains
qualified by its samples and elapsed/live-source observations. Basic website
browsing and selected federal/media collection were explicitly brought forward;
do not label them future-only M5/M4 work or declare all of those milestones done.

M2 rewrite detection needs amendment/version evidence and must distinguish a
faithful replacement amendment from an unrelated subject substitution. The phrase
“replaces everything after the enacting clause” is not conclusive. M4's deeper
federal committee participation, M5's full-tenure/topic pages/backfill and M6's
private contact packets remain separate. Existing committee assignments and future
meetings do not establish participation. No political stance or attendance is
inferred to fill a gap.

PDF extraction and daily new committee-vote discovery remain deferred. Preserve
historical coverage, failed trial receipts and the unsettled earlier charge hold.
Do not spend on another trial or enable routine committee inference through this
documentation change. Remaining non-PDF work can proceed with that gap explicit.

## 6. Completion receipts and status maintenance

For each delivered slice, record changed modules, adapted-source provenance,
fixtures/checks, coverage limitations, storage impact, workflow effects and actual
cost if any. Tests should exercise meaningful failure/replay boundaries rather
than duplicate implementation. Publish only the bounded public artifacts intended
for the website; never private vault material or local review archives.

Source-specific reports, the journal, usage/cost ledgers and hosted run receipts
remain evidence. Keep this plan's implemented/planned states and README entry
points synchronized; preserve old documents as history instead of leaving two
competing active plans. Updating documentation never resets evidence or passes an
unresolved acceptance gate.
