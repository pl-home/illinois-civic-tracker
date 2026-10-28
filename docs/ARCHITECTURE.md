# Architecture and reviewer guide

Revision 17 — October 28, 2026. Current boundaries are in
[CURRENT_STATUS.md](CURRENT_STATUS.md); dated M0 designs/results remain in
[M0_FINDINGS.md](M0_FINDINGS.md) and Git history, not competing active architecture.

## Data flow

```text
official source adapters  +  public party/communications/news metadata
             |                          |
compact source records and dated health; media-only bounded relevance screen
             |
change_sources -> changes: source-scoped facts, revisions, completion/QA
             |
common accepted gate -> homepage / JSON / Atom / member history / digest preview
```

Source publication date, legislative event date, first observation, source check,
accepted revision and future delivery state are distinct. Quiet baselines,
parser migrations and backfill do not become new activity. Partial sources
retain last-good facts and unfinished coverage; disappearance is not removal
unless the source's completeness contract supports it.

## Ownership map

| Responsibility | Code / configuration | Important boundary |
| --- | --- | --- |
| Daily gate/orchestration | `daily.py`, `config/daily.json`, `daily.yml` | 01:00 Central target; local-date gate; source isolation; review guard |
| Illinois bills/floor votes | `daily_state.py`, `vote_csv.py`, `http.py`, `project.json` | FTP changed XML plus floor CSV; raw choice/motion/conflicts retained; committee votes separate |
| Federal bills/floor votes | `daily_federal.py`, `dashboard_sources.py` | Complete pagination before removals; official House/Senate evidence; unknown join dates remain undated |
| Calendars/roles | `dashboard_collect.py`, `hearings.py`, `hearing_collect.py`, `hearing_changes.py`, `hearing_view.py` | Stable notice IDs, agenda/amendment deltas, explicit status, expiring exact witness proof |
| County parties | `parties.py`, `config/parties.json` | Eleven pages plus poster; six mention feeds; deterministic symmetric relevance; held image/ambiguous edits |
| News | `media.py`, `media_inference.py`, `news_archive.py`, `config/media.json` | Metadata only; exact supplied-ID screening; reservation before paid request; no factual generation |
| Direct communications | `communications.py`, `config/communications.json` | Publisher-owned office/campaign/party sections; explicit House caucus-wide exception for Fritts; retained-source flags |
| Shared event layer | `change_sources.py`, `changes.py`, `relevance.py`, `change_feed.py` | Schema/fingerprint/source gate, quiet/replay/correction handling, source-scoped QA |
| Static browsing | `dashboard.py`, `browse.py`, `member_history.py`, `web/` | No network, source-state mutation, credential or model access during builds |
| Stage D previews/delivery | `digest.py`, `delivery.py`, `config/digest.json`, `config/digest-delivery.json` | Same accepted revisions and exact selection hashes; owner-only three-day delivery reserves before SMTP and retains uncertainty |
| Diagnostics/accounting | `error_journal.py`, `model_diagnostics.py`, `usage.py`, `privacy.py` | Sanitized bounded journal; permanent charges/holds; no raw exceptions, prompts, private data or credentials |
| Manual historical tools | `mail_test.py`, `inference_eval.py`, `pdf_extract.py`, `rollcall_eval.py` | Dated trials, not general repair runners or activated product features |

## Writes and side effects

Collectors own `data/`. `changes collect` is offline but writes the ledger/QA;
it is not a read-only inspection command. `media prepare` can reserve paid
liability; `media execute` can call the model. CI/Pages/build/preview read accepted
inputs and write only bounded publication/scratch outputs.

State-writing workflows share `m0-source-evidence`, check out current main and
persist before publication. Paid reservations must be durable before request
secrets become available. Pages uses a separate publication lock and SHA guard;
a green deploy job can still skip an obsolete artifact. Daily green can mean a
skipped time gate. The operational gap is documented, not silently fixed here.

The owner-only digest workflow runs a daily gate and sends only when three
America/Chicago days have elapsed since the last inbox-confirmed delivery. Its
durable ledger persists the reservation before secrets are exposed and retains
uncertain SMTP outcomes. M0 Gmail/INBOX proof remains a separate historical
self-test; this workflow makes no exactly-once SMTP claim and never addresses
legislators, parties or campaigns.

## Trust, identity and storage

All source text is untrusted data. Accepted evidence needs source/identity/schema
checks, not an official-looking URL or a model answer. TLS root/hostname checks
remain enabled; configured issuer intermediates are fingerprint-pinned, not new
trusted roots. Source access stays inside reviewed host/path/rate budgets.

Canonical JSON <=20,000,000 bytes; change ledger <=10,000,000; journal <=96 KiB.
The fourteen base public files include four digest files (<=90,000 combined)
and total <=650,000. Member/news HTML has a separate <=3,000,000 cap; combined
<=3,650,000. Members show 25 activities/page; news five/page up to 100 screened
metadata records/member over 200 days. Homepage news uses 90 days/three items.
Annual Git growth is not bounded by a live-file cap and still needs measurement.

No full article/PDF/site mirror, private correspondence, contact address or
credential is copied to public Git/artifacts. Obsidian and prospective Claude
access remain separate. Source/financial history is never reset to clear a gate.

## Focused review

Read current status, the relevant packet and one guide; inspect only its module,
config, tests and a representative dated receipt. Start with
`tests/test_changes.py`, `tests/test_hearing_changes.py`, `tests/test_parties.py`
or `tests/test_digest.py` for the respective layer. All commands and dangerous
near-names are classified in [EXECUTION_GUIDE.md](EXECUTION_GUIDE.md).
[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md) prevents old trial setup notes
from being mistaken for current permissions.

