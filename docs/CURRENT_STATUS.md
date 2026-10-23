# Current status and decision record

Revision 13 — October 23, 2026, America/Chicago. This is the current status entry
point, not a claim that every live source was checked today. Read it before dated
findings, checkpoints or trial instructions. [Documentation index](DOCUMENTATION_INDEX.md).

## Implemented, pending and deferred

| Area | Implemented | Boundary / next evidence |
| --- | --- | --- |
| Stage A | Source-scoped accepted facts/revisions, QA, quiet baseline, JSON/Atom/homepage feed | Retained conflicts and withheld scopes are not repaired facts |
| Stage B | Hearing navigation, agenda/amendment revisions, explicit postponements/cancellations, expiring witness proof | Genuine live upcoming/open-form acceptance remains source-dependent; missing notices do not imply cancellation or attendance |
| Stage C | Eleven reviewed county-party HTML pages, one poster, six bounded Capitol Fax headline feeds, deterministic relevance | Images/ambiguous edits remain held; a real subsequent source edit is distinct from a baseline or synthetic test |
| Stage D preview | HTML, text, selection JSON and CSS from accepted data; ten-day opportunities; quiet/partial health | Owner has not approved delivery. No sender, reservation ledger or weekly job is implemented |
| Member browsing | 25 activity entries per page; separate undated relationships; member news five per page within 200 days | Homepage news remains three within 90 days; up to 100 screened records/member; not complete tenure or article coverage |
| Communications | Separate office/campaign/party metadata; fifteen sources, twelve automated and three link-only | The Caucus Blog is explicit caucus-wide context for Fritts; his office latest-news page is separate. Publisher text is attributed, not independently verified |
| Inference | Only bounded public media-headline relevance: Qwen3 32B via DeepInfra; hosted daily calls are now proven | USD 0.02/day, 0.20/Chicago Monday–Sunday week, 20 lifetime; unsettled amounts stay held |
| PDF / committee roll calls | Qualified historical records and preserved failed trials | Daily new PDF collection, new trials/OCR and legislative/party inference remain deferred |
| Stage E / M2–M6 | P05 storage simulation and P06 rollover review | Successor identity migration, correction coverage, semantic rewrites, deeper federal history and private contact packets remain incomplete |

M1 and full Stage D are **not complete**. A transport self-test is not a weekly
delivery system. Updating documentation is not preview approval or permission
to send mail, invoke a model, retry an uncertain charge or change a schedule.

P06 records the service/session rollover matrix in
[SESSION_ROLLOVER_REVIEW.md](SESSION_ROLLOVER_REVIEW.md) and its evidence JSON.
The January safety guard remains in place; no GA105 or Congress120 identity is
verified or configured.

## Operating configuration and observed health

The independent GitHub daily workflow targets 01:00 Central. Its UTC wakes are
06:00/07:00; the gate admits local hours 01:00 through before 06:00 on time and
06:00 through before 09:00 for one bounded late catch-up, unless that local date
is already complete. It reports typed gate reasons and retains separate attempt
and success timestamps. Delayed jobs after 09:00 can still skip collection.
The January 3, 2027 review guard still requires a service/session review.

The October 22 [scheduled run 39771120266](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39771120266)
reported success, but **source collection, tests, model steps and publication
were skipped**. It began at 06:30:43 Central, after the configured 01:00–05:59
non-manual window; the persisted local-date ledger was still October 18. This
was a late-window refusal, not a completed refresh. P01 recorded the evidence;
P02 is now hosted-proven: [run 39945362221](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39945362221)
started at 06:20 Central inside the late window, advanced the dashboard to
October 23, ran the model step, and deployed successfully. The result was
correctly partial: Illinois retained a bounded-file backlog, Senate roll-call
discovery returned `HTTP_403`, and both calendar sources had safe failures.
See [the diagnosis receipt](evidence/daily-delay-diagnosis.json) and
[P02](WORK_PACKETS.md#p02-bounded-delayed-run-observability-and-repair).
Confirm future freshness against gate reasons, step outcomes and dated source
receipts, never a green badge alone.

Latest checked-in evidence at this audit, not fresh source checks:

| Receipt | Timestamp / finding |
| --- | --- |
| Illinois | October 19 22:26 UTC; last report `ok`, historical committee coverage qualified |
| Federal | October 18 10:44 UTC; last report `ok`, now old evidence |
| Calendars | October 20 03:47 UTC; last report `ok`, now old evidence |
| Communications | October 21 00:06 UTC; blog `ok`; Fritts, Arellano, Durbin, Duckworth office and Senate Democratic Caucus fetches failed, prior posts retained |
| Shared QA | October 21 00:07 UTC; partial, nine withheld scopes |

GitHub workflow-state lookup found daily/CI/Pages active and the expired M0
observer disabled. An active manual trial workflow is **available**, not authorized
or scheduled. Initial CI/Pages lookups timed out; the handoff itself subsequently passed
clean-runner CI and actual Pages deployment, recorded in the
[documentation receipt](evidence/documentation-handoff.json). That does not refresh
source evidence. No collectors,
model calls, mail or diagnostics were dispatched for this documentation update.
The former Codex/Windows schedules were previously stopped; they were not
reactivated or independently reverified here.

## Decisions that must survive a handoff

- Preserve raw vote choices, motions, tally/date conflicts, original filing and sponsor/removal/other-chamber distinctions. Unknown is not absence or Nay.
- Official source facts are deterministic. Newsroom metadata and office/campaign/party statements remain separate. Topic matches never establish the owner's stance.
- Main ILGA access is sequential, at least ten seconds; backfill twenty. Preserve verified TLS, host/path restrictions, source locks and quotas.
- No private vault, contact addresses, credentials, raw article/PDF/site archives or authenticated URLs enter public files/logs. Secrets stay in Actions secrets; names alone may be documented.
- Keep source/financial history, unresolved reservations, failed receipts and attribution. Do not reset/delete them to pass a gate or fit a budget.
- The 134-item Fritts export is a regression/archive fixture, not a discovery whitelist. Arellano needs no equivalent manual export.
- Replacement-amendment boilerplate alone does not prove a shell rewrite; SB2427 is a continuity regression. No synopsis/rewrite inference is active.
- Obsidian remains private notes/drafts storage. Claude folder access is separate and unverified. No automatic outreach or witness-slip submission.

## Storage and validation

Canonical JSON: 20,000,000 bytes; shared ledger 10,000,000; error journal 96 KiB.
Four digest files: 90,000 combined, inside fourteen base public files capped at
650,000. Member/news HTML: 3,000,000 separately; combined site: 3,650,000.
The October 20 source-update build measured 546,175 base / 2,983,868 combined
bytes. P05's 365-day synthetic report passes unchanged and realistic scenarios
and identifies noisy-case pressure without pruning data. Dated test counts remain
attached to their receipts; Git growth is forecast separately in the report.

Use [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md) and one [work packet](WORK_PACKETS.md).
The reconciliation passed 323 offline tests and privacy checks. The later P02/P03
implementation passed 325 tests; P05 adds three offline tests for a current total
of 328. The October 23 scheduled run completed two
bounded media model calls for USD 0.00020308 and published a partial but current
dashboard. Model calls remain limited to public media relevance.
The small offline handoff checker validates documentation, dependencies and
disabled-feature configuration; a pass does not prove live source health or
grant authority to execute a planned task.
