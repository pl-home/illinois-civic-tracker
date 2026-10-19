# Hosted PDF extraction

The owner authorized setting up PDF extraction on October 19, 2026. This is a
manually versioned trial, not a scheduled collector and not a replacement for official
vote validation. The paused committee implementation is not included in this release.

## Operation

Run the `Manual bounded PDF extraction trial` workflow for the explicitly configured trial version. The current version is `pdf-native-v2`. It requires the
existing `OPENROUTER_API_KEY` Actions secret. There is no new credential and no
local LLM. The job shares the existing source-workflow lock.

1. Fetch the configured public ILGA roll-call PDF through the normal sequential
   ten-second source gate. The source response is capped at two megabytes.
2. Native PDF parsing must find one or two pages, usable text on every page, and
   at most 24,000 UTF-8 text bytes. Larger or scanned-only documents stop. A
   deterministic instruction-pattern screen also rejects suspect source text;
   it is not a complete prompt-injection defense.
3. Record the source SHA-256, page count, native-text digest and a USD 0.005 hold
   in `data/pdf-extraction-ledger.json`. Commit and push before exposing the key.
4. Send the hash-bound native text with explicit page boundaries to OpenRouter.
   Only Qwen3 32B through `deepinfra/fp8` is allowed. No PDF plugin, provider
   fallback, OCR fallback, browsing, tools or reasoning mode. Raw PDF bytes stay
   on the runner. The first version used the explicit free `cloudflare-ai` parser;
   it returned an HTTP error without an extraction or measured charge receipt.
5. Return three short fields: document title, measure caption and motion. Each
   has a one-based page and a literal supporting quotation. Check schema, page
   range, quotation occurrence and value occurrence against the hash-bound native
   text. These are source-grounding checks, not independent factual validation.
6. Record API-reported cost and provider, settle the hold, and refresh the public
   usage panel. Source snapshots, bill records and vote choices are never changed.

The current sample is an official Senate Local Government committee roll call
for SB2769. It is historical evidence, not new activity on the trial date.

## Spending and replay

The hold covers the provider's entire 40,960-token context at the maximum allowed
USD 0.10/M input and USD 0.40/M output rates plus 600 output tokens. Shared limits
remain USD 0.02/day, USD 0.20/Monday-Sunday week in Chicago, and USD 20 lifetime,
including all earlier evaluations and news screening. Current advertised model
rates may be lower; recorded API cost determines settlement. The selected parser
was advertised free in v1. The current native-text version invokes no hosted
parser and cannot silently fall back to one.

An exclusive permanent claim file and a consumed ownership receipt permit only
one paid attempt from the runner. The committed ledger blocks another workflow
from reserving or replaying the same version. The native-text v2 gate allows
exactly one existing, uncertain v1 entry; it retains the original entry and hold,
archives its report, verifies the source PDF is byte-identical, and appends one
new reservation. No third version is accepted. Both liabilities count against
all shared caps. This is a distinct manual configuration change, not a retry loop. Missing/uncertain cost keeps the hold;
there is no automatic paid retry. A stale-day reservation cannot execute. Never
reset the ledger to retry. No automatic retry is allowed. The v1 hold remains outstanding unless a later
reconciliation supplies authoritative charge evidence; an HTTP failure alone is
not assumed free.

## Storage and review

Raw PDF, native text and request ownership live only in ignored runner scratch.
The first page is rendered to a seven-day workflow preview artifact for visual
review. Public records contain compact provenance, short quoted fields, limits
and measured charges. Full parser annotations and complete PDF text are not
committed. `data/pdf-extraction-report.json` is the trial receipt.

## Trial observations

[Hosted v1 run 39336117094](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39336117094)
passed native preflight of the one-page source, then returned `HTTPError` from
OpenRouter. No extraction was accepted, cost remains unknown, and its USD 0.005
hold is retained. The original generic error does not prove a root cause.
Safe numeric HTTP status is now retained on later requests.

[Read-only health run 39336488151](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39336488151)
confirmed authentication and the exact provider endpoint at 2026-10-19T22:39:39Z.
It made zero model calls and published no account balances, key labels or hashes.
The `openrouter-health.yml` workflow can repeat these free checks.

The rendered source was visually inspected: native text is available and page
structure is legible. This does not independently verify a model output.

Routine use remains disabled. Before enabling it, test more actual documents,
including tables, amendments and known extraction failures; preserve an
unverified outcome. The current text-only model cannot visually validate ballot
marks or vote columns. Prefer structured official HTML/XML where available.

## References

- [OpenRouter PDF input and explicit parser selection](https://openrouter.ai/docs/guides/overview/multimodal/pdfs)
- [Provider-specific Qwen3 32B endpoint catalog](https://openrouter.ai/api/v1/models/qwen/qwen3-32b/endpoints)
- [Usage accounting](BUDGET_USAGE.md)

Read `pdf_extract.py`, the PDF tests, `usage.py` and the workflow for implementation.

OpenRouter documents provider ZDR as applying to model inference, not enabled
plugins. Native text avoids the extra hosted PDF parser hop; it still sends the
public document text to OpenRouter and the pinned inference provider.
See [ZDR scope](https://openrouter.ai/blog/insights/zero-data-retention/).
