# Illinois civic tracker

A factual tracker for Bradley Fritts and Li Arellano, Jr. (GA104), and Darin
LaHood, Dick Durbin and Tammy Duckworth (Congress119), plus the two Lee County
party organizations. Public browsing is on [the website](https://pl-home.github.io/illinois-civic-tracker/);
private positions, notes and correspondence stay in Obsidian. No automatic outreach.

## Start here — October 23, 2026

1. [Current status and decisions](docs/CURRENT_STATUS.md): implemented boundaries, actual receipt dates and known failures.
2. [Execution guide](docs/EXECUTION_GUIDE.md): safe commands, ownership, side effects and stop rules.
3. [One work packet](docs/WORK_PACKETS.md): exact starting files, dependencies and acceptance criteria.
4. [Product vision](docs/PRODUCT_VISION.md) and [implementation plan](docs/IMPLEMENTATION_PLAN.md), revision 12.
5. [Documentation index](docs/DOCUMENTATION_INDEX.md): every public guide classified as current, reference, historical or deferred.

Stages A–C and Stage D **previews** are implemented within their documented
coverage limits. [HTML/text previews](docs/DIGEST_PREVIEWS.md) are available;
**email delivery is disabled pending owner review**. Full Stage D and M1 remain
incomplete. PDF work and daily new committee-roll-call extraction stay deferred.

## What runs, and what does not

The GitHub daily workflow targets **01:00 America/Chicago** without an AI chat or
local computer. It collects official source metadata/calendars, bounded party
pages and news/communications. Only public media-headline relevance uses Qwen3
32B through DeepInfra, capped at **USD 0.02/day, 0.20/week and 20 lifetime**.
Unsettled requests stay held. [Budget accounting](docs/BUDGET_USAGE.md).

A configured schedule or green job does not establish current collection. The
October 23 scheduled run entered the bounded late window, refreshed sources,
ran two approved media-model calls, and published a partial but current site.
[Current status](docs/CURRENT_STATUS.md) gives the exact evidence. P01/P02 and
P03 are complete within their limits; the next available offline implementation
packet is P05 storage-growth simulation. P04 remains source-dependent.
Manual trial workflows are not authorization to run them. Old Codex/Windows
schedules remain outside this runner and must not be reactivated here.

The browser provides member actions/votes, committee roles/meetings, accepted
changes, paginated history and news, and separate office/campaign/party material.
The Caucus Blog is explicit caucus-wide context for Fritts, not proof of his
personal authorship. Historical imports and the 134-item export are not new
activity or the discovery universe. [Architecture](docs/ARCHITECTURE.md),
[source coverage](docs/DAILY_REFRESH.md), [communications](docs/COMMUNICATIONS.md).

## Safe offline verification

Use Python 3.11 from the actual repository root, with the package installed:

```sh
python scripts/check_handoff.py
python -m civic_tracker.privacy
python -m unittest discover -s tests -v
python -m civic_tracker.browse --output .local/handoff-site
python -m civic_tracker.digest preview --output .local/handoff-digest
```

These do not collect sources, use credentials, invoke a model or send mail.
The checker validates docs/packet dependencies and disabled-feature flags, not
live source health. [Commands with side effects](docs/EXECUTION_GUIDE.md).

## Repository map and boundaries

| Path | Responsibility |
| --- | --- |
| `config/` | Reviewed identities, source bounds, schedules and feature limits; no secret values |
| `src/civic_tracker/` | Collection, accepted facts, rendering, diagnostics and accounting |
| `data/` | Compact public records/receipts/ledgers; collector-owned, not scratch |
| `web/` | Static browser templates and enhancement |
| `tests/` | Offline regressions and reviewed public/synthetic fixtures |
| `docs/` | Current guides, explicit future tasks and immutable dated evidence |
| `scripts/check_handoff.py` | Read-only documentation/packet consistency check |
| `.github/workflows/` | Existing hosted collection/publication and restricted manual tools |

Canonical JSON is capped at 20 MB, the shared ledger at 10 MB, base public files
at 650 KB and member/news HTML at 3 MB separately. No raw HTML/PDF/ZIP/CSV archive,
private vault, credential, address or machine profile path is published. Keep
source/financial history and failed receipts intact; do not prune to make checks
pass. Main ILGA requests are sequential with verified TLS and at least ten-second
spacing (twenty for backfill). Use a noreply commit identity and explicit owned
paths. Actual reused code is disclosed in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
