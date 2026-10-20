# Paginated 200-day member news

October 20, 2026 owner-requested follow-up. Member bill-history pages now show
five screened articles in their news column. **Older coverage**, **Newer coverage**,
**Newest coverage** and **Oldest available coverage** lead to independently
paginated news pages, `member-<id>-news.html` and `member-<id>-news-2.html`, etc.
**Browse all screened reports** opens the news browser; **Member bill activity**
returns to the bill page. News pagination does not multiply every bill-page/news-
page combination. All pages and links work without JavaScript. Homepage news
remains three reports within 90 days; member news uses 200 days.

## Collection and validation

The five existing Google News queries, 150-entry feed bound and 30 eligible
candidates per member are unchanged. `media.prepare` no longer stops at three
accepted results: it walks the bounded candidate pool and queues at most four
unseen/reconsiderable cases per member. The existing inference engine still
enforces 20 candidates per run, four media requests per Chicago day, USD 0.02/day,
USD 0.20/week and USD 20 lifetime, including earlier liabilities. Prompt, model,
provider, cache identities and one-attempt ownership are unchanged. Invalid,
uncertain and quarantined cases are not automatically retried.

`news_archive.py` adds `data/media-history.json`, a small rolling display cache
of up to 100 accepted reports per member. It stores public metadata and the short
RSS snippet needed to recheck the exact screening case; no article body is read.
Every retained/displayed row must pass member/name, derived article ID, public
URL/publisher, 200-day date bounds and an exact valid positive cache decision.
Wrong-member, expired, future, unscreened, negative and malformed records are
withheld. Rows sort by publication date, newest first, and duplicate URLs or
normalized headlines are suppressed. Source-check dates remain distinct from
publication dates. A failed feed check cannot refresh retained evidence dates.
Changing a cached decision to false also removes the article from this display.

`media.apply` updates the rolling cache and keeps the existing small homepage
snapshot. Its health report now considers the entire bounded candidate pool;
pending and withheld counts are visible, even after three positive results.
The member renderer rechecks cache decisions independently of a stored label.
The cache proves a relevance decision, not the truth of an article or its date.
Publisher attribution and the expandable search methodology remain visible.

## Storage and operation

The rolling display cache is capped at 1,000,000 bytes inside the existing
20,000,000-byte working-JSON ceiling. Older-than-200-day and beyond-100 entries
leave this display cache; permanent legislative history, referenced evidence,
screening receipts and financial ledgers are not deleted. Rendering writes only
allowlisted static files. At most 20 news pages per member are possible (five
reports per page). Member/news HTML stays within its existing 3,000,000-byte cap;
the base artifact retains 650,000 bytes, or 3,650,000 combined. Size failures
stop publication instead of silently emitting a partial artifact. The original
archive and all bill-pagination identities remain intact.

The existing daily media phase updates these records at 01:00 Central. The
existing media-only workflow can perform an owner-authorized refresh, preserving
reservations before model execution. Building/browsing never calls a model or
API. No new schedules, paid service, PDF task or outreach is enabled.

This is not a comprehensive 200-day news archive. Feed/indexing limits, candidate
bounds, publisher policy, pending screening and the 100-report rolling limit may
omit reports. Sparse results are not padded. Screening older candidates proceeds
gradually within the unchanged budget, and one refresh need not clear a backlog.

## Review entry points

Read `news_archive.py`, the small `media.py` queue/retention changes,
`member_history.py` news navigation, and `dashboard.media_section`'s bounded
limit/offset rendering. Tests in `test_news_archive.py` cover 12 reports across
three pages without duplicate/lost rows, wrong-member/cache/URL withholding,
expiry, retained source dates, invalidated decisions, the rolling/byte limits
and unchanged financial history. The media queue regression proves collection
continues past three positives while retaining its four-candidate bound.
See the [completion receipt](evidence/news-pagination.json). No upstream source
code was newly copied; existing third-party notices remain applicable.
