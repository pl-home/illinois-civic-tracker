# M0 findings and M1 release gates

> Documentation review: October 22, 2026. Historical evidence/setup; not current activation instructions. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

**Latest October 17 scope update:** the owner authorized recent media reports for all five members and narrow routine Qwen3 32B / DeepInfra relevance screening, with USD 0.02 daily, USD 0.20 weekly and USD 20 lifetime limits. [MEDIA_REPORTS.md](MEDIA_REPORTS.md) describes operation and evidence limits. Older statements excluding routine inference are superseded only for this task; party and legislative inference remain disabled.


**October 17 daily website scope update:** the owner explicitly authorized daily public website refresh at **01:00 America/Chicago**, superseding its previous 23:00 target and manual-only status. This staged source-refresh release does not declare unresolved M0/M1 checks passed or enable the weekly digest/inference. Read [DAILY_REFRESH.md](DAILY_REFRESH.md) for source coverage, retained failures, initial hosted verification and remaining gates. Earlier status statements below are dated evidence.


Updated 2026-10-16. **M0 is incomplete; M1 is not deployed.** This file is the review entry point. The product direction is in [PRODUCT_VISION.md](PRODUCT_VISION.md), and the required checks are in [BUILD_BRIEF_M0_M1.md](BUILD_BRIEF_M0_M1.md).

The former Codex refresh and Windows website task were stopped before this repository was created. Historical evidence was read without modifying the archive. Only reviewed public facts and compact findings were ported. No routine AI operation, nightly collection, or weekly delivery schedule is enabled here.

## M0 verification

Initial source observations ran **2026-10-16 14:10:50–14:12:38 UTC**. Later evidence files carry their own observation timestamps. PASS is limited to the stated sample; it does not mean the entire product is implemented.

| Check | Result | Evidence and implication |
| --- | --- | --- |
| 0.1 FTP equivalence and discovery | PASS sampled equivalence; bundle search limited | **50/50** files matched, covering 20 HB, 14 SB, 10 HR, 4 HJR and 2 SJR. Current FTP bytes were compared with hash-verified archived main-site mirror bytes, with their original retrieval dates retained. This was not a simultaneous fetch from both hosts. The [FTP listing](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/) exposed **12,855** entries with dates, times and sizes. No ZIP link appeared in that directory or its BillStatus parent; no claim is made about other directories. Use per-file listing changes, then hashes. |
| 0.2 FTP sync timing | BLOCKED pending elapsed observations | The first successful hosted listing/header observation was recorded at **14:36:23 UTC**, alongside the initial local sample. Two successful hosted observations (14:36 and 21:15 UTC on October 16) had the same listing hash. Same-day observations cannot establish daily sync time, and a quiet listing may remain inconclusive even over several days. Actual timestamps, not scheduled start times, establish coverage. The bounded six-hourly workflow remains active through 2026-10-20 UTC. Listing timestamps have no established timezone and are not a sync-completion guarantee. Need 2–3 days of successful observations. |
| 0.3 Amendment statute references | PASS for two bills | [HB0742 XML](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400HB0742.xml) and [HB2137 XML](https://ftp.ilga.gov/Legislation/104/BillStatus/XML/10400HB2137.xml) retain original references and carry amendment-section additions/deletions. A flat union would misrepresent current text. Preserve section and operation; rewrite detection remains M2. |
| 0.4 Floor CSV versus verified votes | PARTIAL: all baseline gaps classified | Baseline comparison: 2,310/2,525 legacy comparison keys matched (91.485%). The tested offline audit resolves **129 additional keys**, giving **2,439/2,525 (96.594%)** exact-choice or explicit-evidence coverage. The remaining **86 keys** retain 55 incomplete PDF amendment captions, 22 No Vote/NV label differences, 2 missing CSV motion fields, 1 CSV amendment caption, and 6 date-candidate discrepancies (one also lacks amendment detail). These are comparison keys, not distinct physical votes. All 215 original cases remain in the [audit](evidence/m0-vote-audit.json); no unknown value or date was silently repaired. |
| 0.5 CSV regeneration cadence | BLOCKED pending time | Initial Last-Modified: **2026-10-16 03:45:47 GMT**. Latest vote date: **2026-05-31**. A regenerated export is not necessarily new legislative activity. Record daily headers and recheck after the November veto session; this cannot be completed in October. |
| 0.6 PDF parsing and hearing fallback | PASS bounded sponsor and historical fallback samples; upcoming forms pending | Sponsor PDF sample remains 20/20. Static committee PDFs are still empty and not validated on live rows. Public committee hearing history provides a compliant alternative: **5 nonempty detail pages / 103 posted items** parsed; **20/20 distinct bill identities** and **20/20 committee histories** cross-check with FTP XML, and **5/5 hearing times** match public history rows. XML does not establish hearing time. The range control calls a disallowed API, which was not used. Historical witness-results links are kept separate from active submission forms; an upcoming form has not been validated. See [fallback evidence](evidence/m0-hearing-fallback.json). |
| 0.7 Capitol Fax feeds | PASS RSS access; matching coverage qualified | Eight search feeds each returned 12 items. After excluding Protected titles, public counts were Fritts 9, Arellano 10, LaHood 10, Durbin 12, Duckworth 9, Lee County 12, county Democrats 12, county Republicans 11. Newest public dates span July 10–October 14. Search results are candidates, not proof that every post names the subject. Store only title/link/date; independently establish a match before describing a mention. |
| 0.8 Hosted source access | PASS corrected runner check | At **14:32:37 UTC**, Ubuntu reached both ILGA hosts, Capitol Fax and both party sites. Initial certificate-verification failures (code 20) were resolved by supplying a fingerprint-pinned, CA-published intermediate. Hostname and system-root verification stay enabled. CSV access was a header-only HEAD, not a zero-byte source file. [Successful hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/38916531335). |
| 0.9 Gmail self-delivery | PASS | After an owner-confirmed credential correction, SMTP accepted the self-test and its exact Message-ID was found in **INBOX**, using a read-only search, at **14:46:56 UTC**. The first failed receipt remains in m0-mail-attempts.json; no credentials or addresses are recorded. The successful receipt and no-send authentication diagnostic are separate. Ordinary repeated triggers remain blocked. This verifies the transport, not the unbuilt weekly digest. |
| 0.10 GA103 service | PASS roster sample | [GA103 House roster](https://ftp.ilga.gov/Members/103HouseMembers.xml) contains Bradley Fritts, district 74. [GA103 Senate roster](https://ftp.ilga.gov/Members/103SenateMembers.xml) contains neither target; Arellano is absent from both rosters. Configure Fritts from GA103 and Arellano from GA104. Historical backfill is deferred to its milestone. |

### Vote comparison details

The frozen first comparison matched 2,177 keys (86.218%). Removing source prefixes such as HOUSE BILL and standardizing explicit amendment number spellings raised that to 2,310. The initial evidence is retained; the later reconciliation supersedes its comparison totals without re-downloading sources.

Of the 209 missing exact keys, **203 have a same-bill/chamber/date candidate**. Many archived motions are fallback document labels or lack amendment numbers. This is evidence of a join limitation, not permission to match without a motion. The six choice differences all compare CSV **No Vote** with archived PDF **not-voting**: Fritts HB2771 (two motions, 2025-06-01), HB5090 (2026-05-31), HB5486 (2026-05-06), SB2351 (2025-05-22), SB2914 (2026-05-21). No Vote remains an explicit unknown value; it is not silently reclassified as absence, excusal or a nay. No yes-versus-no contradiction was established by these exact matches.

The follow-up audit classifies every original gap without changing the archived records. Explicit header/index motion text resolves 127 keys; two more use a same-roll companion with an identical complete named-vote body. Matching a tally alone cannot fill in amendment numbers. Competing companion motions are rejected as ambiguous. Resolution outcome captions and empty report columns are handled explicitly, and 3/5 fractions are not split as column separators.

The 96.594% figure measures coverage of the original comparison-key denominator. It does not assert that every source date or every physical roll call is consistent. Known index/PDF date conflicts remain visible even on otherwise resolved keys. No Vote remains unknown in the shared CSV normalizer; the deeper audit exposes 22 such label cases within the original 215, rather than inventing a global equivalence with NV.

The CSV's larger coverage also includes executive appointments that the prior bill-type discovery omitted. CSV-only rows are preserved for review, not called errors or newly occurring activity. Committee votes remain a separate source; the floor CSV cannot replace them.

### PDF limits

The bounded sponsorship parser checks complete fields rather than just recognizing bill numbers. Tests cover parenthesized alternate sponsors and the two-name `and` form. It is intentionally an M0 sample helper: punctuation-based name splitting is not a production solution for suffixes or hyphenated names. M1 role normalization must replay dated source actions, preserve removals and chief changes, and validate against the subject-specific export.

The [House schedule](https://ilga.gov/House/Schedules) and [Senate schedule](https://ilga.gov/Senate/Schedules) are fallback candidates discovered through official search results. Their current views were empty. Inspection showed that the range control calls /API/Hearings/GetHearingsListByRange, disallowed by the project access policy, so it was not called. Public committee history/detail pages were instead tested on nonempty historical samples. They are a validated parsing fallback, not a deployed nightly collector. Active witness-slip forms and future date-change handling still need acceptance checks.

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
| 1.8 Privacy and identities | PASS current foundation; ongoing gate | Reviewed public files and fixtures pass the scanner. A one-time history audit reviewed 102 previously published blobs with zero private-data findings; a corrected legacy text-encoding blob was reviewed explicitly. All audited commit emails were noreply. Local commits use GitHub noreply; evidence commits use the Actions bot. GitHub reports secret scanning and push protection enabled. Production email logging still requires release review. |
| 1.9 Digest and repeat suppression | BLOCKED, not built | The M0 self-test does not implement a weekly digest. Rendering, weekly ledger and repeat-trigger tests remain. |
| 1.10 Size | PASS current foundation; growth simulation pending | The prior foundation was below 1 MB; the follow-up public working files total approximately **1.16 MB**, excluding Git and ignored raw scratch; see [follow-up validation](evidence/m0-followup-validation.json). At that check data/ remained empty; the October 17 manual evaluation adds only its compact trial ledger, not a production index. No raw PDF, HTML, ZIP or full CSV is committed. M1 size reporting and annual growth checks remain. |
| 1.11 Clean-runner tests | PASS clean CI for current foundation | Clean Ubuntu CI passed for the foundation; the expanded local suite has **52 passing tests**, including TLS verification retention, rate timing, app-password whitespace handling and mail safeguards. [The updated 52-test clean-runner CI passed](https://github.com/pl-home/illinois-civic-tracker/actions/runs/38988476454); current validation is in [m0-followup-validation.json](evidence/m0-followup-validation.json). The original foundation receipt remains preserved. |

### October 17 basic browser scope

The owner moved basic browsing into the first release and authorized a separately labeled historical preview. It renders all 134 reviewed export entries and exactly 24 ceremonial flags, with explicit unknown role/filing fields. It does not satisfy acceptance 1.1's complete role history or the production index gate. Production collection/digest schedules remain disabled. See [BROWSING_PAGE.md](BROWSING_PAGE.md) for the artifact, source limits and validation.

## Evidence and reproduction

- [Initial findings](evidence/m0-initial.json): source fingerprints, all 50 comparisons, amendment references, initial comparison differences, roster checks, PDF sizes and feed samples.

- [Vote reconciliation](evidence/m0-vote-reconciliation.json): every unresolved key and CSV-only key under the current narrow normalization.

- [Follow-up vote audit](evidence/m0-vote-audit.json): every original unresolved key with explicit classifications, raw choices and source links.

- [Historical hearing fallback](evidence/m0-hearing-fallback.json): five nonempty pages, twenty XML identity checks and history-time checks.

- [PDF sample](evidence/m0-pdf-sample.json): each of the twenty compared rows, raw sponsor block and field-by-field results.

- [Hosted access receipt](evidence/m0-runner-access.json): host failures or verified fetch fingerprints, without private exception text.

- [Timing observations](evidence/m0-observations.json), [confirmed mail receipt](evidence/m0-mail-delivery.json), [no-send mail diagnostics](evidence/m0-mail-diagnostics.json), and [history audit](evidence/m0-history-audit.json) distinguish source availability, credential setup and actual delivery. The [failed first attempt](evidence/m0-mail-attempts.json) is preserved separately; the corrected self-test has an inbox delivery pass.

Run `python -m unittest discover -s tests -v` and `python -m civic_tracker.privacy` after installing the project. The verification CLI accepts explicit read-only input paths rather than storing machine-specific locations. `verify_sources` is a networked one-time probe; `verify_pdf_sample` reuses downloaded reports. Do not rerun the entire source probe just to recompute vote joins.

The history audit traversed every reachable Git blob and applied the current privacy patterns, then checked both author and committer identities. One earlier Markdown encoding was decoded explicitly for review; current files use UTF-8/LF. CI scans the checked-out tree; the separate timestamped history audit is not a claim that CI continuously audits history.

## Deviations and open risks

1. M0 uses current FTP versus verified historical mirror bytes to avoid fifty unnecessary main-host requests. Evidence preserves each comparison date.

2. A bounded metadata observation is the only new schedule at this stage; it disables itself on the first wake after its configured end time. It is not the M1 collector. No weekly digest schedule is enabled.

3. Linux requires a missing intermediate for ILGA. The pinned fingerprint is obtained from a platform-verified chain; the CA URL supplies identical DER bytes. Only that intermediate is loaded, with partial-chain acceptance disabled. No new root is trusted. Certificate rotation can cause a visible failure requiring review.

4. A sent-week ledger cannot make SMTP submission and Git persistence atomic. A crash can leave delivery uncertain. M1 must suppress automatic retries of uncertain submissions or document another recovery design instead of claiming unconditional exactly-once delivery.

5. GitHub scheduled jobs may be late. DST gating, catch-up behavior, failure notices, duplicate suppression and source staleness are still design/release gates.

6. A state-writing workflow initially checked out the dispatch revision while waiting behind another evidence writer, and its reservation push failed before SMTP. These workflows now check out current main inside their shared concurrency gate. One findings commit also used legacy Windows text encoding; CI rejected it, and current files were corrected to UTF-8. The historical blob was reviewed with zero private-data findings.
7. M0 helpers still contain bounded reconciliation identifiers. M1 source selection and aliases must be fully configuration-driven; these helpers are not the production architecture.

## Next step

Hosted access and owner-only self-delivery pass. Historical nonempty hearing parsing now passes its bounded sample. Review the 86 retained vote-source gaps and verify upcoming hearing forms before deployment. Continue the bounded timing observations for 2–3 days; the post-veto cadence check remains a dated follow-up. **Do not enable M1 collection or digest schedules while these release gates remain unresolved.**

## Hosted inference decision

After the earlier planning-only decision, the owner authorized one bounded Qwen3 32B / DeepInfra evaluation on October 17. It completed 30 calls for USD 0.00145256 and failed the mandatory instruction-injection gate. [The result review](INFERENCE_EVALUATION_RESULTS.md) preserves metrics, costs and limitations. Routine inference remains disabled; M1 remains deterministic. The manual evaluator has its own public/synthetic corpus, durable trial ledger and no schedule.
