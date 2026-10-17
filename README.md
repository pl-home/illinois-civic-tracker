# Illinois civic tracker

A small, factual Illinois legislative and county-party monitor. The intended product is a weekly digest that helps a constituent notice relevant actions and upcoming hearings. It does not infer a position or send messages to legislators.

**Browse the initial historical collection:** [Illinois civic tracker](https://pl-home.github.io/illinois-civic-tracker/). The basic browser was brought forward on October 17, 2026. It contains the reviewed 134-item Fritts export, search, measure-type filters, expandable source fields and a show-ceremonial option. It is a historical preview with explicit coverage limits; automatic updates and digest delivery remain undeployed. See [browsing-page design and operation](docs/BROWSING_PAGE.md).

## Current status

**M0 verification is in progress. M1 is not deployed.** The former local schedules were stopped before this repository was started. Historical source material is read only. This is a fresh repository; it contains no private vault, raw archive, email addresses or credential values.

For a focused code review, read [architecture and boundaries](docs/ARCHITECTURE.md), [M0 findings](docs/M0_FINDINGS.md), and one representative evidence file.

Read [the product vision](docs/PRODUCT_VISION.md), [the build brief](docs/BUILD_BRIEF_M0_M1.md) and [M0 findings](docs/M0_FINDINGS.md). Findings distinguish direct observations, normalization gaps and tests that still need time or corrected credentials. Hosted source access and Gmail self-delivery to INBOX pass. The follow-up audit reaches 96.59% comparison-key coverage and validates a five-page historical hearing fallback. Retained source gaps, upcoming hearing behavior and multi-day timing remain open.

The owner authorized a [small manual Qwen3 32B / DeepInfra evaluation](docs/INFERENCE_EVALUATION.md) within a USD 20 trial ceiling. The credential stays in Actions secrets; routine inference remains disabled. This optional evaluation does not change the deterministic M1 pipeline.

## Intended M1 operation

- Illinois collection nightly at 23:00 America/Chicago.
- Factual digest Mondays at 06:00 America/Chicago, including a quiet-week health summary.
- FTP XML first; one conditional floor-vote CSV retrieval, committee assignments, bounded party pages and Capitol Fax feed metadata.
- No AI in routine operation. Federal sponsorship is handled by owner-managed Congress.gov alerts.
- Compact public records; positions, correspondence and contact packets remain private.

No nightly collection or digest workflow is enabled yet. The only schedule in this repository is a time-limited M0 metadata observation, ending automatically after the verification window.

## Repository map

| Folder | Responsibility |
| --- | --- |
| config | Subjects, source policy and bounded M0 observation window |
| src/civic_tracker | Small source verification, normalization, privacy and rule modules |
| tests | Synthetic tests and a reviewed 134-item public sponsorship export |
| docs/evidence | Compact public verification outcomes, not raw source copies |
| data | Reserved for M1 compact records and ledgers |
| web | Accessible static browser template, styling and filter enhancement |
| .github/workflows | Tests, historical Pages publication, M0 source access and bounded observations |

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
