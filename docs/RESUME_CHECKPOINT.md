# Current checkpoint

Updated October 16, 2026 after resuming at the owner's request.

- Follow-up vote audit is implemented and tested: 129 of the original 215 gaps resolved; 86 retained source-detail/label/date cases remain. Coverage is 2,439/2,525 original comparison keys (96.594%), not a count of physical votes.
- Hearing fallback parses five nonempty historical pages and 103 posted items. Twenty distinct bill identities and committee histories match FTP XML; five hearing times match public committee history. Historical witness results are not active submission links. The disallowed range API was not called.
- Local test suite: 52 passing tests. Updated clean-runner validation is recorded separately after publication.
- OpenRouter setup guidance and a disabled planning record are saved. Plan inference now; enable later. No key was read, no model call was made, and no inference workflow is enabled.
- Existing source and release limits are in M0_FINDINGS.md. Multi-day timing and the post-veto CSV cadence check remain pending. Review retained vote gaps and future hearing forms before M1 deployment.
- Old Codex and Windows schedules remain stopped. Only the previously authorized bounded M0 metadata observer is scheduled.

Start with M0_FINDINGS.md, OPENROUTER_SETUP.md and ARCHITECTURE.md. The earlier draft state is superseded by the tested source modules and follow-up evidence.
