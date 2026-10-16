# Build Brief — Milestones 0 and 1

For: Codex (implementer). Read with `PRODUCT_VISION.md` rev. 3; section references below (§) point there.
Date: October 16, 2026.

## Goal

A **new public GitHub repository** whose scheduled workflows:
1. collect Illinois activity for Bradley Fritts and Li Arellano, Jr. every night at 23:00 Central; and
2. email the owner a factual weekly digest every Monday at 06:00 Central.

No AI in the run. No manual steps after setup.

## Ground rules (apply to every change)

1. **Start a fresh repository.** Do not push, copy wholesale or reference the existing vault or tracker folder. Port code module by module, reviewing each file for local paths, usernames, credential references and personal data.
2. **No personal data or secrets in the repo, its history, workflow logs or test fixtures.** That includes the owner's email addresses (sender and recipient), passwords, API keys, Windows paths and usernames. These come only from GitHub secrets: `GMAIL_USER`, `GMAIL_APP_PASSWORD`, `DIGEST_TO`, `OPENSTATES_API_KEY` (optional in M1), `LEGISCAN_API_KEY` (optional).
3. **Commit identity:** commit with the owner's GitHub `noreply` address only. Workflow commits use the `github-actions[bot]` identity.
4. **ILGA access rules** (§5):
   - Use ftp.ilga.gov for everything it carries; no crawl-delay applies there.
   - Requests to the main ilga.gov site run one at a time, at least 10 seconds apart; the one-time backfill uses 20 seconds.
   - No parallel requests to ilga.gov.
   - Never automate logged-in pages (`/MyLegislation`, `/account`).
   - Send a descriptive User-Agent with a project URL but no personal email.
5. **No deletion** of anything in the existing tracker archive. Read it, don't modify it.
6. **No outbound messages** other than the digest to `DIGEST_TO`. No witness slips, contact forms or mail to anyone else.
7. **Keep it small and readable.** The owner is learning, so add comments that explain non-obvious decisions and constraints. Configuration goes in YAML or JSON files, not code.

## Milestone 0 — verify before building

Write the results to `docs/M0_FINDINGS.md`. For each item give the answer, the evidence (URLs, timestamps, sample sizes), and the implication for M1. Stop and report if something blocks M1.

| # | Question | How |
|---|---|---|
| 0.1 | Is `ftp.ilga.gov/Legislation/104/BillStatus/XML/` byte-identical to the `ilga.gov/ftp/legislation/104/BillStatus/XML/` files the tracker uses now? Is there a single ZIP bundle? What does the directory listing provide for change detection (dates, sizes)? | Compare a sample of about 50 files; inspect the listings |
| 0.2 | When does ftp.ilga.gov sync each day? | Record listing timestamps several times over 2–3 days |
| 0.3 | Does a bill's statute listing in the XML update after an amendment replaces its text? | Check HB0742 and HB2137 (shell bills that became Public Acts 104-0004 and 104-0582) |
| 0.4 | Does `104MemberVotes.csv` match the tracker's PDF-verified votes? | Join Fritts's and Arellano's rows to the existing 3,544 verified vote records on bill, chamber, date and motion. Report the match rate and every mismatch. |
| 0.5 | How often is `104MemberVotes.csv` regenerated? | Record `Last-Modified` and `ETag` daily; recheck after the November 2026 veto session |
| 0.6 | Can `Legislation in Committee-House.pdf` / `-Senate.pdf` and `Sponsor Bill Listing By Name-*.pdf` be parsed reliably? | Parse them and compare against bill-status XML for 20 bills |
| 0.7 | Do the Capitol Fax search feeds (`capitolfax.com/?s=<name>&feed=rss2`) return recent matching posts for each subject and for "Lee County"? | Fetch each one and record item counts and dates |
| 0.8 | Can GitHub-hosted runners reach ftp.ilga.gov, ilga.gov, capitolfax.com and both party sites? | Run a minimal workflow that fetches one small resource from each |
| 0.9 | Does Gmail SMTP with an app password deliver a self-sent message to a "+" address into the **inbox** (not only Sent)? | Send one test from a workflow using the secrets |
| 0.10 | Did Fritts or Arellano serve in the 103rd General Assembly? | ftp.ilga.gov member XML for GA 103 |

## Milestone 1 — nightly collection and the Monday digest

### Scope

1. **Repository scaffold**
   - `config/` holds: subjects (name forms as each source spells them, chamber, district, service period); session (`ga: 104`); topics (§7 table: committees, ILCS chapters, keywords); noise rules (§6); party pages; Capitol Fax feeds.
   - `src/` holds collectors, normalizers, rules and the digest.
   - `data/` holds the compact index and ledgers.
   - `tests/`
   - `.github/workflows/`
2. **Collectors**
   - **Bill status:** ftp.ilga.gov XML. Fetch only files whose listing entry changed since the last run. Seed the initial index from the existing tracker archive (read-only) to avoid re-downloading.
   - **Floor votes:** `104MemberVotes.csv`, fetched with a conditional GET. Compute per-roll-call nay counts from the full file, then keep only the subjects' rows.
   - **Committees:** ftp.ilga.gov committee XML. Snapshot and diff the subjects' assignments.
   - **Hearings:** the static "Legislation in Committee" PDFs, if 0.6 passes; otherwise the hearing-schedule pages, at ≥10 s apart.
   - **County parties:** port the existing website collector and its page list. Keep deterministic change detection; drop the local-model review step.
   - **Capitol Fax:** search feeds per subject plus "Lee County". Skip titles beginning "Protected:".
3. **Normalize to compact records** (Tier A/B, §6). Each bill record holds:
   - ID and official permalink; short description; synopsis;
   - each subject's role, as **chief / chief co-sponsor / co-sponsor / alternate**, with the date it began;
   - last action and date; statute references; committee;
   - flags (ceremonial, shell, appropriation); topic tags plus the reason for each tag.

   Each vote record holds the subject, bill, normalized motion, raw motion text, date, raw vote value, roll-call nay count and source URL.
4. **Rules**
   - Ceremonial short-description rule exactly as in §6, including `MEM'L`.
   - Topic tags from committee, then statute chapter, then keywords. Untagged items go into an "Other" bucket that isn't emailed.
   - Shell **flag** only (`-TECH`, a leading `$`, or "technical change" in the synopsis).
   - Votes with zero nays are index-only.
5. **Digest**
   - HTML email plus a plain-text fallback, sections as in §4, excluding section 2 (shell changes, M2).
   - Every item carries an official link and an inclusion reason.
   - A quiet week still sends a short message that says what was checked.
   - Health footer: per-source success or failure, last successful fetch, and repo size.
6. **Workflows**
   - `collect.yml`: cron at 04:00 and 05:00 UTC; the job exits unless the `America/Chicago` hour is 23. Commits the updated `data/` with the bot identity.
   - `digest.yml`: Mondays at 11:00 and 12:00 UTC; the job exits unless it's 06:00 Chicago time. The sent-digest ledger guarantees exactly one send per week.
   - Both also allow manual `workflow_dispatch` with a `--dry-run` that renders the digest to the job summary without sending.
7. **Safeguards**
   - A CI job that fails if any tracked file contains an email address (other than an allowlisted GitHub `noreply` pattern), a Windows user-profile path (drive letter followed by the Users folder), or a token-like string. Write the pattern so these docs don't trip it. It must not contain the owner's address itself.
   - Document in the README that the owner should enable secret scanning with push protection.

### Out of scope for M1

Shell-bill rewrite detection and alerts (M2), federal anything (M4), the public site (M5), contact packets (M6), any AI model, and deleting or restructuring the old tracker.

### Acceptance checks for M1

| # | Check | Pass condition |
|---|---|---|
| 1.1 | Fixture: the owner's Fritts sponsorship export (134 items: 90 HB, 14 SB, 24 HR, 4 HJR, 2 SJR) | The index contains all 134 bill IDs with matching chief-sponsor and last-action values, plus each item's Fritts role, which the export doesn't show. *The export file goes in `tests/fixtures/` only after review; it holds no personal data.* |
| 1.2 | Ceremonial rule | Exactly the 24 items listed from the Oct 16 test are flagged. HR0055, HR0112, HR0292, HR0316, HR0494, HJR0012 and HJR0024 are **not** flagged. |
| 1.3 | Shell flag | HB0742, HB2083, HB2137, HB2211 and HB4179 are flagged |
| 1.4 | Votes | HB0024: Fritts yea 2025-04-08 (House); Arellano yea 2025-05-22 (Senate). Counts: Fritts 1,469 floor votes, Arellano 1,502 (current CSV). Roll calls with ≥1 nay: Fritts 644, Arellano 371. |
| 1.5 | Replay | Running collection twice in a row on unchanged sources produces no new digest items and no new data commits |
| 1.6 | Failure isolation | With one source forced to fail, the others still update, and the digest's health footer names the failed source |
| 1.7 | Rate rules | The logs show ilga.gov requests sequential and ≥10 s apart, and no requests to logged-in paths |
| 1.8 | Privacy | The CI privacy check passes. `git log --format='%ae'` shows only `noreply` addresses. Workflow logs never print the From or To address. |
| 1.9 | Digest | A dry run renders all sections. One real send lands in the owner's inbox. A second trigger in the same week sends nothing. |
| 1.10 | Size | The `data/` footprint is reported; the repo is under 100 MB |
| 1.11 | Tests | All tests pass in CI on a clean runner (no machine-specific paths) |

### Report back

Send a short summary listing:
- what was built;
- each M0 finding and each M1 check, with pass, fail or blocked and the evidence;
- anything that deviated from this brief and why;
- open risks;
- the next recommended step.

Don't include large logs or copied source files.
