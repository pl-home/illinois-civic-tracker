# Hosted PDF extraction

The owner authorized setting up PDF extraction on October 19, 2026. This is a
single manual trial, not a scheduled collector and not a replacement for official
vote validation. The paused committee implementation is not included in this release.

## Operation

Run the `Manual bounded PDF extraction trial` workflow once. It requires the
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
4. Send that exact PDF as a base64 file with OpenRouter's explicit free
   `cloudflare-ai` file-parser engine. Only Qwen3 32B through `deepinfra/fp8` is
   allowed. No provider fallback, OCR fallback, browsing, tools or reasoning mode.
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
is advertised free; leaving the parser engine unspecified is prohibited.

An exclusive permanent claim file and a consumed ownership receipt permit only
one paid attempt from the runner. The committed ledger blocks another workflow
from reserving or replaying this trial. Missing/uncertain cost keeps the hold;
there is no automatic paid retry. A stale-day reservation cannot execute. Never
reset the ledger to retry. Failures can require an explicit later trial/version
and a separate review of any outstanding liability.

## Storage and review

Raw PDF, native text and request ownership live only in ignored runner scratch.
The first page is rendered to a seven-day workflow preview artifact for visual
review. Public records contain compact provenance, short quoted fields, limits
and measured charges. Full parser annotations and complete PDF text are not
committed. `data/pdf-extraction-report.json` is the trial receipt.

Routine use remains disabled. Before enabling it, test more actual documents,
including tables, amendments and known extraction failures; preserve an
unverified outcome. The current text-only model cannot visually validate ballot
marks or vote columns. Prefer structured official HTML/XML where available.

## References

- [OpenRouter PDF input and explicit parser selection](https://openrouter.ai/docs/guides/overview/multimodal/pdfs)
- [Provider-specific Qwen3 32B endpoint catalog](https://openrouter.ai/api/v1/models/qwen/qwen3-32b/endpoints)
- [Usage accounting](BUDGET_USAGE.md)

Read `pdf_extract.py`, the PDF tests, `usage.py` and the workflow for implementation.
