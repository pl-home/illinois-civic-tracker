# P07 Illinois veto-session coverage

P07 is a deterministic 104th General Assembly improvement for the 2026 veto
session. It does not migrate GA105 identities, read PDFs, send email, or invoke a
model.

## What is now covered

- `config/veto-session.json` records the published House and Senate session days
  of November 17–19, 2026 and links to both official calendar PDFs and schedule
  pages.
- `veto_session.context()` exposes `upcoming`, `active`, `published-days-passed`,
  or `between-published-session-days` without inferring unpublished December
  dates. “Published days passed” does not mean the broader veto-session period
  has ended.
- The public homepage shows the veto-session state and links before the member
  cards. It distinguishes published session dates from daily calendars and bill
  actions.
- Illinois bill-status events receive explainable candidate labels for
  gubernatorial vetoes, gubernatorial recommendations, reduced/vetoed
  appropriations, and procedural messages/notices/resolutions.

The labels are scope markers, not conclusions about whether a measure is legally
eligible for veto-session consideration. The official bill-status source remains
the evidence; the tracker does not infer a veto or a session agenda from a title.

## Source boundaries

The official House and Senate schedule pages currently publish a November/
December veto-session heading, while the published calendars identify November
17–19 as session days. No December day is added until an official calendar or
notice identifies it. Daily hearing pages, floor-vote CSV updates, FTP bill XML,
and source-health receipts remain separate collection responsibilities.

## Validation

`tests/test_veto_session.py` covers date states, explicit no-inference behavior,
both chamber links, and narrow action labels. Existing dashboard tests verify the
public panel. No collector was run for this packet; current dashboard data and
ledgers were not rewritten.

Official references: [House schedules](https://ilga.gov/House/Schedules), [Senate
schedules](https://ilga.gov/Senate/Schedules), [House veto calendar
PDF](https://ilga.gov/Uploads/Schedules/House/House%20Calendar%20-%202026%20Veto%20Session.pdf),
and [Senate veto calendar PDF](https://www.ilga.gov/Uploads/Schedules/Senate/2026%20104th%20GA%20Veto%20Calendar.pdf).
