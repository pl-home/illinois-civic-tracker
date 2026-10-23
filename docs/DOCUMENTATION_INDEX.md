# Documentation index

Revision 14 — October 23, 2026. Every public Markdown guide is classified below.
Current status is authoritative for operating state; dated receipts retain their
original outcomes. Do not read a historical command as execution authorization.

Read first: [current status](CURRENT_STATUS.md), [execution guide](EXECUTION_GUIDE.md),
one [work packet](WORK_PACKETS.md), then only its named reference/code/tests.

| Document | Class |
| --- | --- |
| [AGENTS.md](../AGENTS.md) | current |
| [docs/AMENDMENT_INFERENCE_REQUIREMENTS.md](AMENDMENT_INFERENCE_REQUIREMENTS.md) | deferred |
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | current |
| [docs/BROWSING_PAGE.md](BROWSING_PAGE.md) | historical |
| [docs/BUDGET_USAGE.md](BUDGET_USAGE.md) | reference |
| [docs/BUILD_BRIEF_M0_M1.md](BUILD_BRIEF_M0_M1.md) | historical |
| [docs/CHANGE_FEED.md](CHANGE_FEED.md) | reference |
| [docs/COMMITTEE_DIAGNOSTIC_RERUN.md](COMMITTEE_DIAGNOSTIC_RERUN.md) | deferred |
| [docs/COMMITTEE_ROLLCALL_EVALUATION.md](COMMITTEE_ROLLCALL_EVALUATION.md) | deferred |
| [docs/COMMUNICATIONS.md](COMMUNICATIONS.md) | reference |
| [docs/CURRENT_STATUS.md](CURRENT_STATUS.md) | current |
| [docs/DAILY_REFRESH.md](DAILY_REFRESH.md) | reference |
| [docs/DASHBOARD.md](DASHBOARD.md) | reference |
| [docs/DIGEST_PREVIEWS.md](DIGEST_PREVIEWS.md) | reference |
| [docs/DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) | current |
| [docs/ERROR_JOURNAL.md](ERROR_JOURNAL.md) | reference |
| [docs/EXECUTION_GUIDE.md](EXECUTION_GUIDE.md) | current |
| [docs/HEARING_TRACKING.md](HEARING_TRACKING.md) | reference |
| [docs/IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) | current |
| [docs/INFERENCE_EVALUATION.md](INFERENCE_EVALUATION.md) | historical |
| [docs/INFERENCE_EVALUATION_RESULTS.md](INFERENCE_EVALUATION_RESULTS.md) | historical |
| [docs/INFERENCE_EVALUATION_V2.md](INFERENCE_EVALUATION_V2.md) | historical |
| [docs/M0_FINDINGS.md](M0_FINDINGS.md) | historical |
| [docs/MEDIA_REPORTS.md](MEDIA_REPORTS.md) | reference |
| [docs/MEMBER_HISTORY.md](MEMBER_HISTORY.md) | reference |
| [docs/NEWS_PAGINATION.md](NEWS_PAGINATION.md) | reference |
| [docs/OPENROUTER_PROVIDER_RECOMMENDATION.md](OPENROUTER_PROVIDER_RECOMMENDATION.md) | historical |
| [docs/OPENROUTER_SETUP.md](OPENROUTER_SETUP.md) | historical |
| [docs/PARTY_MONITORING.md](PARTY_MONITORING.md) | reference |
| [docs/PDF_EXTRACTION.md](PDF_EXTRACTION.md) | deferred |
| [docs/PRODUCT_VISION.md](PRODUCT_VISION.md) | current |
| [docs/RESUME_CHECKPOINT.md](RESUME_CHECKPOINT.md) | current |
| [docs/SESSION_ROLLOVER_REVIEW.md](SESSION_ROLLOVER_REVIEW.md) | current |
| [docs/VETO_SESSION_COVERAGE.md](VETO_SESSION_COVERAGE.md) | current |
| [docs/WORK_PACKETS.md](WORK_PACKETS.md) | current |
| [README.md](../README.md) | current |
| [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) | reference |

## Evidence, machine files and private documents

- `docs/evidence/*.json`: immutable dated observations/results, including failed trials. See the relevant guide for interpretation; no blanket current pass is inferred.
- `docs/evidence/documentation-handoff.json`: this reconciliation's checks and limitations.
- `docs/schemas/changes-v1.schema.json` and `docs/provenance/stage-a.json`: schema/provenance contracts, not operating status.
- [handoff.json](handoff.json): document classes and task IDs/dependencies/gates; machine navigation only, never authorization.
- `config/*.json`, `src/`, `tests/` and workflow YAML establish actual implementation. The checker verifies paths and a small set of policy invariants; it does not replace tests or live evidence.
- Private workspace README and vision/plan mirrors are synchronized separately. Old continuation notes, build briefs, external assessments and planning-history copies are historical. Private vault-location/credential notes never belong in this public index or upload.

For a quick structural review use status → architecture → one packet/guide → one
representative receipt and its tests. No need to load all collected records or
earlier conversations. Future model/provider/pricing/source claims require fresh
primary evidence before changing implementation, not copying old research tables.
