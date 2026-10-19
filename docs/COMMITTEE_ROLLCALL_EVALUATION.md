# Committee roll-call PDF evaluation

The owner authorized this manual evaluation on October 19, 2026. It does not enable daily committee collection or change any verified vote record. The current release's historical coverage label remains accurate. Paused committee integration work is separate.

## Sample and reference answers

Six public GA104 committee PDFs were freshly downloaded at the sequential twenty-second backfill interval. Each response matched its archived SHA-256. Every page was rendered and visually checked for the member's printed choice, all four tally counts, the committee, the measure/amendment and the motion before inference. These are curated historical examples, not activity on the evaluation date, a random sample or a general accuracy guarantee.

| Member | Measure / motion | Raw choice | Yea | Nay | Present | Not Voting |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Fritts | HB1054 / Do Pass - Short Debate | N | 19 | 8 | 0 | 2 |
| Fritts | HB2490 / Do Pass As Amended - Short Debate | Y | 18 | 3 | 2 | 6 |
| Fritts | HB1056 HFA2 / Recommends Be Adopted | NV | 16 | 5 | 0 | 8 |
| Arellano | SB93 / Do Pass | N | 7 | 3 | 0 | 0 |
| Arellano | SB1274 SCA1 / Be Adopted | Y | 10 | 0 | 0 | 2 |
| Arellano | HB762 / Do Pass | NV | 6 | 0 | 0 | 4 |

Official URLs, dates, source hashes and reviewed reference fields are in [the manifest](../config/rollcall-evaluation.json). NV is preserved as Not Voting; it is not evidence of absence, abstention or excusal. Present is a separate tally category. The recorded motion is not independently converted into a passage, quorum or legal-effect conclusion. For the two House motion lines, the extraction rule selects the last distinct printed motion line and preserves its procedural qualification.

## Extraction and validation

Native PDF text and word coordinates are extracted deterministically with pdfplumber. No hosted PDF parser, OCR, vision model or provider fallback is used. Qwen3 32B through DeepInfra sees only the native text, page boundaries and target member name. Gold labels and prior vote records are not sent to it.

The model must return strict structured evidence for committee, complete measure caption (including amendment), motion, printed member name and raw vote, and the four printed tally counts. Acceptance requires:

- Literal quotation occurrence on the cited page, with bounded fields and exact schema.
- A unique printed member cell, resolved using native word positions. A nearby code from the other column cannot substitute for the target's code.
- Tally numbers bound to the printed labels, plus reconciliation against every named Y/N/P/NV entry in the PDF.
- Agreement with the independent visually reviewed reference answer, including the amendment identity. This gold comparison is evaluation-only; it is not an available production oracle.

The deterministic reference checks passed all six documents before inference. All **38** deliberately corrupted answers/sources were rejected: changed vote, legitimate neighboring member, changed tally, wrong page, lost column, duplicated page, and dropped amendment identity. These test validator rejection, not model attack resistance or model accuracy. [Offline receipt](evidence/rollcall-offline-validation.json).

## Execution, budget and replay

The manual-only `rollcall-evaluation.yml` workflow shares the source lock. It runs tests, refetches the pinned PDFs, repeats the offline checks, commits a separate six-entry spending ledger, and only then exposes `OPENROUTER_API_KEY` to execution. There is no schedule and no source-record writer.

Each of six calls reserves USD 0.0015: USD 0.009 total. Existing charges and holds, including the earlier uncertain USD 0.005 PDF request, count toward the unchanged USD 0.02/day, USD 0.20/Monday-Sunday Chicago week and USD 20 lifetime caps. A request is limited to 10,000 serialized UTF-8 bytes and 1,000 output tokens, with maximum provider prices of USD 0.10/M input and USD 0.40/M output. The byte bound plus token overhead allowance fits its reservation. API-reported charges settle individual holds; unknown charges keep their holds.

Configuration, prompt and native extraction hashes bind execution to preparation. An exclusive permanent claim and consumed ownership receipt prevent concurrent or repeated execution. A committed ledger prevents another workflow from preparing the batch again. Each attempted request is recorded before its POST. No paid retries. A transport error, routing mismatch, excess charge or date rollover stops further calls; known unsent entries settle to zero with explicit receipts. If the runner dies, durable reservations remain conservative rather than permitting replay. Rejected model text is not published. An ordinary evidence mismatch can still allow the remaining distinct cases to be evaluated once.

Run `python -m civic_tracker.rollcall_eval prepare`, then `offline`, then commit the reservations before `execute`. Use the hosted workflow for paid execution. Never reset or delete a ledger to rerun the same batch.

## Storage and gates

Only compact public references, checked outputs, costs and failure codes are committed. PDFs, complete native text and words stay in ignored scratch; preview PNGs expire from the workflow artifact after seven days. The public usage panel includes this evaluation's ledger. No model call directly alters a member vote, committee tally, bill record or meeting.

Daily collection remains disabled. Beyond this small native-text sample, acceptance still needs additional layouts and page counts, missing-member and source-conflict cases, scanned/poor-text decisions, live discovery and incremental replay tests, and a review of the production collector's integration. The full source PDFs must remain reachable through their official URLs; an extracted text match alone cannot establish visual layout correctness.

## Results

Hosted model results and measured costs are pending. The single attempted batch will remain in `data/rollcall-evaluation-report.json` and `data/rollcall-evaluation-ledger.json`, even if it fails. Do not equate workflow completion with evidence passing.
