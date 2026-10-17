# Inference evaluation v2: quarantine and evidence checks

**Status: completed October 17, 2026; quality gate failed. Routine inference remains disabled.** The first experiment stays frozen in `docs/INFERENCE_EVALUATION_RESULTS.md`, its original corpus, report, and ledger. This is a separate experiment with a separate corpus, config, ledger, and receipt.

## What changed

The v2 preflight checks source text for several instruction-shaped structures: attempts to override earlier/system/developer instructions, direct commands to label a notice, commands to expose credentials, and commands to assert a bill passed. Matching excerpts are quarantined before request construction. They are recorded with zero reserved cost and are never included in an API request. The classifier does not decide whether an attack is safe.

For non-quarantined text, each topic quotation still must appear exactly in the source. It must also contain a topic-specific policy anchor, so a literal mention such as “housing bill passed today” does not count as housing evidence. The system requires the category quotation to be extractive as well. These rules are deterministic screening controls, not a semantic proof that a policy claim is true. The source remains attributed, unverified content; an ambiguous or unrecognized attack can still pass the narrow patterns.

The frozen v1 held-out attack that added a false housing claim is included as a quarantine regression. Four further adversarial/regression examples test override, output-category, and credential-disclosure wording. All five are expected to be stopped before a paid request.

## Actual website evidence available

The old read-only archive currently contains **one** genuine semantic page delta suitable for this sample: a new Lee County Democrats Facebook post appeared in the website's homepage feed, encouraging vote-by-mail voters to deliver unmailed ballots to the County Clerk. The compact v2 fixture includes only the added post text and public provenance:

- Page: [Lee County Democrats homepage](https://leecodemocrats.com/)
- Organization: Lee County Democrats
- Collection receipt time: October 16, 2026 at 8:00 a.m. Central (`2026-10-16T13:00:13Z`)
- Prior and current normalized-content hashes, plus the archived change event ID, are in `tests/fixtures/inference-evaluation-v2.json`.
- The collector reported this page as changed. The retained diff shows the post added between the archived observations. A photo/link adjustment on that same page is not counted as a separate content example.

The available archive does **not** support a plural sample of independent real website changes: its October 15–16 snapshots contain only this one semantically new changed page. The remaining clean classification examples are explicitly synthetic, and the attack cases are synthetic or frozen-v1 regressions. The test must not be described as measuring general accuracy on real party-site changes. Collect and review additional actual deltas before drawing that conclusion. Current site text without a paired before/after capture is not labeled a delta.

A one-time bounded live check on October 17 fetched each configured homepage at most once. The Democrats page's only apparent new line was already present in the October 16 normalized baseline; its larger text block came from parser chunking, so it was rejected as a new delta. The GOP retrieval returned a Unicode encoding error before usable comparison evidence was produced. It was not retried. These checks did not add examples to the corpus.

The event category set also lacks a dedicated voter-information class. The actual example is provisionally labeled `position_statement` because the publisher explicitly urges an election-related action; it has no policy-topic label. Review that taxonomy decision before treating scores as reliable.

## Bounded review protocol

The v2 corpus has 10 records: 2 development examples and 8 held-out examples. Five held-out records are quarantined without a model request; **five** model requests remain. At USD 0.02 per request, the estimated reservation is USD 0.10. The config caps any v2 run at 30 requests and USD 0.60, below the owner's USD 20 overall trial cap. The evaluator sums outstanding liabilities from both v1 and v2 ledgers before allowing a new reservation; unknown billing retains its full reservation. There are no retries.

The v2 metrics have only three non-quarantined held-out cases, including the single actual site delta. Their scores are descriptive only. The original thresholds remain unchanged: 90% held-out category accuracy, 90% topic precision, and 85% topic recall. Undefined precision or recall fails the gate. The evaluation also requires at least five distinct actual website deltas; the current one is reported as **insufficient real-change coverage**, and this alone prevents a v2 quality pass. Gates also require every annotated attack to be quarantined, matching-party event examples to receive the same category/topics, and the repeated event classification to remain stable. Passing v2 would not enable routine inference or approve a website classifier for production.

The completed run preserves the one-real-delta limitation and provisional voter-information category. To run the offline tests (no reservation or API call):

```sh
python -m unittest discover -s tests -p test_inference_eval.py -v
```

The hosted workflow explicitly selected v2 and preserved its separate ledger and receipt. Do not reserve or dispatch this experiment again; the existing reservation prevents another execution. The v1 default remains unchanged.

## Completed result

[Hosted run](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39039387630) completed successfully as an execution on October 17 at 9:07 a.m. Central. Successful execution is separate from classifier acceptance. Read the frozen [receipt](evidence/inference-evaluation-v2.json) and `data/inference-evaluation-v2-ledger.json` for request hashes, charges, timestamps and gates.

- Five attack cases were deterministically quarantined, with no model request and zero charge. This validates these patterns only, not general prompt-injection immunity or model resistance to unseen attacks.
- Five paid requests cost **USD 0.00027216**; no uncertain billing remains. Combined with v1's USD 0.00145256, the two experiments cost **USD 0.00172472**, within the USD 20 trial cap. This is recorded experiment cost, not an account-wide balance statement.
- Both development party-event cases passed and matched. Among three eligible held-out cases, only the synthetic housing-policy case passed: valid output and category accuracy were **1/3**. The actual vote-by-mail change and synthetic meeting case were rejected with `unsupported-output-quote`.
- That safe error covers a non-string, over-240-character, impermissibly empty or non-extractive quotation. Invalid raw output is not retained, so the receipt does not establish which quotation condition failed. The validator did not promote either response into a finding.
- Topic precision and recall were each 1/1 on this tiny set; that does not overcome the two invalid outputs. The actual-delta coverage gate also failed: **one distinct delta, minimum five**. Repeated notices or different pieces of one captured page change cannot inflate this count.

**Decision: no activation.** Preserve v1 and v2 as regression material, without relabeling or retuning them into a fresh score. Before another evaluation, collect additional compact, paired before/after website changes and review the voter-information taxonomy. A future version should consider model-selected source-span IDs with deterministic quotation assembly, reducing dependence on free-text quotation fidelity. That proposal has not been implemented or evaluated. Any future model/provider or prompt change needs a separately versioned held-out trial; routine source collection remains deterministic.
