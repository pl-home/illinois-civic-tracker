# Legislator & County Party Tracker — Product Vision

**Latest October 17 scope update:** the owner authorized recent media reports for all five members and narrow routine Qwen3 32B / DeepInfra relevance screening, with USD 0.009 daily liability and USD 20 lifetime limits. [MEDIA_REPORTS.md](MEDIA_REPORTS.md) describes operation and evidence limits. Older statements excluding routine inference are superseded only for this task; party and legislative inference remain disabled.


**October 17 daily website scope update:** the owner explicitly authorized daily public website refresh at **01:00 America/Chicago**, superseding its previous 23:00 target and manual-only status. This staged source-refresh release does not declare unresolved M0/M1 checks passed or enable the weekly digest/inference. Read [DAILY_REFRESH.md](DAILY_REFRESH.md) for source coverage, retained failures, initial hosted verification and remaining gates. Earlier status statements below are dated evidence.


Rev. 3, October 16, 2026. This consolidates rev. 1–2 and the decisions made on October 16. It replaces the outcome sections of `docs/PRODUCT_SPEC.md`; that spec's evidence rules still apply. **Open** marks items that still need a decision. The companion `BUILD_BRIEF_M0_M1.md` says what to build first.

This document is written to live in a **public** repository. It names no personal email addresses, credentials or local paths, and it must stay that way (§13).

**October 17 scope update:** the owner brought a basic read-only browsing page forward into the first release. The initial historical preview may publish separately from the gated M1 collector/digest. Search, measure-type filters, explicit coverage and a show-ceremonial view are included; full-tenure and topic pages remain M5. See [BROWSING_PAGE.md](BROWSING_PAGE.md). OpenRouter setup may be prepared, with inference still disabled pending later activation.

---

## 1. Purpose

The tracker answers four questions for its owner, a Lee County, Illinois constituent:

1. What have my legislators done, recently and over their tenure, on the topics I care about?
2. What is coming up in Springfield that I can still weigh in on?
3. What are the Lee County Democrats and Lee County Republicans doing locally?
4. What is Capitol Fax saying about the people and organizations I follow?

**Collection is automatic. Only a small set of things rises to the owner's attention** (§4). Everything else is stored quietly and is searchable.

**Use free tools first; build only the gaps.** Where a free official tool already does the job, the tracker doesn't duplicate it.

| Need | Covered by | Tracker builds |
|---|---|---|
| Federal sponsorship and cosponsorship | Congress.gov member alerts (**set up** for LaHood, Durbin, Duckworth) | Nothing |
| Federal bills on topics | Congress.gov saved-search alerts by policy area (optional; owner sets up) | Nothing for now |
| Federal votes | Gap: Congress.gov doesn't alert on votes; Senate votes are only on Senate.gov | Later milestone |
| Duckworth's committee activity | Partly: Congress.gov committee-profile and committee-schedule alerts | Later milestone (§11) |
| Illinois sponsorship, actions, votes, hearings | Data is free (§5), but no free tool alerts on it | **Core of the build** |
| Witness-slip details | The owner's ILGA account profile stores them | Hearing list with slip links only |
| County parties | Nothing | Existing website collector |
| Capitol Fax mentions | The owner reads it daily; no alerts exist | Per-name feed alerts |
| Other media | Google Alerts (owner) | Nothing |

---

## 2. Subjects

| Subject | Office | Notes |
|---|---|---|
| Bradley Fritts | IL House, District 74 | |
| Li Arellano, Jr. | IL Senate, District 37 | |
| Darin LaHood | U.S. House, IL-16 | Federal; mostly covered by Congress.gov alerts |
| Dick Durbin | U.S. Senate | Not seeking reelection; the seat changes in January 2027 |
| Tammy Duckworth | U.S. Senate | Committee watch (§11) |
| Lee County Democrats | County party | Websites only |
| Lee County IL Republicans | County party | Websites only |

**Illinois committee assignments** (ILGA Member's Committee Listing, Oct 16, 2026):
- **Fritts:** Approp-Pensions & Personnel; Energy & Environment; Judiciary–Civil; Labor & Commerce (Minority & Women Business Sub); Trans: Regulation, Roads & Bridges; Transportation: Vehicles & Safety.
- **Arellano:** Approp-Health and Human; Health and Human Services; Public Health (Minority Spokesperson); State Government; Local Government; Pensions; Veterans Affairs.

**Duckworth committee assignments (119th Congress):**
- **Armed Services:** Airland; Personnel; Readiness and Management Support.
- **Commerce, Science, and Transportation:** Aviation, Space, and Innovation (**Ranking**); Surface Transportation, Freight, Pipelines, and Safety; Telecommunications and Media.
- **Foreign Relations:** Europe and Regional Security Cooperation; Multilateral International Development, Multilateral Institutions, and International Economic, Energy, and Environmental Policy (**Ranking**); State Department and USAID Management, International Operations, and Bilateral International Development.
- **Veterans' Affairs.**

Subjects, sessions, service periods and committee assignments are **configuration, not code**. Two rollovers arrive in January 2027: the 104th → 105th General Assembly and the 119th → 120th Congress. When a person leaves office, their history stays and new collection stops.

---

## 3. Principles

1. **Official sources establish facts.** ILGA, Congress.gov, the House Clerk and Senate.gov are authoritative. Open States, LegiScan, news and party sites are cross-checks or attributed statements.
2. **Index everything; detail what matters; store full text almost never** (§6).
3. **Permalinks over copies.** Every item carries a stable official link, so it can be looked up later by the owner or an AI assistant.
4. **Filter noise without hiding it.** Ceremonial items are indexed and countable but never shown by default, and the reason is visible.
5. **Never infer the owner's position.** Topics decide relevance. Only the owner's explicit choices, kept privately, record a stance.
6. **Nothing is filed or sent to legislators automatically.** The only automatic email is the digest, sent to the owner.
7. **Treat both county parties the same way:** same collection, extraction and presentation, with statements attributed to the party.
8. **No frontier AI in routine operation.** Milestone 1 uses no AI at all. Later, an open-weight model may serve as a fallback for topic tagging (§7).

---

## 4. What reaches the owner

| Channel | When | Contents |
|---|---|---|
| **Weekly digest email** | **Mondays 6:00 a.m. Central** | See below |
| **Immediate alert** | During session only (**milestone 2**) | A shell bill involving a subject, or rewritten into one of the owner's topics |
| **Stored quietly** | Always | Ceremonial items, unopposed votes, routine actions, everything outside the topics. Never emailed; available on the site |

**Weekly digest sections, in order:**
1. **Can still weigh in:** Illinois bills on the owner's topics posted for a committee hearing in the next ~10 days, with hearing date and time, slip link and synopsis line.
2. **Shell bills that changed** (milestone 2).
3. **Your legislators this week, by topic:** introductions, role changes, and votes on roll calls with at least one nay. Each item shows the member's choice, the motion, the date, why it was included, and the official link.
4. **County parties:** events, meeting notices, leadership or contact changes, candidate or endorsement posts.
5. **Capitol Fax mentions:** new posts naming a subject.
6. **Health footer:** sources that failed, changed format or went stale this week.

A quiet week produces a short email that says what was checked. The digest is factual and stance-free.

**Delivery:** the owner's Gmail account sends to itself, at a "+" address the owner chooses so mail filters can label it. Both addresses are GitHub secrets (§13).

---

## 5. Data sources and collection

All automated Illinois collection runs **nightly at 23:00 Central**.

| Source | What it provides | Access rule |
|---|---|---|
| **ftp.ilga.gov** `/Legislation/104/BillStatus/XML/` | Per-bill status XML: filing, dated sponsor and action history, synopsis, vote tallies in the action text | **Primary.** ILGA's robots.txt names this repository as the route for automated and bulk retrieval. No crawl-delay applies on this host. Fetch only files that changed. |
| ftp.ilga.gov `/Members/`, `/Committees/` | Member roster and contacts; committee membership and roles | Nightly; snapshot and diff |
| **`ilga.gov/documents/reports/static/104MemberVotes.csv`** | Every member's **floor** vote for the General Assembly: 261,928 rows and 2,843 roll calls through 2026-05-31. Columns: GA, Member, Chamber, Session, Legislation, Vote Type, Vote Date, Vote | **Confirmed public** (opens without login). One conditional request per night. Compute nay counts per roll call from the full file, then keep only the subjects' rows. |
| `ilga.gov/documents/reports/static/` PDFs | `Legislation in Committee-House/Senate.pdf` (bills posted for hearing); `Sponsor Bill Listing By Name-House/Senate.pdf`; `Bills Amended By Sponsor.pdf` | Main site: **≥10 s between requests, sequential**. Parse reliability to be verified (M0). |
| ilga.gov roll-call PDFs | Individual **committee** votes (not in the CSV) | Only for committee votes in the subjects' committees, on bills that matter. ≥10 s apart. |
| Open States API | Cross-check and fallback | Key held privately; GitHub secret |
| Party websites (existing collector) | Pages, events, precinct rows | Existing bounded page list |
| Capitol Fax search feeds `capitolfax.com/?s=<name>&feed=rss2` | Posts mentioning each subject, plus "Lee County" | Daily. Drop titles starting "Protected:". Store title, link and date only. |

**ILGA robots.txt (read Oct 16, 2026):**
- Disallows only `/account`, `/admin`, `/search` and `/api`.
- Sets `Crawl-delay: 10` for ilga.gov.
- Points automated systems to ftp.ilga.gov.
- Explicitly permits personal use by a constituent, even with automated tools.

Rules for the job:
- Use the ftp repository for everything it carries.
- Requests to the main site run one at a time, at least 10 seconds apart; the one-time backfill uses 20 seconds.
- Don't automate logged-in pages.
- The public site goes beyond strictly personal use, so stay inside ILGA's stated preferences.

**Backfill:** build the index from the existing tracker's 104th General Assembly archive instead of re-downloading it. Back-collect the 103rd only if a subject served in it (M0 check).

---

## 6. Data tiers and noise

| Tier | What | Kept | Contents |
|---|---|---|---|
| **A — Index** | Every bill, resolution and floor vote involving a subject, over their full tenure | Permanently (small) | ID, date, type, short description, member role or vote, nay count, flags, topic tags, official permalink |
| **B — Detail** | Items on a topic, pinned, split votes, shell bills, role changes | Permanently, compact | Synopsis, action history, statute references, amendment info, inclusion reason |
| **C — Evidence** | Items the owner acted on; unresolved source conflicts | Until no longer referenced | Saved copy or Wayback link plus hash |

There is no full bill text, and no vote-PDF text dumps.

**Noise rules** (tested Oct 16 against the owner's 134-item Fritts sponsorship export):
- **Ceremonial**, flagged by the official short description: starts with `CONGRATS-` or `MEMORIAL-`; contains `MEM'L`; ends with `MONTH`, `DAY`, `WEEK`, `HWY`, `HGWY` or `NAME`; or matches `READING ROOM`. This flagged 24 of 134 items (with `MEM'L` added), 10 of them Fritts's own resolutions. Index only; hidden by default.
- **Do not drop resolutions wholesale.** The rule above correctly leaves position statements visible, such as "No taxes on retirement income," "Condemns Gov. JB Pritzker," "Support Israel," "Condemns political violence," and task-force joint resolutions.
- **Unopposed votes** (zero nays on the roll call; 64% of roll calls in the 104th): index only, shown as "no recorded opposition."
- **Procedural and appointment votes** (`MOTION IN WRITING`, `EXECUTIVE APPOINTMENTS`): index only unless split and on a topic.
- **Never noise:** shell bills, appropriations, split votes on a topic.

Every hidden item records why it was hidden. A "show hidden" view exists for auditing the filter.

---

## 7. Topics

**Topics:** immigration, **energy policy**, pensions, law enforcement, housing, **civil liberties**.

Tagging uses **official structure first**: the committee a bill is assigned to and the statute chapters it amends. A keyword list is a secondary signal. An open-weight model is a later fallback for untagged items. Items can carry several topics.

| Topic | Illinois committees | Illinois statutes (ILCS) | Federal policy area (CRS) |
|---|---|---|---|
| Immigration | (H) Immigration & Human Rights | No dedicated chapter; committee and keywords | Immigration |
| Energy policy | (H) Energy & Environment; (H) Public Utilities; (S) Energy and Public Utilities; (S) Environment and Conservation | 220 Utilities; 20 ILCS 3855 (Illinois Power Agency Act); 415 Environmental Safety | Energy |
| Pensions | (H) Personnel & Pensions; (H) Approp-Pensions & Personnel; (S) Pensions | 40 Pensions | None of its own; filed under Labor and Employment, Social Welfare or Taxation. Needs subject terms. |
| Law enforcement | (H) Police & Fire; (H) Judiciary–Criminal; (H) Restorative Justice & Public Safety; (S) Criminal Law | 720 / 725 / 730 Criminal; 430 Public Safety; 50 Local Government (police acts) | Crime and Law Enforcement |
| Housing | (H) Housing | 310 Housing; 765 Property (landlord–tenant) | Housing and Community Development |
| Civil liberties | (S) Judiciary; (H) Judiciary–Civil; (S) Human Rights; (H) Cybersecurity, Data Analytics, & IT; (H) Ethics & Elections | 5 ILCS 140 (FOIA); 5 ILCS 120 (Open Meetings Act); 740 ILCS 14 (Biometric Information Privacy Act); 775 Human Rights; 10 Elections; 725 Criminal Procedure; 430 ILCS 65 (FOID) | Civil Rights and Liberties, Minority Issues |

**Open:**
- Confirm the civil-liberties scope. Proposed: privacy and surveillance; speech and assembly; open government (FOIA and Open Meetings); due process; voting and elections; firearms rights and regulation; religious liberty. These are subject areas only, with no assumed position. Firearms and criminal procedure overlap with law enforcement; tagging both is fine.
- Confirm the energy-policy scope. Proposed: generation, utilities and rates, power procurement, clean-energy law, and large-load siting such as data centers.
- Whether ILGA updates a bill's statute listing after an amendment rewrites it is untested (M0).

**Pinned bills or issues:** none yet; configuration supports a list.

---

## 8. Shell bills (milestone 2)

**October 17 clarification:** replacement boilerplate triggers a content comparison; it does not establish an unrelated rewrite. The future website synopsis must follow the adopted/operative version, distinguish meaningful same-subject revisions from subject changes, and support an insufficient-evidence result. SB2427 is the owner's continuity/false-positive example. Read [amendment inference requirements](AMENDMENT_INFERENCE_REQUIREMENTS.md). This deferred use of inference remains disabled.

Leadership routinely files placeholder ("vehicle") bills, then rewrites them by amendment. The owner's own sponsorship export shows two that became law with their placeholder titles unchanged: HB0742 "REGULATION-TECH" (Public Act 104-0004) and HB2137 "LOCAL GOVERNMENT-TECH" (Public Act 104-0582).

**Detection:**
- The short description ends in `-TECH` or starts with `$`, or the synopsis says it "makes a technical change."
- Then an amendment is filed or adopted, especially one whose synopsis begins "Replaces everything after the enacting clause."
- Watch for bills parked on second reading that receive late amendments.

**Handling:**
- Every shell bill involving a subject gets a Tier B record.
- On an amendment, re-tag topics from the amendment, not the title.
- If the bill is now on a topic, include it in digest section 2. During session, also send the immediate alert. Amendments can move on one hour's posting notice.
- Witness slips stay tied to the original bill number, so show where the language went.

Milestone 1 sets the shell **flag** only; detecting rewrites and alerting is milestone 2.

---

## 9. Hearings and witness slips

- From the static "Legislation in Committee" reports and hearing schedules, list bills posted for hearing in topic committees, or on a topic by statute.
- Each entry shows the hearing date and time and links to that bill's witness-slip page.
- The owner's ILGA account stores the details slips ask for. **The tracker never submits slips.**
- Filed slips appear publicly on the bill's Witness Slip tab.
- Most activity runs January–May; this must work before the 105th General Assembly's spring committee hearings.

---

## 10. County parties

Reuse the existing website collector: page list, change detection and precinct-row parsing.

Extract into structured items:
- events (date, time, venue, cost, contact);
- meeting notices;
- officer and contact changes;
- candidates and endorsements;
- position statements, attributed to the party.

Cosmetic edits are suppressed. Facebook isn't collected; the coverage gap is stated on the page.

---

## 11. Federal (later milestones)

- **Sponsorship:** Congress.gov alerts (owner-managed). No build.
- **Votes:** House roll-call XML from the Clerk and Senate roll-call XML from Senate.gov. Include in the digest only split votes on topics.
- **Duckworth committee watch:** hearings and markups from her committees, with subcommittees where she is ranking member first. Her participation comes from her press releases (attributed) and hearing video or transcripts. Measures referred and reported come through Congress.gov committee alerts, filtered to topics or her own bills. Routine military promotions and ambassador nominations are index-only. Committee roll calls are shown only where published; absence is stated, not inferred.
- **Open:** extend the committee watch to LaHood and Durbin (decide later).

---

## 12. Contact packets (later milestone)

Around March and September, build a packet per legislator with:
- what they did on the owner's topics since the last packet;
- the official contact route (Illinois district office or contact form; U.S. Senate web forms);
- a draft built only from the owner's explicit positions.

Draft and sent are separate states. Packets live privately in Obsidian, never in the repo.

---

## 13. Public vs. private, and secrets hygiene

| Public (repo and site) | Private (never in the repo) |
|---|---|
| Official records index and detail | The owner's positions, drafts, contact log, slip log, notes (Obsidian) |
| Topic tags and inclusion reasons | **The owner's email addresses** (sender and "+" recipient): GitHub secrets |
| Hearing list and slip links | Gmail app password, Open States key, LegiScan key: GitHub secrets |
| County party items (attributed) | Local machine paths, usernames, runtime locations |
| Capitol Fax titles and links | Anything copied from the existing vault without review |

**Required safeguards:**
- **A fresh repository.** Don't push the existing vault or tracker folder. It contains local Windows paths, usernames and references to private credential notes.
- **Commit identity:** the owner enables GitHub's "Keep my email addresses private" and "Block command line pushes that expose my email" settings, and every local tool that commits (Codex included) uses the GitHub `noreply` address. Workflow commits use the Actions bot identity.
- **GitHub secret scanning with push protection** enabled.
- **A CI check that fails the build** if any committed file contains an email address other than an allowlisted `noreply` form, a Windows user-profile path, or something shaped like a key or token. The check must not itself contain the owner's address.
- **Sent emails** carry no secrets. The digest's From/To headers come from secrets at send time and are never logged.

---

## 14. Architecture

- **Runner:** GitHub Actions in a public repository; standard runners are free for public repos.
- **Schedules** (GitHub cron is UTC-only):
  - Nightly collection at 23:00 Central = 04:00 UTC (daylight time) or 05:00 UTC (winter).
  - Digest Mondays 06:00 Central = 11:00 UTC or 12:00 UTC.
  - Schedule both UTC times and have the job check the `America/Chicago` local hour, exiting if it isn't the target hour.
  - A ledger ensures each digest sends exactly once, even if a run is delayed or repeated.
- **Inactivity:** GitHub disables scheduled workflows in a public repo after 60 days with no repository activity. Nightly data commits likely count, but GitHub doesn't define "activity," so the owner should notice if a Monday digest fails to arrive; the digest's absence is the heartbeat.
- **State:** the compact index (JSON or CSV) and the seen-items and sent-digest ledgers are committed to the repo, on a `data` branch if that keeps history cleaner. No PDFs, ZIPs, raw HTML or the full vote CSV are committed; only the subjects' rows and the computed nay counts.
- **Repository size:** target ≤ 100 MB; hard limit 400 MB. Report growth in the health footer.
- **Site:** a basic static browser on GitHub Pages is brought forward into the first release; full-tenure and topic pages remain a later milestone.
- **Email:** Gmail SMTP (`smtp.gmail.com`, STARTTLS, port 587) with an app password, which requires 2-Step Verification on the account. Verify in M0 that self-sent mail to a "+" address lands in the inbox, not only in Sent.
- **AI:** none in milestone 1. Later, an optional open-weight model via API tags otherwise untagged items, with its output labeled as machine-generated. Frontier models are used for building and for owner-initiated analysis only.

---

## 15. The current build: keep, change, retire

| Keep | Change | Retire |
|---|---|---|
| Official ILGA, Congress.gov, Clerk and Senate parsers | Codex scheduling and Windows Task Scheduler → GitHub Actions | Floor-vote PDF parsing (after the CSV spot-check passes) |
| Vote reconciliation logic, kept as a spot-audit | Hardcoded members, sessions and runtime paths → configuration | Full PDF text in vote notes |
| Party website collector, diffs, precinct parsing | Per-member field names (e.g., `fritts_vote`) → generic subject fields | Base64 duplicate of the LegiScan dataset |
| LegiScan and Open States clients (cross-check only) | Bill-status source `ilga.gov/ftp/...` → `ftp.ilga.gov` (after the M0 comparison) | Local Ollama website review (replaced by rules) |
| The existing 97 tests | 3,544 Obsidian vote notes → compact index plus generated pages | Raw-archive growth |

The existing GA104 archive is **not deleted** until the new index is built and verified against it.

---

## 16. Milestones

| # | Deliverable | Timing |
|---|---|---|
| **M0** | Verification of sources, email and runner access; findings file | First |
| **M1** | Illinois nightly collection plus the Monday digest (subjects' activity, split votes, hearings list, county parties, Capitol Fax mentions, health footer), plus basic browsing. No AI. | Before Jan 2027 |
| **M2** | Shell-bill detection and immediate in-session alerts; amendment re-tagging | Before the spring 2027 session |
| **M3** | Session rollover: 105th GA, 120th Congress, new committee assignments | January 2027 |
| **M4** | Federal votes; Duckworth committee watch | After M3 |
| **M5** | Full-tenure pages and topic pages on GitHub Pages; 103rd GA backfill if applicable | After M1 |
| **M6** | Contact packets (private) | First around March 2027 |

---

## 17. Acceptance criteria (product level)

- The digest arrives every Monday with no AI in the run, and failures appear in the health footer.
- A reviewed sample of hidden items contains no substantive legislation; a sample of shown items contains no ceremonial items.
- Every item has a working official permalink.
- Both county parties are processed identically.
- No private material appears in the repo, its history, the site or workflow logs.
- Repo size stays within budget after a simulated year of nightly runs.

---

## 18. Open questions

1. Civil-liberties and energy-policy scope (§7).
2. Pinned bills or issues.
3. Committee watch for LaHood and Durbin.
4. How often ILGA regenerates `104MemberVotes.csv` (check after the November veto session).
