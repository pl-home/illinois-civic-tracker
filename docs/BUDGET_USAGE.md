# AI usage and budget reporting

The owner's later October 17, 2026 authorization raises the tracker budget to **USD 0.02 per day** and **USD 0.20 per week**. Weeks run Monday 00:00 through the following Monday 00:00 in **America/Chicago**, with Sunday shown as the last inclusive date. Both limits are enforced independently before a paid reservation. The original USD 20 lifetime ceiling remains in place. These are ceilings, not spending goals; collection frequency, candidate limits and the four-media-request daily safeguard are unchanged.

The homepage's **AI usage & budget** panel appears near the top, before collection health and member cards. It shows week dates, recorded weekly and daily charges, limits, remaining capacity and progress meters. Its expandable **Usage details** disclosure explains exact amounts, unsettled reservations, calculation time and scope. A disclosure is the HTML `<details>` / `<summary>` control also used for **How we find news**; a coordinated group is often called an accordion.

## Accounting

`src/civic_tracker/usage.py` is the shared calculation for enforcement and display. It reads the existing v1 evaluation, v2 evaluation and media ledgers without modifying them. The source of actual charges is the recorded OpenRouter response cost. Earlier evaluations are included. It does not fetch unrelated OpenRouter account activity or represent itself as a complete account invoice.

- A known charge replaces its reservation, including a known zero charge. It is not added to the reservation.
- An unknown charge keeps its entire reservation counted against available capacity; the UI shows it separately from money known to have been charged.
- Deterministically quarantined, uncalled entries do not incur a charge. An unexpected nonzero charge still counts.
- Entry attempt timestamps determine the Chicago date, falling back to the evaluation reservation timestamp or media's recorded local date. Unknown or timezone-free dates count conservatively in every current period and show a warning. They still count once in lifetime totals.
- Missing or invalid unsettled reservation amounts, negative money and non-finite money fail closed; they never become zero available liability.
- Daily and weekly boundaries are evaluated in Chicago, including daylight-saving transitions. Rolling seven-day and UTC-week totals are not used. Historical ledgers are never reset at a boundary.

`media_inference.prepare` applies daily, weekly and lifetime liability checks before persisting each USD 0.002 batch reservation. Multiple new batches in the same prepare call increase all three totals sequentially. The durable pre-network commit, runner-local ownership, live day-boundary checks and no-replay protections are unchanged. Changing dollar limits does not authorize another model task or provider.

## Refresh and review

The usage report is recalculated after normal media preparation/settlement and communications refresh, using the existing daily 01:00 Central pipeline. The static page displays its explicit calculation time and covered week; it is not a live billing widget. `python -m civic_tracker.media refresh-usage` updates just this deterministic report without fetching sources, exposing a model key or making a model call. A normal Pages push can publish it.

`data/inference-usage.json` contains the compact period totals; `data/dashboard.json` includes the same report for the browser. Detailed financial evidence remains in its existing ledgers. No key, account identifier or private financial information is copied into the public usage summary. The public 20 MB JSON and 650 KB browser-artifact limits are unchanged.

Review `tests/test_usage.py` for Chicago Monday/Sunday and DST boundaries, exact weekly reservation limits, known-versus-held costs, malformed costs and read-only reporting. The existing inference tests continue to verify daily/lifetime caps and crash replay behavior. Previous evidence files retain the older limits that applied when those runs occurred.

## Hosted acceptance

The [Pages deployment](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39049908111) and [verification run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39049908094) succeeded October 17. The live panel was checked near the top of the page, before member activity, with weekly and daily limits of USD 0.20 and USD 0.02 and a visible Central-time calculation timestamp.

The initial October 12–18 report records **USD 0.00220856 charged**, no unsettled reservations, and **1.10428%** of the weekly limit used. Financial ledgers remained byte-identical, and publishing this report made no model calls. All 143 tests and the privacy check passed. Independent review found a missing-reservation default that could understate liability; it now fails closed and has a regression test. Compact evidence: [budget-usage-validation.json](evidence/budget-usage-validation.json).
