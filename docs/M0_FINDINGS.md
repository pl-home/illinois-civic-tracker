# M0 findings and M1 release gates

Updated 2026-10-16. **M0 is incomplete; M1 is not deployed.** This file is the review entry point. The product direction is in [PRODUCT_VISION.md](PRODUCT_VISION.md), and the required checks are in [BUILD_BRIEF_M0_M1.md](BUILD_BRIEF_M0_M1.md).

The former Codex refresh and Windows website task were stopped before this repository was created. Historical evidence was read without modifying the archive. Only reviewed public facts and compact findings were ported. No routine AI operation, nightly collection, or weekly delivery schedule is enabled here.

## M0 verification

Initial source observations ran **2026-10-16 14:10:50–14:12:38 UTC**. Later evidence files carry their own observation timestamps. PASS is limited to the stated sample; it does not mean the entire product is implemented.

| Check | Result | Evidence and implication |
| --- | --- | --- |
| 0.1 FTP equivalence and discovery | PASS sampled equivalence; bundle search limited | **50/50** files matched, covering 20 HB, 14 SB, 10 HR, 4 HJR and 2 SJR. Current FTP bytes were compared with hash-verified archived main-site mirror bytes, with their original retrieval dates retained. This was not a simultaneous fetch from both hosts. The [FTP listing](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/) exposed **12,855** entries with dates, times and sizes. No ZIP link appeared in that directory or its BillStatus parent; no claim is made about other directories. Use per-file listing changes, then hashes. |
| 0.2 FTP sync timing | BLOCKED pending elapsed observations | One initial listing cannot establish daily sync time. A bounded six-hourly observation workflow is prepared through 2026-10-20 UTC. Listing timestamps have no established timezone and are not a sync-completion guarantee. Need 2–3 days of successful observations. |
| 0.3 Amendment statute references | PASS for two bills | [HB0742 XML](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400HB0742.xml) and [HB2137 XML](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400HB2137.xml) retain original references and carry amendment-section additions/deletions. A flat union would misrepresent current text. Preserve section and operation; rewrite detection remains M2. |
| 0.4 Floor CSV versus verified votes | BLOCKED reconciliation gate | [Official CSV](https://ilga.gov/documents/reports/static/104MemberVotes.csv): **261,928 rows / 2,843 roll calls**; fresh bytes exactly matched the supplied file. From 3,544 verified source documents, exclude 957 committee documents. The remaining 2,587 floor documents collapse to **2,525 unique subject/bill/chamber/date/motion keys**. Explicit motion aliases yield **2,310 exact choice matches (91.485%)**, **209 keys without an exact CSV key**, and **6 choice-label differences**. Every residual difference and all 618 CSV-only keys are retained in the reconciliation evidence. Do not retire PDF audit evidence or silently loosen joins. |
| 0.5 CSV regeneration cadence | BLOCKED pending time | Initial Last-Modified: **2026-10-16 03:45:47 GMT**. Latest vote date: **2026-05-31**. A regenerated export is not necessarily new legislative activity. Record daily headers and recheck after the November veto session; this cannot be completed in October. |
| 0.6 PDF parsing | PASS bounded sponsor sample; BLOCKED hearings | First ten parseable rows on the first page of each sponsor report: **20/20** match XML role, last action, chamber and date. Sample owners are Carol Ammons and Neil Anderson; this is layout verification, not Fritts/Arellano index acceptance. Sponsor PDFs are approximately **46.3 MB / 937 pages** and **28.0 MB / 564 pages**, unsuitable as the default nightly source. Both committee PDFs returned one page with **NO DATA FOUND**. Obtain a nonempty hearing sample or validate the public schedule fallback before enabling hearing coverage. |
| 0.7 Capitol Fax feeds | PASS RSS access; matching coverage qualified | Eight search feeds each returned 12 items. After excluding Protected titles, public counts were Fritts 9, Arellano 10, LaHood 10, Durbin 12, Duckworth 9, Lee County 12, county Democrats 12, county Republicans 11. Newest public dates span July 10–October 14. Search results are candidates, not proof that every post names the subject. Store only title/link/date; independently establish a match before describing a mention. |
| 0.8 Hosted source access | PASS corrected runner check | At **14:32:37 UTC**, Ubuntu reached both ILGA hosts, Capitol Fax and both party sites. Initial certificate-verification failures (code 20) were resolved by supplying a fingerprint-pinned, CA-published intermediate. Hostname and system-root verification stay enabled. CSV access was a header-only HEAD, not a zero-byte source file. [Successful hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/38916531335). |
| 0.9 Gmail self-delivery | PENDING single owner-only workflow | The three repository secrets were configured privately. The first workflow stopped in reservation before SMTP (no message sent). State-writing workflows now check out current main after entering their shared concurrency gate, rather than a stale dispatch revision. A manual-only workflow reserves one test in Git before SMTP submission, then searches INBOX read-only for its exact generated Message-ID. No other messages are read. A duplicate reservation blocks another send. Success requires an inbox receipt, not merely an SMTP acceptance or Sent-folder entry. |
| 0.10 GA103 service | PASS roster sample | [GA103 House roster](https://ftp.ilga.gov/Members/103HouseMembers.xml) contains Bradley Fritts, district 74. [GA103 Senate roster](https://ftp.ilga.gov/Members/103SenateMembers.xml) contains neither target; Arellano is absent from both rosters. Configure Fritts from GA103 and Arellano from GA104. Historical backfill is deferred to its milestone. |

### Vote comparison details

The first comparison matched 2,177 keys (86.218%). Removing source prefixes such as HOUSE BILL and standardizing explicit amendment number spellings raised that to 2,310. The initial evidence is retained; the later reconciliation supersedes its comparison totals without re-downloading sources.

Of the 209 missing exact keys, **203 have a same-bill/chamber/date candidate**. Many archived motions are fallback document labels or lack amendment numbers. This is evidence of a join limitation, not permission to match without a motion. The six choice differences all compare CSV **No Vote** with archived PDF **not-voting**: Fritts HB2771 (two motions, 2025-06-01), HB5090 (2026-05-31), HB5486 (2026-05-06), SB2351 (2025-05-22), SB2914 (2026-05-21). No Vote remains an explicit unknown value; it is not silently reclassified as absence, excusal or a nay. No yes-versus-no contradiction was established by these exact matches.

The CSV's larger coverage also includes executive appointments that the prior bill-type discovery omitted. CSV-only rows are preserved for review, not called errors or newly occurring activity. Committee votes remain a separate source; the floor CSV cannot replace them.

### PDF limits

The bounded sponsorship parser checks complete fields rather than just recognizing bill numbers. Tests cover parenthesized alternate sponsors and the two-name `and` form. It is intentionally an M0 sample helper: punctuation-based name splitting is not a production solution for suffixes or hyphenated names. M1 role normalization must replay dated source actions, preserve removals and chief changes, and validate against the subject-specific export.

The [House schedule](https://ilga.gov/House/Schedules) and [Senate schedule](https://ilga.gov/Senate/Schedules) are fallback candidates discovered through official search results. They have not yet been validated as working hearing collectors. An empty report cannot establish reliability with live hearing rows.

## M1 acceptance status

| Check | Status | Current evidence / missing work |
| --- | --- | --- |
| 1.1 134-item Fritts index | BLOCKED, not built | Reviewed fixture contains exactly 90 HB, 14 SB, 24 HR, 4 HJR, 2 SJR. No production index or complete role/action comparison exists yet. |
| 1.2 Ceremonial rule | PASS fixture rule only | Exactly 24 IDs flagged; all seven named negative examples remain unflagged. Expected IDs were derived from the reviewed export and specified rule. An independent historical 24-ID file was not separately supplied. |
| 1.3 Five shell examples | BLOCKED full acceptance | Generic flag tests pass; a five-bill source fixture has not been checked. No rewrite detection is implemented or claimed. |
| 1.4 Floor-vote counts | PASS source verification; M1 storage pending | Fritts **1,469** rows, **644** with at least one nay; Arellano **1,502**, **371** split. HB0024: Fritts yea House 2025-04-08; Arellano yea Senate 2025-05-22, both zero nays. Counts computed from the full CSV before selecting members. Reconciliation gate remains open. |
| 1.5 Idempotent collection | BLOCKED, not built | No M1 collector, seen-items ledger or unchanged-source replay yet. |
| 1.6 Failure isolation | BLOCKED M1 acceptance | M0 runner probe continues across host failures. Production collector orchestration and digest footer are not built. |
| 1.7 Request policy | PASS sampled corrected timing; M1 release review pending | Main-host lock, persistent timing gate and disallowed-path checks exist. Initial six live requests were sequential, with a minimum recorded spacing of **19.99913 seconds**: a sub-millisecond clock-ordering defect, now fixed. The timestamp persisted is now the actual recorded attempt start. A regression test passes; the corrected hosted run recorded **20.00011 seconds** between starts. |
| 1.8 Privacy and identities | PASS current foundation; ongoing gate | Reviewed public files and fixtures pass the scanner. Local commits use GitHub noreply; evidence commits use the Actions bot. GitHub reports secret scanning and push protection enabled. Production email logging still requires release review. |
| 1.9 Digest and repeat suppression | BLOCKED, not built | The M0 self-test does not implement a weekly digest. Rendering, weekly ledger and repeat-trigger tests remain. |
| 1.10 Size | PASS current foundation; growth simulation pending | Reviewed working files excluding Git and scratch are below 1 MB; data/ is empty. No raw PDF, HTML, ZIP or full CSV is committed. M1 size reporting and annual growth checks remain. |
| 1.11 Clean-runner tests | PASS clean CI for current foundation | [Clean Ubuntu CI passed with 22 tests](https://github.com/pl-home/illinois-civic-tracker/actions/runs/38916497951), including pinned-certificate rejection, rate timing and mail safeguards. |

## Evidence and reproduction

- [Initial findings](evidence/m0-initial.json): source fingerprints, all 50 comparisons, amendment references, initial comparison differences, roster checks, PDF sizes and feed samples.
- [Vote reconciliation](evidence/m0-vote-reconciliation.json): every unresolved key and CSV-only key under the current narrow normalization.
- [PDF sample](evidence/m0-pdf-sample.json): each of the twenty compared rows, raw sponsor block and field-by-field results.
- [Hosted access receipt](evidence/m0-runner-access.json): host failures or verified fetch fingerprints, without private exception text.
- Bounded observations and the mail receipt will appear under `docs/evidence/` when the workflows succeed in writing them.

Run `python -m unittest discover -s tests -v` and `python -m civic_tracker.privacy` after installing the project. The verification CLI accepts explicit read-only input paths rather than storing machine-specific locations. `verify_sources` is a networked one-time probe; `verify_pdf_sample` reuses downloaded reports. Do not rerun the entire source probe just to recompute vote joins.

## Deviations and open risks

1. M0 uses current FTP versus verified historical mirror bytes to avoid fifty unnecessary main-host requests. Evidence preserves each comparison date.
2. A three-day metadata observation is the only proposed schedule at this stage. It is not the M1 collector. No weekly digest schedule is enabled.
3. Linux requires a missing intermediate for ILGA. The pinned fingerprint is obtained from a platform-verified chain; the CA URL supplies identical DER bytes. Only that intermediate is loaded, with partial-chain acceptance disabled. No new root is trusted. Certificate rotation can cause a visible failure requiring review.
4. A sent-week ledger cannot make SMTP submission and Git persistence atomic. A crash can leave delivery uncertain. M1 must suppress automatic retries of uncertain submissions or document another recovery design instead of claiming unconditional exactly-once delivery.
5. GitHub scheduled jobs may be late. DST gating, catch-up behavior, failure notices, duplicate suppression and source staleness are still design/release gates.
6. M0 helpers still contain bounded reconciliation identifiers. M1 source selection and aliases must be fully configuration-driven; these helpers are not the production architecture.

## Next step

Complete hosted access and the single self-delivery test, then resolve the CSV motion/choice gaps and validate nonempty hearing data. Continue the bounded timing observations for 2–3 days; the post-veto cadence check remains a dated follow-up. **Do not enable M1 collection or digest schedules while these release gates remain unresolved.**
