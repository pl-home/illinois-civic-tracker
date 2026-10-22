# Hosted inference selection and original recommendation

> Documentation review: October 22, 2026. Historical evidence/setup; not current activation instructions. Start with [current status](CURRENT_STATUS.md) and the [execution guide](EXECUTION_GUIDE.md). Failed results and original evidence remain unchanged.

Reviewed October 17, 2026. The owner subsequently approved this model/provider for one bounded manual evaluation. Routine inference remains disabled. The original selection rationale follows; current execution controls are in [INFERENCE_EVALUATION.md](INFERENCE_EVALUATION.md). The owner reports OPENROUTER_API_KEY saved as an Actions secret and approves a **USD 20 trial ceiling**. No monthly reset, automatic replenishment, or production spending is assumed. The original provider research used no credential or model call. The later [authorized evaluation](INFERENCE_EVALUATION_RESULTS.md) used the Actions secret inside its worker, completed 30 calls for USD 0.00145256, and failed its mandatory adversarial gate. No credential value was copied out or published.

## Proposed model and host

Start the later evaluation with **qwen/qwen3-32b**, served by **DeepInfra**, pinning endpoint slug **deepinfra/fp8**. The developer publishes the [weights and Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-32B/blob/main/LICENSE). It is hosted through OpenRouter; there is no local model installation or separate DeepInfra account/key needed for this route.

The [public endpoint metadata](https://openrouter.ai/api/v1/models/qwen/qwen3-32b/endpoints) was read without authentication. These are the observed options, not price guarantees:

| Provider endpoint | Input / million tokens | Output / million tokens | Relevant advertised parameters |
| --- | --- | --- | --- |
| deepinfra/fp8 | USD 0.08 | USD 0.28 | structured_outputs, response_format, max_tokens |
| tenstorrent/fp8 | USD 0.14 | USD 0.40 | Structured-output/response-format support not listed |
| siliconflow/fp8 | USD 0.14 | USD 0.57 | structured_outputs, response_format, max_tokens |

The DeepInfra endpoint advertises a 40,960-token context limit; do not substitute the larger model-wide maximum displayed elsewhere. At the observed token rates, 5,000 input plus 500 output tokens would cost about USD 0.00054 in model tokens, before additional reasoning tokens or account fees. This arithmetic is not an actual billed request or an evaluation result. The cap remains USD 20 regardless of this estimate.

DeepInfra is a suitable first candidate because it advertises the required output format at low token rates, and has a published inference-content policy. This is not a claim that it is the best available model or that it meets the project's quality threshold. Test held-out legislative and party examples before adopting it.

## Privacy and routing

[OpenRouter's provider directory](https://openrouter.ai/providers) lists DeepInfra as no training / zero retention. [DeepInfra's own inference privacy page](https://docs.deepinfra.com/account/data-privacy) says input/output content is held in memory for inference and not logged or used for training; it distinguishes metadata logging, bulk inference, and other model exceptions. OpenRouter remains a separate service with its own controls. Keep account input/output logging and sharing disabled. Public excerpts only; private Obsidian notes and owner correspondence remain excluded.

For the future single-request implementation, propose:

```json
{
  "model": "qwen/qwen3-32b",
  "provider": {
    "only": ["deepinfra/fp8"],
    "allow_fallbacks": false,
    "require_parameters": true,
    "data_collection": "deny",
    "zdr": true
  }
}
```

These fields follow the [provider-routing guide](https://openrouter.ai/docs/guides/routing/provider-selection) and [zero-retention filter](https://openrouter.ai/docs/guides/features/zdr). Also require a strict [JSON schema](https://openrouter.ai/docs/guides/features/structured-outputs), bounded completion tokens, no tools, and a versioned prompt. An unavailable/ineligible endpoint is a skipped inference health result; do not relax the provider or privacy policy. Enforce the trial ceiling with a durable ledger and remote key cap before enabling any requests; do not use a resettable monthly budget as the trial ledger.

## Original activation checklist (superseded by the later approval)

1. Owner reviews this proposed model/provider. The planning config keeps approved_model null, approved_providers empty and enabled false.
2. Implement the separate optional evaluation client, held-out public examples, schema/evidence validation and budget/failure controls described in OPENROUTER_SETUP.md. No inference client or workflow exists yet.
3. Recheck endpoint availability, policy and pricing at activation. Run a small bounded evaluation only after explicit activation, then review its precision, unsupported statements, abstentions and actual cost.
4. Keep deterministic collection and the basic website operational independently of any later model call.

The owner has completed credential setup as reported; adding another key or choosing a model in OpenRouter's chat interface is unnecessary. Request-level provider/model settings belong in the future tracker implementation. Saving the existing secret does not trigger the page or any workflow to use it.
