# Bounded execution guide

Revision 14 — October 23, 2026. Written for an implementer with limited context.
Use one packet at a time. Do not read every raw report or old conversation.

## Start every task

1. Read `AGENTS.md`, [CURRENT_STATUS.md](CURRENT_STATUS.md), and the chosen [WORK_PACKETS.md](WORK_PACKETS.md) card. Read only its referenced guide/code/tests next.
2. Inspect `git status --short`, `git log -3 --oneline`, `git worktree list`, then `git fetch origin main` and compare `HEAD` with `origin/main`. Fetching is read-only; never reset, stash, switch or overwrite someone else's work to make progress.
3. Use the checkout identified by the private workspace handoff. Do not assume the primary checkout is current: it contains paused work. If dirty data is reported, compare actual normalized bytes with Git; do not discard it. Commit only your named files. Unexplained differences require investigation, not blanket `git add`.
4. Run the safe baseline below. Record the starting commit, checks, known failing source receipts and exact task scope. A preexisting source failure is not a failed offline test, and a successful offline test is not source recovery.
5. Check the packet's owner/evidence gates. A future roadmap entry is not authorization. This handoff authorizes no delivery, PDF retry, paid evaluation, schedule expansion or private-data migration.

## Safe local commands

Use Python 3.11 in the repository root, with the package already installed. A
fresh environment can install with `python -m pip install -e .` (dependency
download only). On Windows use `py -3.11` if `python` selects another interpreter.
Source imports without installation can use `$env:PYTHONPATH = Join-Path (Get-Location) 'src'`
in PowerShell; `$env:PYTHONUTF8 = '1'` avoids console encoding failures.

```sh
python scripts/check_handoff.py
python -m civic_tracker.privacy
python -m unittest discover -s tests -v
python -m civic_tracker.browse --output .local/handoff-site
python -m civic_tracker.digest preview --output .local/handoff-digest
git diff --check
```

These build/check commands use existing public files; they do not collect sources,
send email or invoke a model. Use dedicated ignored output directories, never a
vault or source directory. If an output ownership/size/privacy gate fails, fix
the cause; do not bypass the gate. Test output can be large: keep full logs in
ignored scratch and report failing test names plus a short traceback, not entire
data structures. Use absolute local links only in private handoffs, never public docs.

The handoff checker is read-only and standard-library only. `docs/handoff.json`
indexes all public Markdown and packet dependencies. It is a navigation/checking
aid, not a scheduler, feature flag or authorization record. New docs/packets must
be added there. Do not edit expected policy or gates simply to get a green check.

## Commands that do more than their names suggest

| Entry point | Actual effect / restriction |
| --- | --- |
| `daily gate --manual` | Bypasses the normal time/date gate; not a dry run. Do not dispatch it for an offline check |
| `daily run`, `dashboard_collect`, recovery commands | Network collection and collector-owned state changes; use only for the selected approved source task |
| `changes collect` | Offline but mutates accepted facts/ledger/quality; not a read-only report |
| `media prepare` | Fetches news/communications and can reserve paid inference liability |
| `media execute` | Can make paid model requests; never use to refresh a page or test a heading |
| `media refresh-communications` / `media.yml` mode `communications` | Public first-party collection without model calls, but still network/state changes; verify selected mode and unchanged financial files |
| `parties collect` | Bounded network collection/state changes, no model; existing daily runner owns routine use |
| `digest preview`, `browse` | Read-only source inputs, writes only allowlisted ignored/public artifacts; does not mark anything delivered |
| M0 mail/model/PDF/health workflows | Manual diagnostic/trial tools, not routine repair commands. Availability in GitHub is not permission to run them |

Do not print/read secret values to verify configuration. Congress.gov workflow
selection prefers `CONGRESSGOV_API`, falling back to `CONGRESS_API_KEY`.
`OPENROUTER_API_KEY` is only for the approved media step. Gmail's `GMAIL_USER`,
`GMAIL_APP_PASSWORD`, `DIGEST_TO` names document a future transport boundary;
never expose them to preview/build/PR steps. No private Obsidian folder is needed
for ordinary public code work.

## Implementation loop and stopping rules

Change one responsibility in the packet's allowed files. Add a meaningful
regression only where behavior warrants it; do not test an implementation by
restating its literals. Run its targeted checks, then the existing suite/privacy/
artifact gates once. Keep source dates and evidence labels intact. If you discover
an unrelated defect, record it as a follow-up instead of silently enlarging scope.

Stop dependent work and request the missing decision/evidence when:

- owner preview review, controlled-send authorization, a genuine future form or verified successor/service identity is required;
- a task would change TLS/host limits, budget accounting, source/financial schemas, raw vote interpretation or uncertain-send recovery without an independently reviewed design;
- the same source is blocked or unavailable: preserve last-good data/false-open-slip protection; never bypass access restrictions or invent source dates;
- you cannot explain a failing test or a material delta after one bounded investigation. Supply failing name, source/date, safe error category and smallest unresolved question. Do not repeat paid calls for more detail.

Routine small packets can be executed by a smaller model. Delivery side effects,
budget/ledger concurrency, security and service identity changes need a senior
programmer or independent qualified review. No model is allowed to certify its
own missing evidence as passed.

## Publication and completion receipt

Only publish when the current task authorizes publication. Check current main
again, privacy and noreply commit identity; commit explicit owned paths. Prefer
the existing CI/Pages workflow for display/docs changes. Never run the daily
collector just to publish files. Source-only tasks reuse the existing shared lock
and correct manual workflow mode; do not create a second scheduler.

Check the *actual deployment step*, not only a green job: stale-artifact guards
can skip deployment. A green daily job can skip every collection step. Compare
the deployed manifest/receipt against the intended revision before claiming
freshness. A source's old `ok` status stays old until newly collected.

At completion record: task ID, commit, files/responsibility, exact checks and
results, source date versus observation time, deployment/run links if applicable,
remaining limits, bytes, model calls/cost (zero when none), and unchanged protected
ledgers. Update current status/plan/index and private mirrors together. Preserve
dated receipts and superseded planning copies; do not rewrite historical outcomes.

If interrupted, leave one private continuation note with actual checkout/commit,
dirty owned files, finished checks, next command, unresolved gates and any running
job/lock. A new implementer should resume that exact step rather than restart
collection or consume credentials.
