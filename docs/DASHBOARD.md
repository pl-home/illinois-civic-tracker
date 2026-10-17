# Member activity dashboard

The owner expanded the basic browsing release on October 17, 2026: the homepage now covers Bradley Fritts, Li Arellano Jr., Darin LaHood, Dick Durbin and Tammy Duckworth. It shows recent member actions, recorded votes, committee websites and the next calendar month of posted committee meetings. This narrowly brings a public federal snapshot forward from the later roadmap; it does not deploy the broader federal monitoring pipeline or satisfy the remaining M0/M1 gates.

## Representative output and provenance

Start with `data/dashboard.json`, then `src/civic_tracker/dashboard.py` and `dashboard_collect.py`. The compact snapshot contains 97 selected events. The recent interval is September 18 through October 17, 2026. Older votes are labeled with their actual dates. Original filing, dated sponsor additions/removals and other-chamber roles remain distinct. Related bill actions do not establish a member's personal action. Federal cosponsor listings without a join date are undated context, never recent sponsorship events. Procedural, amendment, nomination and passage votes retain their motions; committee and floor votes remain separate. Illinois related source PDFs are grouped without turning source-document counts into vote counts.

Five October 2 Fritts sponsorship additions were reconfirmed against current official FTP bill-status XML. Other member activity comes from the selected read-only historical source collection, with its original observation times. State vote coverage ends May 31; the federal source collection reaches September 16 for LaHood and September 30 for the senators. These limits do not establish inactivity afterward. Snapshot compilation time is separate from source observation and event date.

The October 17 schedule check has 23 source receipts: two Illinois member committee profiles, fourteen Illinois committee schedule pages, one Senate feed and six House calendar weeks. It found no matching posted meetings from October 17 through November 17 inclusive, with no collection errors. This means none were found in those sources at that check, not that no meetings will occur. Federal hearings must match a monitored member's configured committee. Meeting times are displayed in America/Chicago, with source timezone assumptions retained.

## Witness slips

Illinois meeting detail pages supply bill/docket links when available. A submission link is displayed only after a bounded, read-only check finds a public create form with the required fields and an enabled submit control. Results, closed and login pages do not qualify. Verification uses public HTTPS ILGA hosts and never submits a form or authenticates. Same-day hearings have separate URL-keyed caches.

No eligible future hearing or open form was posted in this snapshot. Form checks have synthetic regression coverage; successful live future-hearing and open-form evidence remains a release gate. The dashboard must not promise that a slip remains open after its check time.

## Collection and rendering

`config/dashboard.json` controls members, committee URLs, 30 recent days and one calendar month ahead. The one-shot collector accepts explicit read-only normalized source files:

```sh
python -m civic_tracker.dashboard_collect --as-of 2026-10-17 --state-archive <state-normalized.json> --federal-archive <federal-normalized.json>
python -m civic_tracker.browse --output .local/site
```

Run from the repository root after installation. Imported facts are public and bounded; full archives, PDFs and HTML are not published. Main ILGA and public slip-host requests share the sequential ten-second gate. FTP is preferred. Collection errors remain visible instead of becoming empty success. Rendering makes no requests, uses no credentials, and escapes source text.

The Pages artifact contains exactly eight allowlisted files: `index.html`, `archive.html`, `dashboard.json`, `records.json`, `styles.css`, `app.js`, `dashboard.js` and `.nojekyll`. The current artifact is about 407 KB. Unexpected output files or symlinks cause the build to fail. The original 134-item export and its 24 ceremonial flags remain in the archive, with old item links redirected there. The homepage works without JavaScript; its small script warns about stale snapshots and preserves legacy links. There are no external scripts, analytics or browser-held API credentials.

## Verification and limits

The 92-test suite and privacy scan pass. Coverage includes date windows, empty-versus-failed schedules, committee scoping, source URLs, raw vote choices, unknown cosponsor dates, conservative slip controls, escaping, artifact isolation and archive invariants. Browser checks confirmed all five members, expandable votes, the archive and mobile layout without horizontal overflow.

This is a manually collected snapshot. The Pages workflow publishes committed data; it does not refresh legislative sources, run inference or send a digest. Automatic refresh stays off until production gates pass. Party-site inference remains a separately versioned manual evaluation and cannot supply official legislative facts.

The published implementation is `380611e`. Clean-runner [CI](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39039374030) and [Pages deployment](https://github.com/pl-home/illinois-civic-tracker/actions/runs/39039374009) passed; the live homepage was checked after deployment. See [compact dashboard validation](evidence/dashboard-validation.json).
