# Illinois civic tracker

A small, factual Illinois legislative and county-party monitor. The intended product is a weekly digest that helps a constituent notice relevant actions and upcoming hearings. It does not infer a position or send messages to legislators.

**Planning reconciled October 19, 2026:** start with the revision 5
[product vision](docs/PRODUCT_VISION.md) and
[implementation plan](docs/IMPLEMENTATION_PLAN.md). They reconcile the earlier
research/build briefs with owner-approved changes and current implementation.
Stage A now supplies the common change feed and quality gates. Next are hearing
revisions, bounded party/relevance coverage and digest acceptance. PDF work is deferred.
See [the shared change contract](docs/CHANGE_FEED.md), [completion receipt](docs/evidence/stage-a.json)
and [actual upstream adaptation notices](THIRD_PARTY_NOTICES.md). The homepage
now includes bounded accepted changes plus JSON and Atom subscription links.

**Browse the tracker:** [Illinois civic tracker](https://pl-home.github.io/illinois-civic-tracker/). The homepage shows recent actions and recorded votes for Fritts, Arellano, LaHood, Durbin and Duckworth, plus committee links, a rolling month of posted meetings and recent attributed media reports. Source dates and incomplete coverage are explicit. Daily website refresh is configured for 01:00 Central; collection health and source dates remain visible. Weekly digest delivery remains undeployed. See [daily source scope and operation](docs/DAILY_REFRESH.md). See [dashboard sources and limits](docs/DASHBOARD.md). The original 134-item Fritts export remains available in the historical archive. Public facts only; no private advocacy notes are published. Each card also shows the exact news search and a separate office/campaign/party communications section with source coverage. See [news discovery and direct communications](docs/COMMUNICATIONS.md).

The homepage reports recorded AI usage against **USD 0.02/day and USD 0.20/week**, using Monday–Sunday in America/Chicago. Actual charges and unsettled reservations are separate; earlier evaluations count. Details: [usage and budget policy](docs/BUDGET_USAGE.md).

[PDF extraction setup and trial receipts](docs/PDF_EXTRACTION.md) document the
manual native-text/OpenRouter pilot, source-grounding checks and outstanding
liabilities. It is not a scheduled collector and does not change verified votes.
The [six-case committee evaluation](docs/COMMITTEE_ROLLCALL_EVALUATION.md) passed
the native choice/tally checks but failed the model output-status gate; daily
committee PDF inference remains disabled.

[Troubleshooting journal](docs/ERROR_JOURNAL.md): compact recurring errors,
recoveries and allowlisted model diagnostics, capped at 96 KiB. Existing model
receipts and cost ledgers remain authoritative.

The [versioned committee diagnostic rerun](docs/COMMITTEE_DIAGNOSTIC_RERUN.md)
preserves the original trial and uses separate bounded spending receipts. It is
manual only; daily committee collection remains disabled.

## Current status

**Staged daily website refresh is configured; complete M1 verification and digest deployment remain open.** The former local schedules were stopped before this repository was started. Historical source material is read only. This is a fresh repository; it contains no private vault, raw archive, email addresses or credential values.

For a focused code review, read the current vision and implementation plan first,
then [architecture and boundaries](docs/ARCHITECTURE.md),
[dated M0 findings](docs/M0_FINDINGS.md), and one representative evidence file.
Older operational statements and the October 16 build brief remain historical
where superseded; code, configuration and dated receipts establish actual coverage.

Read [the product vision](docs/PRODUCT_VISION.md), [the build brief](docs/BUILD_BRIEF_M0_M1.md) and [M0 findings](docs/M0_FINDINGS.md). Findings distinguish direct observations, normalization gaps and tests that still need time or corrected credentials. Hosted source access and Gmail self-delivery to INBOX pass. The follow-up audit reaches 96.59% comparison-key coverage and validates a five-page historical hearing fallback. Retained source gaps, upcoming hearing behavior and multi-day timing remain open.

The [first Qwen3 32B / DeepInfra evaluation](docs/INFERENCE_EVALUATION_RESULTS.md) completed 30 calls for USD 0.00145256. It failed the mandatory instruction-injection gate despite 92.3% held-out category accuracy. The [v2 follow-up](docs/INFERENCE_EVALUATION_V2.md) quarantined five attacks before calls but accepted only one of three eligible held-out responses; its single actual website delta also leaves the real-change coverage gate unmet. Both trials together cost USD 0.00172472. The owner subsequently authorized narrow media-headline relevance screening within the configured project budget. That separate ID-only task is enabled; party and legislative inference remain disabled. See [media evidence, spending controls and operation](docs/MEDIA_REPORTS.md). The credential stays in Actions secrets.

## Intended M1 operation

- Public website source refresh daily at 01:00 America/Chicago (owner update October 17).
- Factual digest Mondays at 06:00 America/Chicago, including a quiet-week health summary.
- FTP XML first; one conditional floor-vote CSV retrieval, committee assignments, bounded party pages and Capitol Fax feed metadata.
- Official facts and change collection remain deterministic. A separate, capped media-relevance task is enabled; federal daily collection supplements owner-managed Congress.gov alerts.
- Compact public records; positions, correspondence and contact packets remain private.

The daily website workflow is configured separately from the time-limited M0 observation. No digest is enabled. Only the narrow media-relevance inference task is scheduled alongside daily website collection. The [daily release notes](docs/DAILY_REFRESH.md) state its remaining coverage limits.

## Repository map

| Folder | Responsibility |
| --- | --- |
| config | Subjects, source policy and bounded M0 observation window |
| src/civic_tracker | Small source verification, normalization, privacy and rule modules |
| tests | Synthetic tests and a reviewed 134-item public sponsorship export |
| docs/evidence | Compact public verification outcomes, not raw source copies |
| data | Reserved for M1 compact records and ledgers |
| web | Accessible static browser template, styling and filter enhancement |
| .github/workflows | Tests, Pages publication, M0 source access and bounded observations |

Raw downloads and temporary inspection stay in ignored scratch storage. No full vote CSV, PDF, ZIP or HTML snapshot is committed. The eventual data budget is below 100 MB; broader history growth must be measured before deployment.

## Local checks

```sh
python -m pip install -e .
python -m unittest discover -s tests -v
python -m civic_tracker.privacy
```

The privacy check reports file names and finding categories only. It rejects non-allowlisted addresses, machine profile paths and credential-shaped strings. Before pushing, enable GitHub secret scanning with push protection and keep commit email private. Commits must use a GitHub noreply identity; workflow commits use the Actions bot identity. These settings complement, rather than replace, file review.

## Access policy

Requests to the main ILGA site are sequential, with at least ten seconds between starts; one-time backfill verification uses twenty seconds. Logged-in and disallowed paths are rejected. FTP is preferred. Redirects require an explicit rate-checked retry so an automatic redirect cannot bypass the gate. Source failures must not be converted into an empty successful digest.

## Credentials and delivery

SMTP verification uses only repository secrets named GMAIL_USER, GMAIL_APP_PASSWORD and DIGEST_TO. OPENSTATES_API_KEY and LEGISCAN_API_KEY are optional. Values never belong in files, fixtures, logs or job summaries. Submission and INBOX confirmation are recorded separately in the M0 mail receipt; SMTP acceptance alone is not a delivery pass.

A sent-week ledger suppresses ordinary repeated triggers. SMTP does not offer an atomic transaction with a Git commit: a crash between submission and ledger persistence can make delivery uncertain. The M1 delivery design must document that boundary rather than promise unconditional exactly-once delivery. GitHub scheduling can also be delayed; catch-up behavior is a release gate.
