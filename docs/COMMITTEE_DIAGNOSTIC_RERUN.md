# Committee PDF diagnostic rerun

The owner authorized a separately versioned diagnostic rerun on October 19, 2026.
It uses the same six reviewed PDFs for Fritts and Arellano, unchanged Qwen3 32B /
DeepInfra routing, prompt, response schema, 1,000-token output bound and validation.
This isolates diagnostic observations from a change in the extraction contract.
It is not daily collection, a prompt-tuning trial or a general accuracy estimate.

The immutable first test is documented in
[the original evaluation](COMMITTEE_ROLLCALL_EVALUATION.md). Its manifest, receipts
and spending ledger remain unchanged. The uncertain USD 0.005 PDF hold stays in
accounting. The new fixed `diagnostics-v2` profile uses distinct manifest, scratch,
offline receipt, report and spending ledger paths. Arbitrary version names are
rejected. Existing ownership, pre-network attempt recording, shared lock, stop
conditions and permanent no-replay claims remain in force.

The six new requests reserve at most **USD 0.009**. Before preparation, recorded
Chicago-day charges plus holds were **USD 0.00566776**, leaving **USD 0.01433224**
under the USD 0.02 daily cap. The USD 0.20 weekly and USD 20 lifetime caps also
apply. Shared accounting includes both trial versions; API-reported charges
settle only their own reservations. An unknown charge never becomes zero.

Future rejected receipts contain the new allowlisted response/JSON/status/finish
diagnostics. Independent field checks also report whether committee, measure,
motion, member choice and tally evidence pass when tested separately against the
native source and reviewed reference. These checks retain only fixed result
codes, never rejected text, and do not override abstention or validation failures.
No reference answer is included in the inference request. The bounded error
journal ingests this profile separately, preserving the first test's incidents.

Manual workflow: `rollcall-diagnostics-v2.yml`. It refetches and hashes the official
PDFs sequentially, renders them, runs the deterministic references and rejection
controls, commits reservations, executes at most six calls, and finalizes the
journal. There are no paid automatic retries or provider fallbacks. Daily
committee collection remains disabled pending investigation and remaining
production gates.

## Results and investigation

[Hosted run 39354481195](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39354481195)
completed on October 19 Chicago time (October 20 UTC). Tests, source checks,
38/38 negative controls, privacy checks, journal finalization and Pages publication
succeeded. The **model evidence gate failed: 0/6 accepted**. Workflow success
means the controlled experiment completed and preserved its receipts, not that
extraction passed. No proposed vote or tally entered verified source records.

| Check | Result |
| --- | --- |
| Explicit model status | `unverified` in 6/6 |
| Provider/model match, valid JSON, normal completion | 6/6; no refusals or output truncation |
| Committee evidence | 6/6 matched |
| Motion evidence | 6/6 matched |
| All four tally counts, literal tally evidence and named-roster reconciliation | 6/6 matched |
| Complete bill/amendment caption evidence | 4/6 matched |
| Member name/quote evidence | 0/6; every case failed `evidence-quote` |

HB1054's measure field failed `measure-mismatch`; HB2490's failed
`evidence-quote`. The remaining four complete captions, including both amendments,
passed. Each member proof failed the literal-quote/name-containment test before
the raw-vote and native-cell binding checks could complete. Therefore this is
**not evidence of six incorrect vote choices**, and passing tallies do not make
the individual votes verified. The failures are no longer an unexplained status
or JSON-format issue: the model explicitly abstained and its supporting member
evidence was inadequate under the contract.

The model finished each response normally with valid JSON and the expected
provider/model. The 1,000-token output ceiling was not reached. The source PDF
and native-extraction hashes match the independently reviewed originals, and
the prompt hash is unchanged. Transport, routing, JSON parsing, token truncation
and changed source files are not supported explanations for this run's failures.

An offline reproduction demonstrates one compatible contract problem in all six
cases: substituting the configured display name (for example, `Bradley Fritts`)
for the PDF's printed order (`Fritts, Bradley`) fails `evidence-quote` even when
the source quotation and vote code are otherwise correct. The normalized person
identity still matches. This reproduces the observed failure *class* without
another model call. **It does not prove that this was the model's actual returned
name or quote**: rejected field text was deliberately not retained. A nonliteral
quote or a different name/value mismatch could cause the same code. The model's
reason for choosing `unverified` was not requested or captured.

## Decision and next gate

**Keep daily committee PDF collection disabled.** Do not override `unverified`,
promote the four matching captions or six matching tallies into accepted member
votes, or weaken literal source binding to make this sample pass.

The next bounded improvement should separate canonical person/bill identity from
literal printed evidence. Prefer deterministic extraction and unique source-cell
binding for clean native text; make any model output select or quote that exact
cell instead of restating a display name. A future diagnostic should separately
record safe booleans for quote occurrence, printed-name occurrence, person
identity, raw-vote agreement, and cell binding, without retaining rejected text.
The prompt also needs explicit rules for when `extracted` is permitted, while
preserving abstention. These are proposed contract changes, **not a tested fix**.

Before activation, a separately versioned test must pass the revised contract and
new held-out layouts, multiple pages, missing-member/conflicting-source cases and
unsupported/scanned-source behavior. Production discovery, incremental replay,
deduplication and collector integration remain separate gates. Do not repeat the
unchanged paid batch: its six requests are spent and replay-protected.

## Cost and preservation receipt

All six calls have measured charges totaling **USD 0.00061384** (about **0.0614
cents**). Their USD 0.009 reservation settled to those charges. Recorded project
Chicago-day and week charges are now USD 0.00128160; with the preserved USD 0.005
uncertain earlier PDF hold, liability is **USD 0.00628160**, below USD 0.02/day and
USD 0.20/week. Lifetime liability is USD 0.00849016, below USD 20. Investigation
after the six calls was offline, with no additional model requests.

The original v1 manifest/report/ledger, earlier PDF ledger and all verified
dashboard records are unchanged. Only usage accounting, the new trial receipts
and journal were updated. The journal contains six distinct diagnostic-rerun
incidents alongside the original failures, with no rejected text or credentials.

Receipts: [trial report](../data/rollcall-diagnostics-v2-report.json),
[spending ledger](../data/rollcall-diagnostics-v2-ledger.json),
[offline controls](evidence/rollcall-diagnostics-v2-offline-validation.json),
[investigation and preservation checks](evidence/committee-diagnostics-v2-investigation.json).
The updated implementation passes **198 offline tests**. New tests cover version
isolation, combined liability, replay rejection and independent field diagnostics.
