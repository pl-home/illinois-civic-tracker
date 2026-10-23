# P06 service and session rollover review

Review date: 2026-10-23 (America/Chicago). This is a review receipt, not an
identity migration. No collector, schedule, record, or member ID was changed.

## Verified current service facts

| Scope | Current service identity | Evidence and boundary |
| --- | --- | --- |
| Illinois | GA104, `ga=104`, ILGA `GAID=18`, `SessionID=114`, 2025–2026 | The official ILGA home page and member/schedule pages identify the current General Assembly as the 104th. The member IDs in configuration are Fritts `3428` and Arellano `3383`. |
| Federal | Congress119, current vote session `2` | The federal collector uses Congress119 and official House Clerk/Senate LIS sources. The tracked IDs are LaHood `L000585`, Durbin `D000563`, and Duckworth `D000622`. |
| Guard | Review before `2027-01-03` | `daily.gate_decision()` and `daily.run()` return `session-review-required` on or after the guard date. This prevents a stale session from being silently presented as current. |

The official references used for this review are [ILGA](https://ilga.gov/),
[ILGA House members](https://www.ilga.gov/House/Members/List), [ILGA general
assemblies](https://my.ilga.gov/ga), [Congress.gov](https://www.congress.gov/),
[House Clerk member records](https://clerk.house.gov/members/L000585), and the
[Senate roll-call index](https://www.senate.gov/legislative/LIS/roll_call_lists/).
They establish current source shape and current service context; they do not
establish successor member IDs.

## Migration matrix

| Area | Current dependency | Required successor review | Status |
| --- | --- | --- | --- |
| ILGA FTP XML | `config/project.json:ga`; `daily_state.py`, `dashboard_collect.py`, `change_sources.py`, verification tools | Confirm the official GA number, FTP listing, XML filename pattern, and `GAID`/`SessionID` URL parameters. Add before/after fixtures and retain GA104 history. | Pending official GA105 evidence |
| ILGA floor CSV | `104MemberVotes.csv`; `floor_csv_baseline_through` | Confirm the new export path/schema and overlap window. Do not reset the watermark or treat old rows as new activity. | Pending |
| ILGA member pages | IDs `3428`, `3383`; member-page URL allowlist | Reconfirm each member’s chamber, district, official ID, and service dates from the new roster. A missing page or changed ID is a review failure, not a removal. | Pending |
| ILGA committee/hearing parsers | `hearings.py`, `dashboard_sources.py`, `hearing_changes.py`; GA104 URL and title guards | Confirm new heading/session text, committee IDs, hearing URL shape, role rosters, agendas and witness-form behavior. Preserve outgoing hearing records. | Pending |
| ILGA historical PDF fixtures | `pdf_extract.py`, roll-call evaluation configs and fixtures | Keep GA104 evidence immutable. A future PDF path/schema requires a separately reviewed extraction task. | Deferred; no migration attempted |
| Federal legislation | `daily_federal.CONGRESS=119`, Congress.gov bill URLs and member lists | Confirm Congress120 API rows, member IDs, bill URL shape, and service dates. Keep Congress119 bills and relationships as history. | Pending official successor records |
| Federal floor votes | House Clerk and Senate LIS URLs use Congress119/session2 | Confirm Congress120 session numbering and both chamber indexes before fetching. Require contiguous index checks and new fixtures. | Pending |
| Federal committees | `config/dashboard.json` assignments reviewed 2026-10-17 | Recheck committee rosters, chair/ranking roles, and source URLs after the new Congress is constituted. Do not infer continuity from current assignments. | Pending |
| Daily guard and workflow | `config/daily.json:review_before`; daily tests and workflow | Keep the guard until a reviewed migration commit replaces it. The date is a safety stop, not proof that either legislature changes service on that exact date. | Verified safety behavior |

## Required before/after acceptance

1. Capture official roster/service evidence for every tracked member and
   committee assignment, with observation date and source URL.
2. Add synthetic before/after fixtures proving GA104 and Congress119 history is
   retained while successor records use new identities.
3. Validate every URL builder and allowlist against both old and successor
   shapes, including bill, vote, hearing, committee, and member URLs.
4. Run correction, deduplication, stale-source retention, and session-mismatch
   tests. A missing successor source must leave the prior verified record and
   produce a visible partial/error result.
5. Review the resulting migration packet independently before changing IDs,
   session constants, URL guards, or the January safety stop.

## Result

P06 is complete as a review/report. No successor identities are verified, so no
implementation change is authorized. P04 remains source-dependent; email and
PDF work remain deferred. The next action is a separately reviewed migration
packet after official GA105/Congress120 service evidence exists.
