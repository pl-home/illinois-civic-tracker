# Illinois Civic Tracker: product vision

Revision 6 — October 20, 2026, America/Chicago.

This reconciles the October 15 research plan, October 16 vision/build brief,
subsequent owner decisions and the two external-project reviews. It preserves
the product's purpose while correcting obsolete scope and implementation status.
The [implementation plan](IMPLEMENTATION_PLAN.md) defines delivery order and
acceptance gates. The [published planning copy](https://github.com/pl-home/illinois-civic-tracker/blob/main/docs/PRODUCT_VISION.md)
and workspace copy share this revision; they are handoff mirrors, not separate
implementations. Earlier plans and dated receipts remain historical evidence.
Owner instructions and newer approved decisions take precedence over older text.

## 1. Purpose and access

Help a constituent answer:

1. What have the selected legislators done, recently and over their service?
2. What hearings or other decisions can the constituent still participate in?
3. What are the Lee County Democratic and Republican organizations publishing?
4. What relevant reporting provides context, and what remains unverified?
5. What verified facts and unanswered questions would support useful communication?

The [public website](https://pl-home.github.io/illinois-civic-tracker/) is the
read-only browsing surface. Obsidian is the private workspace for positions,
watchlists, notes, correspondence and eventual contact packets. Claude or another
AI can assist with owner-initiated analysis, but no chat session or local computer
is required for scheduled public collection. Claude/vault access and any future
feed-to-vault integration remain separate setup and verification tasks.

Use free official data and existing resources first. Adapt small proven components
instead of adopting another application's entire database, account system or
cloud stack. Index quietly; bring explainable, noteworthy changes to attention.

## 2. Subjects, topics and evidence

| Subject | Current configured scope |
| --- | --- |
| Bradley Fritts | Illinois House District 74, GA104 |
| Li Arellano, Jr. | Illinois Senate District 37, GA104 |
| Darin LaHood | U.S. House IL-16, Congress119 |
| Dick Durbin; Tammy Duckworth | U.S. Senate, Congress119 |
| Lee County Democrats; Lee County IL Republicans | Configured public website/feed sources |

Person, office, session, service dates, aliases and committee assignments belong
in configuration. Preserve a former member's history when service ends. Review
identities and committee assignments before GA105/Congress120; do not simply
increment session numbers or assume the same officeholders. The current collector
has a review boundary of January 3, 2027; resolve it before that guard is reached.

Confirmed priority topics are immigration, energy policy, pensions, law enforcement
and housing. The earlier proposed civil-liberties topic and detailed energy/civil-
liberties boundaries remain open; this reconciliation does not decide them.
Committee/statute structure informs tagging before keywords. A tag needs a reason
and can be provisional. Relevance never implies the owner's stance or urgency.

Official sources establish legislative facts. Reporting supplies attributed
context; office, campaign and party publications document their publishers'
statements. A reachable URL, an imported record, a model answer or a status label
does not by itself validate a claim. Bind source, member/session/measure identity,
action or motion and relevant values. Separate discovery, structural validation,
source validation, conflict and withholding. Routine valid records should pass
deterministic checks; human review handles unresolved exceptions.

Preserve original filing separately from current sponsorship, dated additions
and removals, and other-chamber roles. Preserve raw vote codes, procedural versus
amendment/final-passage distinctions, and committee versus floor coverage. Unknown
or missing choices do not establish absence. Source-document counts are not
necessarily counts of distinct voting decisions.

## 3. Current implementation and explicit gaps

Status snapshot: October 20 Stage B release and its receipts, not a promise that every
source will be healthy on a later run.

| Capability | Current state |
| --- | --- |
| Public member dashboard and historical browser | Deployed; recent actions/votes, member links, committee roles/links and a rolling month of meetings, with coverage labels |
| Scheduled official collection | GitHub Actions targets 01:00 America/Chicago daily; Illinois XML/floor CSV, federal bill relationships/floor XML and bounded calendars; completeness qualified per source |
| Recent media and direct communications | Implemented separately: up to three eligible newsroom reports per member, visible discovery method, and attributed office/campaign/party communications with source coverage |
| Inference | Only narrow Qwen3 32B / DeepInfra media-relevance screening is enabled; it selects supplied IDs, not facts or article summaries |
| Operations | Privacy checks, source/cost receipts and bounded structured error journal implemented |
| Common meaningful-change ledger and static feeds | Stage A delivered: source-scoped ledger and common HTML/JSON/Atom gate; quiet baseline, replay, corrections and QA. See CHANGE_FEED.md; complete historical discovery and detailed hearing/party coverage remain limited |
| Hearing agenda/status revision history | Stage B delivered: day/committee navigation, accepted agenda/amendment revisions, explicit postponement/cancellation, conservative identity checks and stale-slip protection. Live open-form acceptance remains pending; Senate ambiguity and federal agenda limits remain explicit |
| Broad county-party website change monitoring | Legacy bounded collector exists; full port into the hosted pipeline remains open. Member-name-filtered party feeds are not equivalent coverage |
| Weekly digest and independent alerts | Not deployed; Monday 06:00 Central remains the digest target after acceptance |
| Daily new committee roll-call/PDF collection | Deferred; qualified historical records remain available. The diagnostic model trial accepted 0/6 and does not enable collection |
| Full-tenure/topic pages, rollover and private contact packets | Remaining milestone work |

The former Codex and Windows schedules remain stopped. Their archived readmes
are not operating instructions. A successful workflow or passing unit tests do
not imply complete source coverage, accepted inference or a finished M1.

## 4. Core improvements and their delivery boundaries

**A common meaningful-change feed.** A stable source-based event should power the
member/bill/committee views and later digest without creating duplicate alerts.
Retain event time, first observation, source validation and revision identity
separately. Historical backfills, unchanged observations and parser migrations
must not masquerade as fresh activity. Corrections and confirmed removals remain
traceable. Per-source completeness governs reconciliation and watermarks.

**Hearing usability and revisions (Stage B delivered within source limits).** Keep the next-month member view; provide clear
date/committee navigation and compact agenda detail. Show the member's exact
published role, local time/location, official notice, agenda bill/amendment links,
and observed additions/removals or source-confirmed postponements/cancellations.
An official hearing ID should survive a changed time or room. Failure or absence
from an incomplete listing must not become cancellation. An agenda listing does
not establish that a member attended or voted.

**Data-quality checks alongside operational health.** Check source identities,
duplicate actions, missing relationships, unknown values, suspicious coverage
changes and freshness. Explain withheld records and partial sources. Distinguish
zero activity, unavailable data, incomplete discovery and an old source freshly
checked. Keep one publication contract across website, feeds and digest.

These are M1 completion work. Static member/committee Atom or RSS and compact JSON
exports are useful outputs of the same event layer, not a separate platform or a
reason to delay digest acceptance. They require no new model use.

## 5. What reaches the owner

The homepage shows recent member activity and the next month of posted meetings.
The proposed weekly digest prioritizes approximately the next ten days of usable
hearing opportunities, then noteworthy verified member activity, attributed
county-party changes, relevant media and a source-health footer. A quiet week
still reports what was checked. Every inclusion has a reason and evidence link.

Ceremonial records remain indexed and hidden by default with a visible reason;
resolutions are not discarded wholesale. Zero-nay votes are ordinarily index-only
and labeled no recorded opposition. Unknown tallies cannot establish unanimity.
Procedural/appointment activity stays distinct. Topic-related split votes,
appropriations, sponsor-role changes and possible bill rewrites need explainable
attention rules. Preserve the reviewed 134-item/24-ceremonial historical fixture
as a regression example, not a future discovery limit or current activity count.

News discovery uses reviewed publishers and dated indexed-feed candidates; it is
not exhaustive article reading. The recent-media section may contain fewer than
three items. Capitol Fax is included in the reviewed media policy. Dedicated
per-subject/Lee County mention coverage still needs its own verified acceptance.
Direct communications remain separate from independent news. A link-only campaign
source or Facebook navigation link is not automatically collected content.

Witness-slip links appear only with a verified open submission form. Historical
results are not submission forms; stale/failed checks cannot preserve an open
claim. The tracker never files a slip, contacts an official or publishes a draft
automatically. Proposed immediate material-change alerts remain later work.

## 6. Data, storage and privacy

| Tier | Retention intent | Contents |
| --- | --- | --- |
| A: quiet index | Permanent, compact, over covered service | Stable person/session/measure/event IDs, dates, roles/choices, flags, topics/reasons, official links and coverage |
| B: selected detail | Permanent, compact | Relevant synopsis/version context, action history and inclusion/correction reasons |
| C: referenced evidence | Retain while referenced or needed for conflicts | Minimal snapshot/hash or archive link with provenance |

Do not adopt Hawaii Tracker's deletion of canonical records after three years.
Window or shard browser payloads instead. Do not delete existing evidence or reset
source/financial ledgers. Raw HTML/XML, full CSVs, PDF text and full bill/article
text are not routine repository payloads. Bound temporary scratch and exceptional
evidence; avoid creating another large local mirror.

Preserve the existing 20,000,000-byte working JSON limit and configured website
artifact bounds. Repository target remains at most 100 MB, with the earlier
400 MB hard ceiling; simulated growth and Git history must be measured. Moving
new snapshots to releases does not erase old Git history or justify losing compact
full-tenure facts. The error journal's live cap is 96 KiB with bounded events and
incident counts; it is not a complete permanent audit trail.

Public: factual indexes, attributed publications, topic reasons and source health.
Private: positions, drafts, contact/slip logs, private watchlists and notes in
Obsidian. Secrets stay in Actions' configured store, available only to their
steps. No credential values, private addresses, local machine paths or raw model
responses belong in public records, diagnostic logs or review exports. Preserve
privacy checks, private commit identity and disclosure of any incorporated code.

## 7. Operation and inference

Continue GitHub Actions plus compact records and GitHub Pages. The daily target is
**01:00 America/Chicago**, superseding 23:00. Existing UTC wakes and a Chicago-date
ledger handle DST/duplicates; GitHub start delays remain possible. Publication
follows collection and successful persistence. Preserve source locking, explicit
failure isolation, verified TLS, official FTP preference, configured request
bounds and sequential ten-second ILGA-main spacing. No logged-in collection.

The planned digest target remains **Monday 06:00 America/Chicago**, disabled until
preview and delivery gates pass. Persist a reservation before side effects and
handle uncertain delivery conservatively. SMTP acceptance and durable state cannot
be one atomic transaction; do not promise exactly-once delivery from a timestamp
or boolean flag. Use no automatic resend of an uncertain attempt.

Core collection, change detection, validation, notability rules and publishing
must operate without a frontier AI or local Ollama. The existing narrow media
exception uses hosted open-weight Qwen3 32B through DeepInfra via OpenRouter.
Limits remain **USD 0.02 per Chicago day, USD 0.20 per Monday–Sunday Chicago week,
and USD 20 lifetime**. Count all project trials and unsettled reservations; never
reset history. The page reports recorded usage with its calculation time, not
unrelated account spending. Unavailable inference must not corrupt official facts.

Party interpretation, bill summaries/rewrite inference and PDF inference are not
enabled by this revision. The owner has deferred PDF work; its historical failure
receipts and unknown charge hold remain intact. A proposal or reusable upstream
model component is not authorization to activate another inference task.

## 8. Milestones and acceptance

| Milestone | Reconciled scope/status |
| --- | --- |
| M0 | Source, runner and mail verification: samples/receipts exist; coverage/timing limits remain. Preserve their exact qualifications |
| M1 | Complete hosted daily monitoring, shared change events/quality gates, hearing usability, bounded party/mention coverage and the weekly digest. Public site and selected federal/media features were brought forward; M1 remains incomplete |
| M2 | Bill-rewrite detection, amendment topic changes and later material-change alerts. Replacing everything after the enacting clause is only a signal; SB2427 illustrates a replacement amendment faithful to the original subject |
| M3 | Review and implement GA105/Congress120 service, source and committee transitions before the configured review guard; do not wait for other milestones |
| M4 | Deeper federal coverage and Duckworth committee participation/watch. Basic federal sponsorship/floor collection already exists; do not rebuild it |
| M5 | Expanded full-tenure/topic pages and applicable GA103 backfill. Basic browsing already shipped |
| M6 | Private contact packets, proposed around March/September, using explicit owner positions and reviewable drafts |

Accept against declared source scope: traceable facts, explicit gaps, identical
party rules, no false new-activity events on replay, no inferred stance, safe
hearing/slip behavior, no private leakage and bounded measured growth. Additional
PDF/committee coverage remains a separately deferred gate; advancing non-PDF work
must not be represented as resolving that coverage gap. Code provenance and
acceptance tests belong with every adapted component.

Open decisions remain topic refinements/pins, deeper federal committee coverage,
full-tenure depth, and later evidence-storage choices. This vision changes the
documentation and delivery plan, not running schedules, notifications or costs.
