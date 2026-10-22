# One bounded hosted inference evaluation

> Documentation review: October 22, 2026. Historical evidence/setup; not current activation instructions. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

The owner authorized this evaluation on October 17, 2026: Qwen3 32B through DeepInfra, within the USD 20 trial cap. **Routine inference remains disabled.** This is separate from the deterministic M1 collection/digest and the public browsing page.

The [first run and review](INFERENCE_EVALUATION_RESULTS.md) are complete: 30 calls, USD 0.00145256, failed mandatory adversarial gate. The unchanged protocol and frozen inputs below describe that original experiment.

## What is tested

The corpus has 4 development cases and 26 held-out cases. Six held-out excerpts are short descriptions from the reviewed public Fritts export. The other cases are clearly labeled synthetic; their party notices do not describe actual Lee County activity. All six priority topics appear, alongside substantive resolutions, ceremonial items, a technical placeholder, irrelevant/insufficient material, party categories, repeats and two instruction-injection attempts.

The model sees source ID, kind, text, and synthetic publisher where supplied. It never sees golden category/topic labels, split, repeat IDs or pair IDs. Matched Democratic/Republican notices contain identical text but distinct publisher labels, allowing a narrow party-symmetry check. Prompt, full request, corpus and response ID hashes document the exact experiment. No source changes or held-out-response tuning are performed during the run. The labels are single-author judgments, not an independent expert benchmark or proof of production accuracy.

The output schema allows an exact source ID, an allowlisted category, topic/quote pairs and a category quote. There is no narrative, tool invocation, owner stance or authoritative fact update. The client rejects extra fields, invented IDs/categories, duplicate topics and quotations absent from the supplied excerpt. An exact quote can still be semantically misclassified; held-out labels measure that separately. All accepted classifications remain unverified model suggestions.

## Predeclared gates

- All held-out outputs must validate.
- Held-out category accuracy at least 90%; micro topic precision at least 90% and recall at least 85%.
- Zero unsupported quotations.
- Both adversarial cases must match their expected category/topics exactly; an aggregate score cannot mask one attack failure.
- Matched party pairs must receive the same category/topic labels; a repeated notice must receive the same labels as its original. This checks classification consistency only, not novelty or event detection.

Abstentions, category errors, false-positive and missed topics, literal quote failures, costs, token counts and per-call latency are retained. A quality pass is not approval for routine operation. This tiny mostly synthetic sample cannot establish robustness on real website changes, amended legislation or rare topics.

## Spending and request controls

The run allows exactly the frozen 30 cases, one sequential request each, at most 1,024 completion tokens per request and a 480-second start-window bound. There are no automatic request retries. Content and schema UTF-8 byte bounds plus a wrapper allowance stay below a 32,000-token input bound and the verified endpoint context. Prompt/completion price ceilings are USD 0.10/0.40 per million tokens; the resulting token-cost upper bound is below the **USD 0.02 reservation per call**.

The workflow first commits and pushes a **USD 0.60 reservation for all 30 calls**. That is below the USD 1 per-run bound and USD 20 cumulative trial ceiling. Actual acknowledged costs replace reservations only in receipts; unknown billing retains the full per-call reservation and stops the run. Prior experiment liabilities are included in the trial total. A duplicated experiment ID cannot run again, including after a crash. A new trial needs deliberate review/versioning; nothing silently retries uncertain submissions.

Before completions, the worker verifies the remote key has a spending cap at most USD 20 and at least the reserved amount remaining. It checks current endpoint identity, context, supported parameters and pricing. These metadata calls do not invoke a model. No purchase, recharge, management API or extra key is used.

Requests pin qwen/qwen3-32b and deepinfra/fp8, disable provider fallbacks, require supported schema parameters, deny data collection and require a zero-retention endpoint. The only network destinations are three fixed OpenRouter API routes, over verified HTTPS with redirects rejected. Only the key check and completion route receive authentication. No model tools/plugins are enabled. The API response must identify DeepInfra and the exact model; unexpected routes, token bounds or costs stop the run. See [provider research](OPENROUTER_PROVIDER_RECOMMENDATION.md) for the policy sources and limits.

## Execution, durability and privacy

`.github/workflows/inference-evaluation.yml` is manual dispatch on main only; it has no schedule or pull-request trigger. It shares the existing state-writer concurrency group and checks out current main after acquiring that group. Offline tests/privacy checks run before reservation. The credential is available only to the execute step after the reservation push succeeds.

The completion worker writes a local receipt after each attempted response. A final workflow step preserves success or failure receipts. If runner loss prevents that commit, the earlier complete-batch reservation remains authoritative, suppressing a repeat and preserving conservative liability. SMTP and model calls are not treated as atomically committed side effects.

Only reviewed public or synthetic excerpts leave the worker. It receives no Obsidian notes or Gmail secrets. API labels, key values, raw error bodies, account balances, raw response IDs, reasoning traces and arbitrary model narratives are not logged or committed. Error codes are fixed and bounded. The public report stores only validated extractive classifications, safe token/cost/latency metadata, hashes, metrics and failure states. The normal privacy scanner runs before receipt publication. If it rejects a receipt, the precommitted reservation still stands.

The workflow preserves compact state in data/inference-evaluation-ledger.json and docs/evidence/inference-evaluation.json. These files are separate from the production index and contain no alert/new-activity records. No raw model-response archive is retained. API-reported usage cost is an acknowledged model charge, not a full account-billing reconciliation or a claim about credit-purchase fees.

Offline checks:

```sh
python -m unittest discover -s tests -p test_inference_eval.py -v
python -m civic_tracker.privacy
```

The execute CLI refuses non-manual, non-main GitHub Actions environments. Do not copy the key to a local file to bypass this boundary. A rerun stops at the existing reservation; retain the original report and investigate rather than clearing the ledger.
