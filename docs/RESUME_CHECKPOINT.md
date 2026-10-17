# Current checkpoint

Updated October 17, 2026 after the owner brought basic browsing into the first release.

- The [public browsing page](https://pl-home.github.io/illinois-civic-tracker/) is live. It renders the reviewed 134-item Fritts sponsorship export, with 24 ceremonial entries hidden by default. Search, measure-type filtering, expandable source fields, item permalinks and a compact public JSON download work. It is a historical preview, not a current-activity feed.
- See BROWSING_PAGE.md and evidence/browsing-validation.json for architecture, provenance, validation and limits. Exact Fritts roles, original filing, topics, votes, Arellano and other source coverage are not loaded. This does not satisfy the full M1 index acceptance gate.
- The 57-test suite passed locally and in clean-runner CI. Pages build/deploy jobs passed. Live UI verified 110 default and 134 show-ceremonial records. Mobile content had no horizontal overflow.
- OpenRouter: the owner reports OPENROUTER_API_KEY saved as an Actions secret and sets a USD 20 trial ceiling. No key value was read, model call made, monthly reset approved or inference client enabled. OPENROUTER_PROVIDER_RECOMMENDATION.md proposes Qwen3 32B via DeepInfra with a restricted provider/structured-output/privacy policy. Model/provider approval and the optional evaluation implementation are pending.
- Earlier source verification remains: 2,439/2,525 legacy vote comparison keys covered (96.594%), with 86 retained source-detail/label/date cases; five nonempty historical hearing pages / 103 posted items parsed; 20 bill identities and histories cross-checked. These are verification evidence, not production imports.
- M0_FINDINGS.md retains production release gates. Recent metadata observations have been preserved; multi-day source timing and future hearing behavior still need review, and post-veto CSV cadence is a dated follow-up.
- Old Codex and Windows schedules remain stopped. Only the bounded M0 observer is scheduled. Pages publishes on repository pushes; it does not collect sources, send email, access secrets or invoke a model. No nightly product collection or digest schedule is enabled.

Next: build/review the compact production index and source adapters while closing the documented gates. Keep historical imports separate from new activity. The optional hosted-inference evaluation is a separate later task. Review README.md, BROWSING_PAGE.md, M0_FINDINGS.md and OPENROUTER_PROVIDER_RECOMMENDATION.md before resuming.
