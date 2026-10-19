# Bounded troubleshooting journal

Start with [`data/error-journal.json`](../data/error-journal.json). It is a compact
public index of failures and recoveries, not a dump of exception messages or model
responses. Existing collection reports and financial ledgers remain authoritative.

## What is recorded

Each incident has a stable identity, collector, sanitized source label, fixed error
code and failure stage, first/last observation, occurrence count, open/resolved
state, run identifier, and a reference to a known report or historical Git commit.
Events record opening, recurrence, recovery and reopening. Only a complete healthy
observation resolves failures in its scope; partial collection does not. Replaying
the same dated receipt does not count as another failure. Older observations are
ignored and counted. A later successful source collection does not retroactively
make a failed PDF evaluation pass.

Future model receipts include only allowlisted diagnostics: response identifier,
token counts, provider/model match booleans, finish reason, JSON/content/status
shape, missing expected fields, unexpected field count, bounded HTTP status/error
category, validation stage, and available source/native/prompt/config fingerprints.
Known status values are normalized; exact `extracted` acceptance is distinguished
from capitalization/whitespace variants. Unknown status strings are hashed. No raw
status, model answer, reasoning text, prompt, PDF, exception message, provider
message, request headers, authenticated URL or credentials are retained here.

For rejected committee responses, a separate diagnostic checks whether the supplied
evidence would match the deterministic reference *if* the status gate passed. This
never changes acceptance, publishes an answer, or substitutes for the original
validation. It helps distinguish a status-format failure from an evidence failure.

The original six-case committee test retained response IDs, token counts and
failure codes, but not the original status values or rejected answers. Its journal
entries explicitly say `diagnostics_available: false` and `model_status:
not-captured`. Those details cannot be reconstructed; no paid replay was made to
populate the journal. See [the evaluation](COMMITTEE_ROLLCALL_EVALUATION.md).

## Storage and privacy boundaries

- Current file: at most **96 KiB**, **64 incidents**, **128 recent events**, **128
  receipt IDs**, **128 scope watermarks**, and **32 run receipts**.
- Recent events and resolved incidents expire after **90 days**. An unresolved
  incident survives the age cutoff, subject to the count and byte caps.
- Eviction prefers resolved incidents, then the oldest open incidents. Counters
  expose eviction, including lost open incidents. This is bounded operational
  history, not a complete audit trail.
- Git retains prior versions: the live file cap does not cap total Git history.
  Long-term repository growth still needs measurement before broader deployment.
- Unknown source labels are hashed; approved URL labels omit user information,
  query strings and fragments. Only known safe public paths are retained.
- Strict persisted-schema validation rejects unexpected fields. A malformed
  existing journal is preserved and fails closed. Malformed source reports create
  sanitized `journal-input` incidents while other reports continue to be read.
- The final serialization checks known secret environment values when present.
  The normal repository privacy scanner remains an additional independent check;
  public 40-character Git commits are exempt only in the exact `commit` field.

The one-time bootstrap imports at most 40 report-affecting Git revisions from the
last 90 days. It uses source receipt dates when available and commit dates as a
fallback, with historical commit references. This is not every past Actions run;
the imported history identifiers are not original workflow run IDs.

## Workflow operation

Daily, federal, Illinois recovery, media, OpenRouter health, manual PDF and manual
roll-call workflows finalize the journal with Python's standard library. No new
collector schedule, API request or model call is introduced. Old read-only M0
probes remain inspectable in Actions rather than being unified into this journal.

The finalizer runs after ordinary handled step failures. It first writes a safe
journal, then independently attempts a **seven-day journal-only artifact backup**
and a **journal-only Git commit/push**. Backup failure cannot prevent Git persistence.
If capture fails, neither later step republishes a stale/invalid journal. Workflow
publication checks use the final journal commit SHA so its extra commit does not
make the already-built website artifact appear outdated. The journal itself is
not added to the Pages snapshot.

Runner loss, checkout failure, forced cancellation or failure inside the finalizer
can still prevent persistence. A finalizer cannot log its own failed push into that
same failed push; use the backup artifact and Actions logs. The seven-day backup
is not a permanent archive. Known step outcome enums are passed individually;
whole job contexts, environment variables and secret values are never dumped.

Read or update locally without collection or paid inference:

```sh
python src/civic_tracker/error_journal.py --workflow journal --job-status success
python -m civic_tracker.privacy
python -m unittest discover -s tests -v
```

Only use `--bootstrap` once when creating a journal; it reads local Git history.
Do not delete/reset the journal to clear an error. Correct the failure and retain
the recovery. Source and cost ledgers must never be reset by troubleshooting.

The manual `error-journal.yml` workflow has a controlled `failure_probe` input.
With `true`, it exits before finalization without using any source/model service;
with `false`, it exercises recovery. It has no schedule or API secrets. Regression
tests cover recurrence, recovery, bounded retention, malformed input, credential
redaction, missing historical diagnostics, and receipt-cache rollover.
