# News discovery and direct communications

Owner update, October 17, 2026: make news discovery visible and display campaign releases and direct office/party communications in their own section. This enables deterministic public first-party collection alongside the existing daily news phase. It does not enable the legacy AI party classifier, automatic outreach, Facebook scraping, private email access or a new local schedule.

## How news is found

Each member card now has **How we find news about [member]**, with the exact Google News search, an ordinary search link, the RSS URL actually used, candidate count and publisher policy link.

| Member | Exact query |
| --- | --- |
| Bradley Fritts | `"Bradley Fritts" OR "Brad Fritts" when:90d` |
| Li Arellano, Jr. | `"Li Arellano" when:90d` |
| Darin LaHood | `"Darin LaHood" when:90d` |
| Dick Durbin | `"Dick Durbin" when:90d` |
| Tammy Duckworth | `"Tammy Duckworth" when:90d` |

The collector reads up to 150 RSS items, checks publication dates, requires a reviewed newsroom host and a name anchor in the headline/snippet, excludes explicit opinion/editorial titles, deduplicates normalized headlines and retains at most 30 candidates per member. Qwen's bounded relevance decisions select from these IDs; it does not discover stories, change their dates, generate their titles, verify their contents or rank them by importance. Date sorting determines display order. Up to four not-yet-screened candidates per member are considered per run within the shared daily limits. [MEDIA_REPORTS.md](MEDIA_REPORTS.md) describes cache, uncertainty and spending controls.

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
| Senate Democratic Caucus press releases | Dated public HTML listing; name match required |
| Lee County Democrats, `leecodemocrats.com/feed/` | Advertised RSS; name match required |
| Lee County GOP, `leecountyilgop.org/feed/` | Advertised RSS; name match required |

The exact verified HTTPS URLs, per-member source mappings and notes are in [config/communications.json](../config/communications.json). Shared party feeds must name the member in their headline or bounded excerpt; a general party announcement is not assigned to every party member. This is a member-communications view, not a replacement for broader monitoring of party websites.

Four source links are **link-only**: Arellano's older campaign site, the Durbin and Duckworth campaign sites without verified dated feeds, and the Illinois House GOP site whose public homepage returned HTTP 403 in the setup check. They are visible in source coverage and are not represented as automatically collected. Fritts' and LaHood's campaign feeds are active collection sources but their latest posts observed during setup were July 15, 2025 and November 5, 2024 respectively. No recent campaign stories are invented to fill the groups.

LaHood's advertised RSS contains malformed publication dates such as day 280 of October; those dates are rejected rather than repaired. The separate official news listing provides valid dates, so the configured collector uses that listing. HTML publication dates are stored with `date_precision: day`; a time or timezone is not fabricated.

## Operation and review

`communications.collect` fetches the first page/feed only, once per configured active source. It allows at most 16 sources, one MB per response, 25 seconds per request and fixed-host HTTPS redirects. It does not follow article links or pagination. RSS entities/DTDs are rejected; links must stay on the reviewed publisher's host. Missing links/dates and partially changed HTML structures produce incomplete health and retain earlier dated metadata within the age window. Retained items are labeled. Successful empty feeds, known link-only sources and failed requests are distinct states.

Only bounded titles, article links, dates, provenance and source receipts persist in `data/communications-state.json`; selected items and source coverage are copied into the browser snapshot. No raw HTML/RSS, article bodies, contact addresses or private correspondence are committed. The browser artifact budget is 650 KB to accommodate bounded source coverage and the additional item groups; the overall public JSON data guard stays 20 MB.

The existing daily `media prepare` phase collects first-party metadata; `media execute` applies it along with the existing news decisions. The separate manual command `python -m civic_tracker.media refresh-communications` collects/applies only public communications and adds search transparency to the snapshot. It does not call the model or alter inference cache, cost ledger, work manifest or model report. The existing `media.yml` manual workflow accepts `mode=communications`; the model step is skipped and its key is not exposed to the collector. The source lock and publication SHA checks are unchanged.

For review start with this file, `config/communications.json`, `src/civic_tracker/communications.py`, `tests/test_communications.py`, then a member's `communications` and `communication_sources` arrays in `data/dashboard.json`. Coverage receipts expose source type, last check, latest listing date and unsupported feeds. Missing results are not proof of inactivity.

## Hosted acceptance

The [communications-only hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39048939298) completed and deployed October 17. All 11 automated sources were healthy; four sources were explicitly link-only. Each member displayed three office posts. Campaign and party groups had no eligible recent items in this bounded check and remain visibly empty with source coverage explanations. No publication date or release was invented to fill them.

Both local and hosted checksum checks confirmed unchanged inference records; the model step was skipped and this refresh made zero model calls. All 137 offline tests and the privacy scan passed. Independent review identified missing-link and partial-date handling issues; targeted regressions now reject source/listing links as article substitutes, count missing HTML metadata, and retain earlier dated items under incomplete health.

The live browser confirmed five exact-query panels with working search/RSS/publisher-policy links and five separate communications sections. Fritts' expanded methodology and office releases were visually checked. Compact results: [communications-validation.json](evidence/communications-validation.json).
