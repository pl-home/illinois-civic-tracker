# Third-party adaptations

The owner authorized direct reuse with disclosure. This register distinguishes
adapted source from independently implemented ideas; it does not declare an
upstream project's facts or architecture validated. Full immutable revisions
and source paths are in [the provenance register](docs/provenance/stage-a.json).

## Hawaii Appleseed Tracker — Stage A

Source: [Hawaii-Appleseed/Tracker](https://github.com/Hawaii-Appleseed/Tracker),
reviewed revision `b244e82`, `tracker/legislative/feeds.py`, especially
`_feed_xml` and `_write_if_changed`. Adapted in
`src/civic_tracker/change_feed.py`: static Atom envelope, timestamps taken from
the change log rather than the build clock, and byte comparison before writing.
Our source-qualified IDs, event revisions, validation gate, JSON payload,
baseline behavior and HTML view are separate implementations.

The reviewed repository did not identify a license in its repository metadata;
the reviewed functions contain no separate copyright/license header. Reuse here
relies on the owner's explicit permission, not an inferred MIT/public-domain
license. Upstream authorship remains with Hawaii-Appleseed/Tracker contributors.
No upstream code has been relicensed by this notice.

`tracker/legislative/db.py`'s durable change-log design informed the independently
written `changes.py`; no database implementation was copied. Its destructive
three-year pruning and blanket title-only suppression were not adopted.

## Independently implemented review principles

- [ShipCreekGroup/alaska-legislative-data](https://github.com/ShipCreekGroup/alaska-legislative-data),
  reviewed `33e044c`, MIT: composite identities, duplicate/reference integrity
  and conservative removal checks informed our QA. No source text was copied.
- [RealRyanNichols/RepWatchr](https://github.com/RealRyanNichols/RepWatchr),
  reviewed `4d40d29`: explicit withheld reasons and common publication gates
  informed our independently written gate. No source text was copied. A status
  string or an official-looking URL alone is insufficient for our adapters.

Other reviewed projects remain candidates in the implementation plan, not
dependencies or claims of incorporated code. There is no new package/service
dependency for Stage A. Acceptance tests: `tests/test_changes.py`,
`tests/test_browse.py` and `tests/test_error_journal.py`.

## Stage C provenance

The party-page allowlist and extraction/suppression principles were reviewed
against the owner's earlier watcher. `parties.py` is independently implemented;
the old runner, raw archives and local-model review are not copied. The shared
change feed continues to use the Hawaii Appleseed adaptation disclosed above.
Deterministic relevance, symmetric category rules and explicit held-for-review
reasons also apply the already disclosed RepWatchr review principles without
copying additional upstream source. See `docs/PARTY_MONITORING.md` and
`tests/test_parties.py`. Party-published text retains publisher attribution;
no content license or independent verification is inferred.
