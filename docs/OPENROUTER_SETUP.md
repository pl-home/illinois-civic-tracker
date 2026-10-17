# OpenRouter setup and future inference plan

Status: **manual evaluation authorized, October 17, 2026**. The owner approved Qwen3 32B through DeepInfra and a small evaluation within USD 20. The manual evaluation client/workflow is implemented; no paid result has been claimed yet. Routine inference remains disabled and M1 remains deterministic. The later approval supersedes earlier planning-only statements below; see [INFERENCE_EVALUATION.md](INFERENCE_EVALUATION.md).

October 17 setup clarification: the owner may create the ordinary inference key and save OPENROUTER_API_KEY as a repository Actions secret now. Secret presence does not enable model calls. The public browsing page never receives or uses this secret. Tell the implementer only that setup is complete and the chosen trial cap, never the key value. Model/provider selection and explicit activation remain separate.

## What the hosted model would do

A later optional stage could suggest topic tags for otherwise untagged public material and classify meaningful county-party content changes. It would run after deterministic collection and comparison. It would not establish votes, sponsorship, filing dates, hearing times, source changes, or the owner's positions. Those remain source-backed facts.

The model runs at a hosted provider reached through OpenRouter. The owner does not download or host model weights. Open-weight describes availability of the model weights; hosted inference can still cost money.

## Setup guidance

1. Sign in to the existing OpenRouter account and open [API keys](https://openrouter.ai/settings/keys). Create a separate **ordinary inference key** named Civic Advocacy. The tracker does not need a management key or access to other provider accounts. The official [quickstart](https://openrouter.ai/docs/cookbook/get-started/quickstart) links this key page.
2. Give that key a small owner-chosen spending limit, with a monthly reset if desired. An initial USD 1 trial limit is an example, not an approved project budget. Record the limit/reset and any expiry privately. OpenRouter documents the [key limit and reset settings](https://openrouter.ai/docs/api/api-reference/api-keys/create-a-new-api-key). No credit purchase or recharge is authorized. The later October 17 instruction authorizes the bounded evaluation requests only.
3. Leave prompt/completion logging and input/output sharing disabled. Review the account privacy controls and the chosen provider's policy. OpenRouter and the upstream host are separate data handlers; review both. See [data collection](https://openrouter.ai/docs/guides/privacy/data-collection).
4. When activation is explicitly requested later, save the inference key as the GitHub Actions repository secret **OPENROUTER_API_KEY** in [repository secrets](https://github.com/pl-home/illinois-civic-tracker/settings/secrets/actions). Never paste it into chat, Obsidian, a source file, an issue, or a workflow log. No key is needed to continue M0 now.
5. Before the first model call, select the exact model, review and pin an eligible provider, set a budget, and run the evaluation described below. Merely creating a secret must not activate inference. A later implementation and explicit enablement are still required.

## Candidate to evaluate

**qwen/qwen3-32b** is an initial candidate, not a final selection or a claim of best performance. Its developer publishes [model weights](https://huggingface.co/Qwen/Qwen3-32B) under [Apache-2.0](https://huggingface.co/Qwen/Qwen3-32B/blob/main/LICENSE), and OpenRouter lists a [hosted model entry](https://openrouter.ai/qwen/qwen3-32b). Those establish open-weight availability and a hosted route; they do not establish accuracy on Illinois legislative material.

Recheck the exact model ID, pricing, provider availability and structured-output support at activation. Do not use a generic automatic model router. A free variant may have different availability and policies; free access is not assumed. No closed-weight model fallback is planned.

## Proposed integration contract

The record is config/inference-plan.json. It keeps enabled=false for routine operation and evaluation_enabled=true for the owner-authorized manual evaluation. The approved model/provider and USD 20 trial ceiling are consumed only by that manual evaluator.

Future routing should restrict requests to explicitly approved providers for the chosen open-weight model. Require supported JSON-schema output, data_collection=deny, and no provider fallback outside the approved selection. If no eligible endpoint remains, skip inference and report that health state. Never silently relax privacy or model restrictions. OpenRouter documents these controls in [provider routing](https://openrouter.ai/docs/guides/routing/provider-selection) and [structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs). A no-collection setting is not a promise about every form of operational metadata or a substitute for reading provider terms.

Only bounded excerpts from already-public source material should leave the collector. Private notes, positions, correspondence, account identifiers and secrets are excluded. Redact contact details from excerpts unless an independently approved use requires them. Treat all source text as untrusted input; embedded instructions cannot authorize tools, network access, contact, purchases or data disclosure.

Require a small schema with an allowlisted topic/category, supplied source ID, supporting excerpt, and uncertainty/review status. Verify that every cited excerpt occurs in the submitted text. Reject invented IDs, URLs, unsupported categories and malformed output. Model suggestions stay labeled and cannot overwrite authoritative source fields.

Keep source-event time, retrieval time and inference time distinct. Model or prompt changes must not make old events look new. Cache by normalized content hash plus model, provider, prompt and taxonomy versions. Apply per-request token limits, a per-run request bound, a durable spending ledger and the remote key limit. Avoid automatically retrying requests whose billing outcome is uncertain.

If inference is unavailable or invalid, collection, indexing and source health still proceed. Untagged material remains available for review. The deterministic weekly digest must not depend on a model answering successfully.

## Evaluation before activation

Build a reviewed sample that includes all priority topics, substantive resolutions, ceremonial material, shell bills, irrelevant posts, both county parties, repeated events and embedded instruction attempts. Separate examples used to develop the prompt from held-out evaluation examples. Measure topic/category precision and recall, unsupported statements, abstentions, cost and latency; inspect errors rather than trusting the model's confidence score.

The owner approved the USD 20 trial ceiling and Qwen3 32B / DeepInfra combination on October 17. The bounded evaluation and failure-path checks precede any separate decision to enable routine inference. Results are recorded in the evaluation evidence file, not assumed from credential setup.

## October 17 credential and trial update

The owner reports the repository secret is configured and sets a USD 20 trial cap. This supersedes the earlier example-only USD 1 amount. It does not approve monthly replenishment or activate calls. The [model/provider recommendation](OPENROUTER_PROVIDER_RECOMMENDATION.md) proposes Qwen3 32B via DeepInfra, with current endpoint metadata and a reviewable request policy. Model/provider approval and the evaluation implementation are now complete for the bounded manual test. Routine activation remains separate.
