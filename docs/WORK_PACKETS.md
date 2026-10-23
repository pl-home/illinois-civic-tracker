# Remaining implementation work packets

Revision 12 — October 22, 2026. These are bounded plans, **not blanket execution
authorization**. This documentation task implements none of these features.
Machine-readable IDs/dependencies are in [handoff.json](handoff.json).
Common checks and stop rules: [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md).

## P01 Daily-run freshness and delay diagnosis — complete

The October 22 run began at 06:30:43 Central. The gate succeeded, but all
collection/test/model/publication steps and deployment were skipped because the
non-manual predicate admits local hours 01:00 through before 06:00. The persisted
completed-date ledger was October 18, so duplicate-date suppression and disabled
configuration were not the cause. The dated evidence and proposed policy are in
[evidence/daily-delay-diagnosis.json](evidence/daily-delay-diagnosis.json) and
[DAILY_REFRESH.md](DAILY_REFRESH.md). The proposal retains the normal window and
allows one ordinary late catch-up through 09:00 Central, then refuses with a
typed `late-window-expired` reason. No collector, schedule, ledger or source was
changed. **Done:** gate decision, local-time conversion, receipt age and hosted
step outcomes are documented; old `ok` is not called fresh. P02 is the next
implementation task.

## P02 Bounded delayed-run observability and repair

**Depends on P01; complete for the bounded gate and hosted proof.** Own `daily.py`,
`tests/test_daily.py`, `daily.yml` only if necessary, and `DAILY_REFRESH.md`.
Explicit safe gate reasons and last-attempt versus last-success evidence are now
present. The documented bounded catch-up behavior is implemented within existing
daily collection authorization. No extra confirmation is needed for routine reversible
checks already in scope; ask only if a later change expands authorization. Preserve the target
01:00 Central, at most one normal attempt per date, shared lock, DST behavior,
January guard and budget reservations. No new collector schedule.

Run `python -m unittest discover -s tests -p test_daily.py -v`, then common checks.
Fixtures cover on-time, late allowed/refused, completed-date duplicate, fall-back
repeated hour, spring-forward, disabled plan and January guard. The hosted
scheduled run 39945362221 began at 06:20 Central, advanced the dashboard to
October 23, and deployed a partial receipt; the late-window path therefore
passed while source-specific failures remained visible. No forced/manual refresh
was used.

## P03 First-party source diagnostics and failure isolation — complete

**Independent source reliability task.** Own `communications.py`,
`tests/test_communications.py`, `COMMUNICATIONS.md`; change `error_journal.py`
only if its existing safe schema cannot represent the approved code. Start with
the five failed sources in `data/communications-state.json`, not all websites.
Current generic errors cannot establish whether transport or parsing failed.

Separate safe HTTP status, timeout/TLS, parse/structure and missing-metadata
categories without logging exception/provider bodies, headers or authenticated
URLs. Keep last-good dates and retained flags; never turn failure into empty
success. Do not change publisher mapping/name filters to fix network failures.
No retry of permanent 403/404; any transient retry is bounded and respectful.
Use mocked failures first, then one approved bounded hosted check. The existing
`media.yml` **mode=communications** skips inference; verify all financial/work
files unchanged. **Done:** safe categories are covered by offline tests and the
hosted communications-only run [39898483019](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39898483019)
completed successfully without model calls; retained records and publisher
attribution remained intact. No model use.

## P04 Genuine live hearing/form acceptance

**Source-dependent, not a reason to poll continuously.** Read
`HEARING_TRACKING.md`, `hearing_collect.py`, `hearing_changes.py`,
`hearing_view.py`, `digest.py` and `tests/test_hearing_changes.py` /
`tests/test_digest.py`. Existing synthetic transitions already pass.

When an official future notice is available, use the existing paced access
client and exact notice/bill/amendment identity to verify an actually open form.
Never submit it. Record date/time/source proof and stale/failed clearing behavior.
Confirm an explicit real reschedule/postponement/cancellation only if published;
absence cannot substitute. **Done:** dated live receipt and page/preview evidence,
or explicit pending source availability. Do not label historical results or
synthetic fixtures a live pass. No PDF work or fabricated sample data in production.

## P05 Annual storage and history-growth simulation

**Ready for a separate offline task, independent of delivery.** Start with
`member_history.py`, `news_archive.py`, `changes.py`, `error_journal.py`,
`browse.py`, `digest.py` and their size tests. Add a separate offline simulator
in `scripts/` and synthetic growth fixtures only; do not prune production data.

Model unchanged runs, realistic revisions, noisy worst case, 100 news records/
member, bounded journal and generated pages for 365 days. Measure canonical JSON,
base/member/digest artifacts, Git history separately and year-one forecast.
**Done:** reproducible report with assumptions and pass/fail against existing
limits. Size failure proposes sharding/windowed display, not deletion of source,
financial or permanent Tier A/B history. No network/model/storage service purchase.

## P06 Service/session rollover review

**Date-sensitive; do not wait for digest.** Before January 3, 2027, read
`config/project.json`, `config/dashboard.json`, `config/daily.json`,
`daily_state.py`, `daily_federal.py`, `dashboard_sources.py`, official member/
committee configurations and tests. Initial packet is a review/report only.

Identify every GA104/GAID/session/Congress119/member/service/committee literal,
URL shape and review guard. Separate proposed successors from verified service
facts. January 3 is a review guard, not proof both legislatures roll over that
day. Preserve outgoing member history, chamber-specific dates and service periods.
**Done:** official evidence and a reviewed migration/test matrix; no speculative
ID swaps, deleting history or merely moving the guard date. Implementation of
verified identities needs a separate reviewed packet and before/after fixtures.

## D00 Owner preview review

**Blocked on owner decision.** Provide the real HTML/text preview and clearly
synthetic local normal/quiet/partial examples described in `DIGEST_PREVIEWS.md`.
Ask for section/detail/inclusion/wording feedback, not for credentials. Record
the actual review outcome. This documentation request is not approval.
**Done:** dated owner acceptance or requested revisions; delivery remains disabled.

## D01 Offline delivery-state design and state machine

**Blocked until D00 and a task to begin delivery work.** Read `digest.py`,
`mail_test.py`, `m0-mail.yml`, existing reservation/privacy tests and Stage D in
`IMPLEMENTATION_PLAN.md`. Proposed new ownership: `delivery.py` and
`tests/test_delivery.py`, plus a delivery-design guide. Do not change live flags.

Define owner reference (no address), Chicago period, immutable preview/input
fingerprints, attempt ID and states: prepared, reserved, submitting, sent,
rejected, uncertain. Once submission may have started, absent acknowledgment is
uncertain, never automatically retryable. A changed preview in the same week
must not create an ordinary duplicate send. Use fake transports and scratch files.
**Done:** independent review plus deterministic transition/replay/concurrency,
failed-reservation-persistence and crash-boundary tests; zero SMTP/network/model.

## D02 Durable reservation workflow without transport

**Depends on reviewed D01; still no email.** Own the new delivery persistence
adapter/tests and a manual-only disabled rehearsal workflow. Use the existing
source lock/current-main convention. Persist a reservation before a transport
could be exposed to secrets. Push failure prevents sending; retain every attempt.
Test concurrent triggers, rejected push, post-reservation crash, changed preview,
and rerun of already submitting/sent/uncertain state. **Done:** hosted no-send
rehearsal proves persistence/order and stale-SHA handling, with no mail secrets
or send step. Do not mistake the existing preview JSON for a delivery ledger.

## D03 Controlled owner-only delivery acceptance

**Depends on D02 and explicit authorization for the controlled send.** Senior
review required. Only here add narrowly scoped Gmail secret consumption and a
transport. Logs/receipts contain no address, headers, raw provider text or body.
No legislator/party/campaign recipients. Validate rejection, SMTP acceptance,
failed durable acknowledgment, exact-message owner inbox confirmation and
uncertainty recovery without resending. **Done:** reviewed controlled receipt,
retained failed/uncertain attempts, no automatic uncertainty replay. Transport
acceptance alone is not inbox proof or exactly-once delivery.

## D04 Weekly activation

**Depends on D03, owner acceptance and scheduling authorization.** Add only the
reviewed Monday 06:00 Central schedule. Preserve shared lock, DST/delayed-run
policy and owner/period deduplication. Rehearse repeated triggers, late start,
quiet week, partial sources and failed persistence. **Done:** explicit activation
receipt and monitoring/recovery instructions. Never toggle `delivery_enabled`
to bypass the current preview-only validation. Full Stage D remains open until
these gates pass; no assumption that preview review approves every later side effect.

## M2 / M4 / M5 / M6 Future feature design

**Separate future tasks; not ready to implement as one packet.**

| Milestone | Small first deliverable | Gate before implementation |
| --- | --- | --- |
| M2 synopsis/rewrite detection | Source-version/adoption evidence design and held-out continuity versus subject-replacement cases, including SB2427 | Follow `AMENDMENT_INFERENCE_REQUIREMENTS.md`; no new model calls, party classifier or PDF work without separate approval |
| M4 deeper federal participation | Source/identity and coverage matrix for one official committee adapter | Assignment is not attendance; bound requests and preserve existing floor data |
| M5 full-tenure/topic coverage | One member/session discovery plan, GA103 service proof and size estimate | Preserve no-export-whitelist rule; no statewide mirror, destructive history rewrite or unknown-date invention |
| M6 private contact packets | Private/public boundary and one reviewable draft template | Keep positions/addresses/correspondence out of public Git; no automatic outreach or assumed Claude vault access |

PDF/committee extraction remains explicitly deferred across all packets. Preserve
failed trial receipts and unsettled liability; availability of a manual workflow
does not permit rerunning it.
