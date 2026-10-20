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
production gates. Results and final cost will be recorded below after execution.
