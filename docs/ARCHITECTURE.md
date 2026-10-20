# Architecture and reviewer guide

## Current operating map — Stage A, October 19, 2026

Start with the revision 8 vision/plan, [CHANGE_FEED.md](CHANGE_FEED.md),
`changes.py`, `change_sources.py`, `change_feed.py` and `tests/test_changes.py`.
Existing daily_state/daily_federal/dashboard_collect produce official compact
records; media/communications produce separately attributed metadata. The new
offline change adapters validate source-scoped projections and atomically store
facts, revisions and completion cursors. The shared public selection feeds HTML,
JSON and Atom. browse/dashboard render without fetching or mutating state.

Daily/federal/Illinois-recovery/media workflows run the offline ledger under the
existing shared state lock before publication. Pages/CI builds remain read-only.
The 01:00 Central schedule and spending limits are unchanged. Only the existing
narrow media relevance task uses a hosted model. PDF work is deferred, and digest
delivery is not deployed. Ten base public files total at most 650 KB;
the October 20 member-history extension adds separately allowlisted static pages
capped at 3 MB. See [MEMBER_HISTORY.md](MEMBER_HISTORY.md). Current build output
reports both components and their sum; working canonical records are not copied
into a new stored index. Each page contains at most 25 entries and works without
scripts. History publication rechecks the shared fact schema and fingerprint;
quiet baselines remain history rather than new alerts. Working JSON is capped
at 20 MB, including a 10 MB ledger. Privacy checks and the
bounded error journal cover Stage A as well. No new service/database is needed.

## Stage B hearing layer — October 20, 2026

Read [HEARING_TRACKING.md](HEARING_TRACKING.md) and `hearing_changes.py`,
`hearing_collect.py`, `hearing_view.py` and `tests/test_hearing_changes.py`.
Official URL/EventID identities and normalized bill/amendment contexts feed
source-scoped accepted revisions. Missing or failed listings do not cancel
meetings; explicit status needs an affirmative source assertion. Senate fallback
identity changes are conservatively withheld. The same accepted-fact and event
gate powers navigation, notice detail and revision history. Witness-form claims
expire and clear on failure. Official changes are recorded before optional media
inference. Live upcoming/open-form acceptance remains pending; PDF work stays
deferred. Full historical payloads do not enter the bounded browser view.

## Historical M0 design notes

The sections below preserve the earlier verification architecture as history.
Their manual-only/eight-file/no-daily/no-inference statements describe M0,
not current operation. Current code, Stage A documentation, and dated source and
financial receipts take precedence; historical source findings still apply.

## What exists now

This is an M0 verification foundation, not the production tracker. Start with README.md, docs/M0_FINDINGS.md, and one evidence file appropriate to the question. The full raw archive is not needed for a structural review.

| Component | Responsibility | Boundary |
| --- | --- | --- |
| config/project.json | Session, subjects, service periods, source intervals and pinned issuer metadata | No secrets or owner settings |
| http.py | Host restrictions, sequential main-host access, persistent timing, bounded reads and verified TLS | No automatic redirects; source failures remain failures |
| vote_audit.py | Follow-up classification of the 215 original comparison gaps | Raw choices and unresolved source detail stay retained |
| hearings.py / verify_hearings.py | Public detail-table parsing and bounded historical validation | No range API; historical results do not establish active submission forms |
| vote_csv.py | Full-file nay counts, subject rows, narrow motion aliases and explicit unknown choices | Floor only; no committee-vote inference |
| rules.py | Exact ceremonial rule and shell flag | No stance, rewrite detection or model calls |
| dashboard_collect.py / dashboard_sources.py / config/dashboard.json | Bounded public activity import, committee schedules and read-only slip-form verification | Manual only; source failures and historical dates remain explicit |
| dashboard.py / browse.py / web | Static five-member dashboard and original 134-item archive | Rendering uses no network, credentials or model calls; eight allowlisted artifact files |
| inference_eval.py / manual evaluation workflow | One authorized Qwen3 32B / DeepInfra evaluation | Precommitted bounded liability, public/synthetic inputs only, no retries or routine integration |
| verify_sources.py | One-time source comparisons against explicitly supplied read-only evidence | M0 only; raw downloads stay ignored |
| verify_pdf_sample.py | Twenty-row PDF/XML layout verification | Sample helper, not a production name/role parser |
| probe_runner.py | Hosted host access plus source request timing | Small bounded resources; CSV HEAD, not full import |
| observe_m0.py | Six-hour listing and daily CSV-header observations | Hard end time in configuration |
| mail_diagnostics.py | No-send connection/authentication diagnostics and exact-test inbox lookup | Does not submit another message |
| mail_test.py | One reserved Gmail self-test and exact-message INBOX check | Same mailbox plus alias only; no digest schedule |
| privacy.py | Reject private addresses, machine profile paths and credential-shaped text | Files and finding categories only; narrow reviewed public exceptions |

Tests use synthetic data or reviewed public sponsorship facts. Optional PDF tooling is for verification, not a required nightly dependency. A [member dashboard and historical browser](DASHBOARD.md) and a [manual hosted evaluation](INFERENCE_EVALUATION.md) are separate from the still-gated production pipeline. No routine inference or production collector is enabled.

## Future hosted inference

The owner approved one bounded Qwen3 32B / DeepInfra evaluation. [Its results](INFERENCE_EVALUATION_RESULTS.md) failed the mandatory instruction-injection gate. config/inference-plan.json keeps enabled=false for routine operation; only the manual evaluator consumes its evaluation authorization. [OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) and [the protocol](INFERENCE_EVALUATION.md) record privacy and spending controls. M1 remains deterministic.

## Proposed M1 flow

1. Each source adapter fetches conditionally or by changed listing entry. Failure in one adapter must not prevent the other adapters from running.
2. Normalize public facts into versioned compact records. Keep source URL, source observation time, legislative event date and provenance distinct. An older event discovered today remains historical.
3. Maintain a complete quiet index and a separate digest-eligible event ledger. Initial imports, parser migrations and repeated source observations must not become new activity.
4. Apply topic reasons in order: committee, statute, then keywords. Retain untagged and ceremonial records quietly. Calculate nay counts from the full floor CSV before member filtering.
5. Render the weekly HTML/plain-text digest from eligible events, upcoming hearings and attributed party/feed items. Quiet weeks still include checks and health. Owner positions and drafts stay outside the public repository.
6. Commit bounded state and public source health using the Actions bot. Deliver only to the configured owner recipient.

M1 needs explicit schemas, adapter interfaces, bounded history retention and deterministic replay tests. The verification helpers do not substitute for that work. Source-specific name spelling and motion aliases should move into configuration when production adapters are built.

## Source and provenance decisions

- FTP bill-status XML is primary. Directory dates/sizes identify candidates; content hashes distinguish actual updates.
- Sponsor actions must distinguish filing, chief changes, additions, removals and alternate-chamber roles. A current chief is not necessarily the original filer. The displayed sponsor list alone is not enough to reconstruct dated history.
- Statute references carry amendment section and add/delete operation. Their flat union is not the current bill text.
- The floor CSV preserves raw motion and choice. Committee votes require separate evidence. Reconciliation cannot discard amendment numbers merely to improve a match rate.
- Party material is attributed to its publisher. Both parties receive the same deterministic extraction and significance rules. Port and review the bounded existing page list; do not start an unrestricted crawler.
- Capitol Fax search feeds provide candidate links, not proof of an exact named mention. Protected posts are excluded; full articles are not stored.

## Workflow state and delivery

All state-writing M0 workflows share one concurrency group and check out current main after the job enters that group. This avoids processing an old dispatch revision after another job commits evidence. A rejected push is a failed job, not successful persistence.

The mail test commits a reservation before secrets are exposed to its send step. If that push fails, the send is skipped. A later workflow sees the reservation and stops. It never automatically clears an uncertain reservation. A separately requested credential-correction retry requires a successful no-send authentication check and an exact-test INBOX search; it preserves the failed receipt. Accepted submissions and attempts that entered the submission stage cannot use that retry route. The test checks only its exact Message-ID in INBOX with a read-only selection and does not read unrelated messages.

Production SMTP still has an unavoidable uncertainty window between submission and durable acknowledgement. A normal sent-week ledger handles repeat triggers but cannot atomically commit an SMTP side effect. The M1 design must choose and test conservative uncertainty handling; it must not advertise unconditional exactly-once delivery.

Manual mail execution uses repository secrets only on the send step. No pull-request workflow receives those secrets. SMTP/IMAP error text is suppressed because it can contain addresses; public receipts record safe error classes and delivery states only.

## Certificate chain

The ILGA servers were reachable from the local platform but failed Ubuntu certificate verification because an intermediate was missing. The configured CA issuer URL and DER fingerprint were read from a platform-verified certificate chain. The downloaded intermediate must match that fingerprint before use. Its AIA download is HTTP; the cryptographic pin protects the certificate bytes. No leaf or root is added, partial-chain trust is disabled, and the normal system-root and hostname checks remain enabled. A changed pin or unavailable issuer fails visibly.

## Deployment gates

Read the complete M0/M1 table in M0_FINDINGS.md before implementation or deployment. Outstanding source timing, post-veto CSV cadence, motion/choice reconciliation and nonempty hearing evidence must be resolved or explicitly addressed in the release decision. M1 also needs import/replay, failure isolation, DST and delay behavior, complete digest rendering, duplicate suppression and size-growth tests.

The old local schedules remain stopped. The bounded metadata observation is the only new schedule. Its first wake after the end date disables that workflow using the [GitHub workflow endpoint](https://docs.github.com/en/rest/actions/workflows#disable-a-workflow); only that observer has Actions-write permission. The source module independently refuses requests after the configured end time. No nightly product collection or Monday digest workflow is enabled.

October 20 news-column extension: `dashboard.media_section` supplies the same
escaped, source-attributed view to member pages (200 days) and the homepage
(90 days). `media.py` persists each query/window in its source receipt, retaining
legacy 90-day provenance. Discovery now uses 200 days; model gates are unchanged.
