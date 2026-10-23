# News discovery and direct communications

> Documentation review: October 22, 2026. Operational reference; dated acceptance sections remain historical. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

Owner update, October 17, 2026: make news discovery visible and display campaign releases and direct office/party communications in their own section. This enables deterministic public first-party collection alongside the existing daily news phase. It does not enable the legacy AI party classifier, automatic outreach, Facebook scraping, private email access or a new local schedule.

## How news is found

Each member card now has **How we find news about [member]**, with the exact Google News search, an ordinary search link, the RSS URL actually used, candidate count and publisher policy link.

| Member | Exact query |
| --- | --- |
| Bradley Fritts | `"Bradley Fritts" OR "Brad Fritts" when:200d` |
| Li Arellano, Jr. | `"Li Arellano" when:200d` |
| Darin LaHood | `"Darin LaHood" when:200d` |
| Dick Durbin | `"Dick Durbin" when:200d` |
| Tammy Duckworth | `"Tammy Duckworth" when:200d` |

The collector reads up to 150 RSS items, checks publication dates, requires a reviewed newsroom host and a name anchor in the headline/snippet, excludes explicit opinion/editorial titles, deduplicates normalized headlines and retains at most 30 candidates per member. Qwen's bounded relevance decisions select from these IDs; it does not discover stories, change their dates, generate their titles, verify their contents or rank them by importance. Date sorting determines display order. Homepage reports use 90 days/three items; member news pages use 200 days/five per page with a bounded 100-item screened cache. Up to four not-yet-screened candidates per member are considered per run within the shared daily limits. [MEDIA_REPORTS.md](MEDIA_REPORTS.md) describes cache, uncertainty and spending controls.

This is an indexed-feed search, not exhaustive web coverage. Full articles are not read. Source ownership determines the section: newsroom reporting about an election remains in news. A newsroom can reprint a release; the current metadata-only collector cannot certify original authorship or identify every reprint. It does not label a newspaper article a campaign statement merely because it covers a campaign.

## Direct communications

Below news, each member has **Member, campaign & party communications**, with separate **Member office**, **Campaign releases** and **Party/caucus** groups. Each group displays up to three dated items from the preceding 90 days. Labels identify the publishing institution; they do not imply that the politician personally wrote every item. Allegations and policy characterizations in titles remain the publisher's statements.

Configured automatic sources:

| Source | Format and scope |
| --- | --- |
| Fritts office, `repfritts.com/latest-news/` | Dated public HTML listing |
| Arellano office, `senatorli.com/feed/` | Advertised RSS |
| LaHood office, `lahood.house.gov/news` | Dated public HTML listing |
| Durbin office, `durbin.senate.gov/newsroom/press-releases` | Dated public HTML listing |
| Duckworth office, `duckworth.senate.gov/news/press-releases` | Dated public HTML listing |
| Fritts campaign, `fritts4rep.com/feed/` | Advertised RSS |
| LaHood campaign, `lahoodforcongress.com/feed/` | Advertised RSS |
| Illinois Senate Republican Caucus, `ilsenategop.org/feed/` | Advertised RSS; name match required |
| The Caucus Blog, Illinois House Republican Caucus | Advertised RSS; caucus-wide posts shown only for Fritts, the tracked Illinois House member |
| Senate Democratic Caucus press releases | Dated public HTML listing; name match required |
| Lee County Democrats, `leecodemocrats.com/feed/` | Advertised RSS; name match required |
| Lee County GOP, `leecountyilgop.org/feed/` | Advertised RSS; name match required |

The exact verified HTTPS URLs, per-member source mappings and notes are in [config/communications.json](../config/communications.json). Shared party feeds normally must name the member in their headline or bounded excerpt. The owner-authorized House caucus exception is explicit: The Caucus Blog supplies caucus-wide context for Fritts, with publisher attribution and a note that authorship/endorsement is not established. It is not assigned to the tracked Illinois senator or federal members. This is a member-communications view, not a replacement for broader monitoring of party websites.

Three source links remain **link-only**: Arellano's older campaign site and the Durbin and Duckworth campaign sites without verified dated feeds. The original House GOP link-only homepage was replaced October 20 by The Caucus Blog's verified advertised RSS feed. They are visible in source coverage and are not represented as automatically collected. Fritts' and LaHood's campaign feeds are active collection sources but their latest posts observed during setup were July 15, 2025 and November 5, 2024 respectively. No recent campaign stories are invented to fill the groups.

LaHood's advertised RSS contains malformed publication dates such as day 280 of October; those dates are rejected rather than repaired. The separate official news listing provides valid dates, so the configured collector uses that listing. HTML publication dates are stored with `date_precision: day`; a time or timezone is not fabricated.

## Operation and review

`communications.collect` fetches the first page/feed only, once per configured active source. It allows at most 16 sources, one MB per response, 25 seconds per request and fixed-host HTTPS redirects. It does not follow article links or pagination. RSS entities/DTDs are rejected; links must stay on the reviewed publisher's host. Missing links/dates and partially changed HTML structures produce incomplete health and retain earlier dated metadata within the age window. Retained items are labeled. Successful empty feeds, known link-only sources and failed requests are distinct states.

Only bounded titles, article links, dates, provenance and source receipts persist in `data/communications-state.json`; selected items and source coverage are copied into the browser snapshot. No raw HTML/RSS, article bodies, contact addresses or private correspondence are committed. The browser artifact budget is 650 KB to accommodate bounded source coverage and the additional item groups; the overall public JSON data guard stays 20 MB.

The existing daily `media prepare` phase collects first-party metadata; `media execute` applies it along with the existing news decisions. The separate manual command `python -m civic_tracker.media refresh-communications` collects/applies only public communications and adds search transparency to the snapshot. It does not call the model or alter inference cache, cost ledger, work manifest or model report. The existing `media.yml` manual workflow accepts `mode=communications`; the model step is skipped and its key is not exposed to the collector. The source lock and publication SHA checks are unchanged.

For review start with this file, `config/communications.json`, `src/civic_tracker/communications.py`, `tests/test_communications.py`, then a member's `communications` and `communication_sources` arrays in `data/dashboard.json`. Coverage receipts expose source type, last check, latest listing date and unsupported feeds. Missing results are not proof of inactivity.

### P03 failure diagnostics

Failed first-party sources retain their last-good items and record only a safe
category and code: `http` with `HTTP_NNN`, `timeout` with `TIMEOUT`, `tls` with
`TLS_ERROR`, `transport` with `TRANSPORT_ERROR`, or `parse` with `PARSE_ERROR`.
Provider exception text, response bodies, headers and URLs are never persisted.
A failed source is not converted into an empty successful feed; its dated receipt
remains marked failed. The mapping is covered offline before any bounded hosted
communications check.

## Hosted acceptance

The [communications-only hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39048939298) completed and deployed October 17. All 11 automated sources were healthy; four sources were explicitly link-only. Each member displayed three office posts. Campaign and party groups had no eligible recent items at that October 17 check; this dated observation is superseded by later source receipts and the House blog addition below. No publication date or release was invented to fill them.

Both local and hosted checksum checks confirmed unchanged inference records; the model step was skipped and this refresh made zero model calls. All 137 offline tests and the privacy scan passed. Independent review identified missing-link and partial-date handling issues; targeted regressions now reject source/listing links as article substitutes, count missing HTML metadata, and retain earlier dated items under incomplete health.

The live browser confirmed five exact-query panels with working search/RSS/publisher-policy links and five separate communications sections. Fritts' expanded methodology and office releases were visually checked. Compact results: [communications-validation.json](evidence/communications-validation.json).

## October 20 House caucus source update

The owner supplied The Caucus Blog and Fritts latest-news links. Fritts latest
news was already collected as `fritts-office` using its dated HTML listing.
The existing `il-house-gop` entry now collects the blog's advertised HTTPS RSS
(`feeds/posts/default?alt=rss`) and links coverage to the blog homepage. Its
footer identifies the publisher as the Illinois House Republican Caucus. Posts
appear under Fritts **Party / caucus**, with no member-name requirement for this
explicit caucus-wide source, separately from his **Member office** and newsroom
reports. This does not imply personal authorship, agreement or campaign origin.

No parser, model task, spending allowance, retention limit, email delivery or
schedule is added. Source count remains fifteen (twelve automated, three
link-only), below the existing sixteen-source cap. The existing daily
communications phase refreshes both supplied sites. First collection of this
previously link-only publisher establishes a quiet shared-feed baseline; old
posts can appear in the browser without being represented as new actions today.

The [source-update receipt](evidence/house-caucus-source.json) separates local
source/parser verification from the hosted communications-only refresh.

The October 20 communications-only hosted refresh collected all 25 blog feed
entries without rejection (11 within 90 days) and published its three newest
items under Fritts. The shared ledger stored eleven quiet initial facts and
created no baseline alerts. Browser checks confirmed the separate office and
caucus groups, publisher labels and caucus-wide qualification. Inference was
skipped and all four model/work/financial files remained byte-identical.

The refresh job succeeded but not all publishers were reachable: Fritts office,
Arellano office, Durbin office, Duckworth office and Senate Democratic Caucus
checks failed; their last verified dated metadata was retained and labeled.
Fritts HTML listing parsed successfully locally, so its hosted failure is not
a demonstrated parser regression. The scheduled daily phase will recheck within
existing bounds; this source addition does not claim those sources healthy.
