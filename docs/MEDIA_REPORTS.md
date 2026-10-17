# Recent media reports and narrowly enabled inference

Owner authorization, October 17, 2026: put recent reports under each member's witness-slip guidance and enable inference with a target below one US cent per day. This supersedes the older no-routine-inference rule **only for media relevance screening**. Party categorization, legislative topic inference, amendment/shell-bill detection and model-generated synopses remain disabled. The failed v1/v2 evaluation gates remain failed; this constrained Boolean task does not claim to pass them.

## Display and evidence

Each of the five member cards shows up to three latest eligible articles found within 90 days. The collector searches free Google News RSS feeds for the member's name, then requires a dated article, a name anchor in its title/snippet and a source host in the reviewed major/Illinois newsroom list in `config/media.json`. Explicit opinion/editorial/endorsement titles, government offices, campaigns, party sites and unlisted publishers are excluded. The list is a source selection policy, not an assertion of political neutrality or article accuracy.

Feed results are sorted by publication timestamp and identical normalized headlines are deduplicated. Up to four candidates per member are screened; the page may show fewer than three. This is not comprehensive media monitoring: indexing gaps, body-only mentions, paywalls, ambiguous titles and the candidate bound can omit coverage. An absent report is not proof of absent activity. Similar reports about the same event may appear when their headlines differ.

Only public title, publisher, date and link are displayed, with attribution. RSS descriptions are brief feed metadata, often just a repeated headline, and are not full article text. No paywall, logged-in content or article body is fetched. Google News article links route to publishers; the UI identifies that route and publisher access terms still apply. Feed metadata is not independently verified against article bodies, and the model cannot supply or change it. Collection failures retain earlier screened reports within the age window and display incomplete coverage.

## Model and spending guard

The enabled task uses `qwen/qwen3-32b` through `deepinfra/fp8` on OpenRouter. Provider fallback, tools and reasoning are disabled; structured output is required. The entire model answer is a list of supplied article IDs and Boolean relevance decisions. Unknown IDs, duplicate/missing IDs, extra fields and malformed answers are rejected. No quotations, summaries, URLs, dates, invented facts or external actions can enter the product through model output. Known instruction-like source text is quarantined before a call. This limits output authority rather than claiming prompt injection is solved.

At most 20 candidates are considered per run, in batches of eight, with at most four media calls per Chicago day. Full request bytes plus an 8,192-byte wrapper allowance are bounded by 16,000; completion is bounded by 512 tokens. At the enforced maximum USD 0.10/input-million and USD 0.40/output-million, worst-case token charge is USD 0.0018048. Each call reserves USD 0.002. Endpoint metadata is checked live; extra nonzero request fees or incompatible routing fail closed.

The hard application cap is **USD 0.009 per America/Chicago day**, including today's previous evaluation charges and unresolved liabilities, and **USD 20 lifetime**, with no reset. Actual costs replace reservations when known; unknown charges retain the full reservation and stop the batch loop. These limits cover this project's calls, not unrelated use of the same OpenRouter account/key. The remote key must also have a spending limit no greater than USD 20. Content/prompt/model/provider caching avoids repeat calls for unchanged headlines. Invalid/uncertain attempts are not retried automatically.

## Durable execution and operation

`python -m civic_tracker.media prepare` fetches five bounded feeds without a model key, persists candidates, cache decisions and budget reservations. The workflow commits and pushes these reservations **before** exposing `OPENROUTER_API_KEY` to `python -m civic_tracker.media execute`. Run-local ignored ownership is consumed before each completion request. A replacement runner cannot recreate ownership for old reservations; a lost settlement therefore consumes reserved capacity instead of allowing a duplicate charge. Do not delete/reset ledgers or rerun a paid request to clear an uncertain result. Deferred never-attempted content may become eligible on a later day.

The existing daily workflow runs this separate phase after official collection at 01:00 Central, then persists settlement and builds the static website. `media.yml` supports an authorized one-time media-only refresh without repeating legislative collection. Both share the source workflow lock; Pages publication checks the final source SHA. A runner crash can leave a conservative reservation without a completed display update; inspect the receipt before further action.

## Review entry points

| File | Purpose |
| --- | --- |
| `config/media.json` | Queries, publisher allowlist, time/candidate bounds, exact enabled model policy |
| `src/civic_tracker/media.py` | Safe feed parsing, metadata selection, health and snapshot application |
| `src/civic_tracker/media_inference.py` | Cache, structured decisions, budget reservations and one-attempt ownership |
| `data/media-state.json` | Bounded metadata candidates and per-member feed health |
| `data/media-inference-ledger.json` | Durable budget and known/unknown cost evidence; never reset |
| `data/media-inference-report.json` | Latest status, counts, decisions, costs and safe error codes |
| `data/media-inference-cache.json` | Content/prompt-keyed decisions and invalid-result receipts |
| `data/media-work.json` | Latest bounded work manifest and fixed structured-output requests |
| `tests/test_media.py`, `tests/test_media_inference.py` | Source filters, rendering, privacy, accounting and replay regressions |

The static Pages artifact still contains only the eight reviewed browser files; detailed model manifests and ledgers stay in the public repository, not the browser payload. No secret or private notes enter them. The privacy scanner permits opaque **public Google News article identifiers only in the exact HTTPS article namespace**; credential-shaped values and other private-data checks remain active everywhere. No raw HTML, feed XML or article copies are stored. Candidate state is bounded; cost history is retained for accounting. The public data-size guard stops new inference at the project's 20 MB JSON budget rather than pruning financial evidence.

Hosted activation results and measured cost will be recorded here after the first run.
