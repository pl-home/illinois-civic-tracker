# Stage D: digest previews

> Documentation review: October 28, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

Delivered October 20, 2026: the preview slice of Stage D. The owner approved
the preview on October 27 and requested an owner-only update every three days.
The separate delivery workflow reserves an immutable preview before accessing
Gmail secrets, sends only to the configured owner plus-address, checks the exact
message in that mailbox, and retains an address-free result. No legislator,
party or campaign recipient is permitted. Full M1 remains incomplete until the
hosted path produces its first confirmed receipt.

## Review entry points

- [Browser preview](https://pl-home.github.io/illinois-civic-tracker/digest-preview.html), also linked near the homepage top.
- [Plain text](https://pl-home.github.io/illinois-civic-tracker/digest-preview.txt).
- [Selection manifest](https://pl-home.github.io/illinois-civic-tracker/digest-preview.json): exact windows, revision IDs, source-input SHA-256 fingerprints, omissions, health and `delivery.enabled: false`.
- [Acceptance receipt](evidence/stage-d-preview.json).

The existing browsing build generates previews, including after the daily 01:00
Central collection. It adds no collector or weekly sending job. Preview files
contain no recipient or private notes.

## Selection contract

`digest.py` consumes accepted shared revisions, validated current hearing facts
and existing public source receipts. It reuses the feed validation gate and
configured deterministic relevance rules. Each selected item includes a reason,
evidence link, source date/precision, first observation and revision observation.
Topics are provisional rule matches, never the owner's stance.

Activity runs Monday 06:00 to the following Monday 06:00 America/Chicago, end
exclusive. Before that end, the preview is explicitly **week so far**, through
its source-snapshot timestamp inclusive. A Monday preview after 06:00 selects
the completed period. Local boundaries handle DST; this is separate from the
Monday–Sunday spending-accounting week. Upcoming opportunities use the ten days
following the preview as-of timestamp.

Only the latest validated revision per event before the cutoff is considered.
Baseline/history/held entries, ceremonial items and votes with no opposition
are suppressed under existing relevance policy. Newly discovered old source
actions do not become this week's activity; substantive corrections can remain
visible as corrections. The manifest counts suppressed and bounded items.
Selection does not mark an event delivered or prove complete source coverage.

Sections separate schedule/agenda revisions, member actions, county-party edits,
newsroom metadata and office/campaign/party communications. Publisher claims
remain attributed. Votes retain raw choice, motion/result detail and tallies;
the title links to a validated bill page when available and the choice to vote
evidence. No generated bill synopsis is added.

Party-page changes include a compact **Before / After** excerpt centered on the
changed span. The excerpt is evidence for review, not a full page archive; the
source URL, observation time and SHA-256 fingerprints remain authoritative.

Future hearings may come from quiet baseline facts, but only with fresh proof
(at most 48 hours), accepted scope and scheduled/rescheduled status. Postponed,
canceled, undated, stale or withheld notices cannot become usable opportunities.
Accepted meeting/agenda changes appear separately. A witness-form link needs
fresh (24-hour) successful verification, the exact notice URL/hash and hearing
identity, matching bill/amendment, a healthy member calendar and an allowed
HTTPS submission URL. Results links are not forms. No slip is submitted.

Quiet previews still show health: source dates, stale/partial checks, withheld
scopes and link-only first-party coverage. The initial real-data preview selects
zero new revisions and zero usable future notices. This is a quiet snapshot with
partial coverage, not proof of inactivity. Synthetic form tests do not establish
a genuine live open-form acceptance pass.

## Reproduction and limits

From a checkout with the package installed:

```sh
python -m civic_tracker.digest preview --output .local/digest-preview
python -m civic_tracker.browse --output .local/site
python -m unittest discover -s tests -v
python -m civic_tracker.privacy
```

Default as-of time is the latest recognized source receipt, not the build clock.
Identical inputs produce identical preview bytes/ID. Optional `--as-of` takes an
offset-bearing timestamp; `--week-ending` takes a Monday date. Backdating newer
mutable source files is rejected with `digest-historical-source-snapshot-required`.
Replay requires the frozen source/config revision matching the manifest and the
same preview policy. Choosing an older activity window still uses the current
snapshot's health and future opportunities, not reconstructed historical proof.

Four allowlisted files (HTML, text, JSON, CSS) total at most 90,000 bytes inside
the unchanged 650,000-byte base ceiling, now 14 files. Member/news HTML retains
its separate 3,000,000-byte cap; combined publication remains at most 3,650,000
bytes. Select at most 20 revisions, six per section, eight hearings and six
displayed agenda items per hearing; omissions and source links stay visible.
No evidence, source history or financial ledger is deleted. The standalone
output rejects unowned files, symlinks and concurrent writes. Rendering escapes
source text, validates links, privacy-checks every output and applies restrictive
CSP with local CSS and no scripts/forms/tracking.

`config/digest.json` remains preview-only and must keep `delivery_enabled` false.
`config/digest-delivery.json` owns the separate three-day owner workflow. Its
durable state is `data/digest-delivery.json`; a reservation is committed before
secrets are exposed, and an SMTP submission without exact inbox confirmation is
held as uncertain. The workflow is a daily gate so the interval is measured in
elapsed time rather than an ambiguous cron expression.

## Acceptance and remaining gates

`tests/test_digest.py` covers normal/quiet/partial snapshots; sparse news;
backfill/corrections; revision deduplication; vote links/tallies; party attribution
and held images; invalid/private content; exact cutoff/DST; config/input hashes;
repeatable files; concurrent/unowned output; and fresh versus stale/mismatched
witness proof. Fixture examples are explicitly synthetic and never inserted
into the public ledger. The complete offline suite passes 319 tests; hosted
verification is recorded separately in the receipt.

The owner review approved section order, detail, quiet/partial wording and HTML
versus text on October 27. Remaining acceptance is operational: confirm the
first hosted three-day reservation and inbox receipt, then review any
uncertain/failure record before allowing another attempt. PDF work stays
deferred.

