# Stage C: hosted county-party monitoring and deterministic relevance

> Documentation review: October 22, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

**October 20 release verified:** [the hosted source-only check](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39464619419)
passed for all twelve page/asset sources and six mention feeds, with zero added
change alerts, zero model calls and all ten financial/trial records unchanged.
All 298 offline tests, hosted CI, privacy and publication checks passed. The
[dated receipt](evidence/stage-c.json) records exact coverage, sizes and remaining
source-dependent follow-ups. The published page and its disclosures were checked
in the browser.

This port checks the Lee County Democrats and Lee County IL Republican Central
Committee with the existing daily **01:00 America/Chicago** hosted refresh. It
does not need an open chat, local computer, local model or new paid service.
The former Windows/Codex schedules remain stopped. PDF work and digest delivery
remain deferred. No new model task or model request is enabled.

## Start here for review

- `config/parties.json`: eleven individually reviewed public HTML pages, one
  explicitly watched first-party GOP poster, six Capitol Fax search subjects.
- `src/civic_tracker/parties.py`: bounded requests, robots policy, parsing,
  last-good observations, page/asset changes, shared-ledger adapter and homepage.
- `src/civic_tracker/relevance.py` and `config/relevance.json`: auditable topic
  associations, provisional words and index-only noise reasons; no owner stance.
- `src/civic_tracker/changes.py`: source binding, quiet baselines, immutable
  accepted revisions and withholding. `changes-v1.schema.json` adds LOCAL
  organization entities; party activity is never assigned to every legislator.
- `tests/test_parties.py`: stateful symmetric fixtures and failure/recovery cases.
- `data/party-state.json`, `data/mentions-state.json`: representative compact
  observations and source health. `docs/evidence/stage-c.json`: dated acceptance.

## What is collected and displayed

The homepage has a **Lee County party websites** section with each organization's
page health and check dates, attributed relevant edits and a show-held-for-review
disclosure. Accepted changes also use the existing common HTML/JSON/Atom gate.
This is organization coverage, separate from the existing member-name-filtered
party feeds in each member's direct-communications section and from newsroom
reporting. Party claims remain attributed to the publisher, not independently
verified facts. No automatic advocacy, message or witness slip is sent.

Both organizations use the same parser, categories, bounds and policy. A changed
span or reviewed page purpose gives an explicit leadership/contact, event/meeting,
candidate/endorsement or published-position reason. A category is a retrieval
aid, not an AI interpretation of a party's motives, stance or political meaning.
The UI retains the reason, before/changed-span excerpts and source fingerprints.
An observed page edit has an observation time and an unknown action/source date.
After a failed interval it is labeled as observed after a collection gap.

Each newly configured page and parser version starts quietly. Whitespace,
scripts, navigation, forms, social widgets/counters and recurring share controls
are excluded. This compact port cannot reparse an archived old raw page on parser
migration: it explicitly rebaselines and therefore cannot promise to recover an
edit coincident with that migration. It does not claim that such an edit was
cosmetic. Previous accepted revisions remain intact.

Unexpectedly empty/unrecognized pages and a text loss over 60% fail closed. Failed
pages keep last-good content and dates without advancing the accepted source
cursor. Recovery compares to the last-good projection; it does not call recovered
old content a newly dated event. Coverage older than 48 hours is withheld/stale.
An image reference or watched-poster byte change is held for human visual review;
no OCR, image interpretation or model fallback is run. An unchanged image URL
does not prove unchanged image bytes except for the one explicitly watched asset.

Public contact targets are fingerprinted and redacted rather than published in
the projection. URL/body privacy gates still apply. Visitors can open the public
source for contact details. HTML source strings are escaped when displayed.

## Bounds and source policy

- Twelve page/asset URLs total; no recursive crawl or auto-added detail pages.
- Two robots files plus the configured sources: sequential anonymous requests,
  verified TLS, descriptive User-Agent, 25-second timeouts, at least one second
  between regular source requests, honoring a published crawl delay up to ten
  seconds. Larger delays require policy review; requests are withheld.
- Each HTML response at most 1.5 MB; the sole PNG at most 3 MB. Read into memory
  only. No raw HTML, full article, image archive or authenticated source is stored.
- A page projection at most 18 KB of text/220 lines, 120 first-party links and
  50 first-party image references; public contact values are redacted.
- `party-state.json` at most **350 KB**, mention metadata at most **50 KB**, both
  inside the existing **20 MB** total working JSON budget. Shared revisions remain
  inside the existing **10 MB** ledger cap; reaching a bound fails closed.
- Changed-page evidence is a minimal projection/fingerprint and two excerpts of
  at most 360 characters in the common ledger. A hash is a comparison receipt,
  not a recoverable screenshot or proof of every word on a past page. No raw
  exceptional snapshot archive is introduced. The image itself is not retained.
- Existing 650 KB base and 3 MB generated member/news HTML caps are unchanged.
- Existing source/cost ledgers and old evidence are not deleted or reset.

Capitol Fax gets one anonymous search feed per member and one for **Lee County**,
up to twelve candidates each. Reviewed surname queries cover name aliases within
that single bound; the county query uses the quoted phrase. WordPress combines
search terms with AND, so an OR expression is not used. Only public, dated, exact headline name matches are
retained; protected titles, future/invalid dates and other hosts are excluded.
A search result is not evidence of a body-text mention. A zero count says nothing
about mentions inside an article or paywalled content. This is separate mention
coverage, not an additional model-screened newsroom pipeline. A robots 404 means
no robots file; 403/429/5xx or TLS/network failure does not receive that exception.

Topic associations check available committee/statute structure before provisional
keyword matches, with exact reasons. The current compact Illinois XML does not
provide statute citations; no citations are invented. An explicit committee
referral in an action can supply structure. Changes without a priority topic
remain eligible when otherwise noteworthy. Ceremonial descriptions and zero
recorded nays are index-only in the new feed, with a visible bounded show-hidden
path and audit counts. Unknown tally never means unanimity; resolutions are not
discarded wholesale. Existing historical member sections retain their own rules.

## Operation and troubleshooting

`python -m civic_tracker.parties collect` checks public pages and mention feeds;
source errors are isolated per page/subject. `python -m civic_tracker.changes
collect` ingests accepted observations; `python -m civic_tracker.browse` publishes.
The daily workflow runs Stage C before the shared change gate. A separate manual
**Check county-party websites** workflow shares the existing source lock and
stale-publication guard, accepts no credentials, and verifies that all media
inference ledger/work files remain byte-identical. It has no independent schedule.

The existing bounded structured error journal ingests each party/mention source,
including recurring error codes and recovery. Parser/shrink/robots/privacy failures
remain failures rather than disappearing content. Workflow failures use the same
always-run finalizer. Routine source health remains visible even with zero changes.
No article or exception response body is copied into diagnostics.

## Reuse and remaining limits

The reviewed URL list and extraction/suppression principles come from the owner's
earlier watcher. Its runner, raw archives, snapshot cadence, Windows schedules
and local-model review were not copied. This is an independent small port using
BeautifulSoup already installed by the project. The existing shared Atom renderer
continues the disclosed Hawaii Appleseed adaptation in THIRD_PARTY_NOTICES.md.

Synthetic symmetric edits validate change semantics. A first live unchanged
baseline is not proof of a genuine subsequent officer/event change. Multi-day
source-change observation and a poster requiring actual visual review remain
source-dependent follow-ups. M1 remains incomplete until Stage D digest acceptance
and remaining hearing/source/storage gates pass. PDF work stays deferred.
