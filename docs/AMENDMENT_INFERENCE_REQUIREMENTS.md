# Future amendment-aware synopses and rewrite detection

Owner requirement recorded October 17, 2026. This is deferred M2/product work, not runtime activation. It adds a use for inference beyond topic tagging: explaining how an amended bill's policy content changed. Routine inference remains disabled; existing evaluation corpora and results stay frozen.

## Required distinction

“Replaces everything after the enacting clause” is a **comparison trigger**, not proof of an unrelated replacement. Classify policy continuity from the actual before/after content. Keep an initial placeholder/shell-candidate flag separate from a later material subject-change finding. A substantive bill can also receive an unrelated replacement without ever carrying a technical short title.

For a triggered comparison, distinguish:

- Same-subject revision: the broad policy purpose continues, even when provisions change substantially.
- Material subject change: the operative content moves to an unrelated or materially different policy purpose.
- Insufficient evidence: available versions, amendment status or text do not support a reliable comparison.

These are provisional product labels, not implemented classifier outputs. Describe changes in the text; do not claim knowledge of legislators' motives. Do not infer that a replacement is controversial, deceptive or improper from boilerplate, timing or subject matter alone.

## SB2427: continuity example and false-positive regression

[GA104 SB2427 official bill page](https://ilga.gov/legislation/BillStatus?DocNum=2427&GAID=18&DocTypeID=SB&LegId=162470&SessionID=114).

The owner supplied a saved official bill-status page and identified this as a case that preserves the original policy purpose. Review of its introduced and amendment synopses supports a common subject: school policies for student wireless communication devices. Three displayed replacement synopses are Senate Committee Amendment 1, House Committee Amendment 1 and House Floor Amendment 4. The saved action history records their adoption; House Floor Amendments 2 and 3 were tabled. Filed, recommended and adopted amendments must remain distinct.

The expected future result is **policy continuity with substantive revisions**, rather than an unrelated replacement solely because the replacement phrase appears. The synopses describe meaningful changes, including the implementation school year, covered schools, accommodations, permitted enforcement and liability provisions. A continuity finding must not imply that these changes are minor or that the amended bill is identical to the introduced version.

This is an owner-selected, already-reviewed development/regression example, not fresh held-out evaluation data. It is not yet a full-text legal comparison or a scored model benchmark. Retain official version/amendment links and compact provenance when building the fixture; the supplied saved-page archive is not copied into the public repository. The existing vision's HB0742 and HB2137 are candidate contrast cases, to be independently checked and annotated before use as positive examples.

## Website synopsis behavior

Eventually show a short, plain-language synopsis tied to an explicit version and date, with official source links. Separate the official synopsis from an AI-assisted explanation. Summarize the introduced bill and the latest adopted/operative version; show pending amendments separately and never fold tabled or merely filed language into the current summary. Enrolled/enacted text and effective-date status must be explicit when available.

For a material subject-change candidate, identify what the bill originally addressed, what the replacement addresses and which amendment changes that relationship. For a same-subject revision, explain the important changes in obligations, affected people, exceptions, enforcement, funding or deadlines. Keep the original bill number/title visible even when the short title no longer describes its substance. Re-tag topics from the relevant version; never rely on the old short title alone.

## Evidence and activation gates

Use deterministic discovery of versions, amendment identifiers, status and dates. Compare adjacent adopted versions as well as introduced versus latest operative text; a chain can conceal a larger cumulative change. Official synopses can screen candidates, but truncated/ambiguous synopses require full-text verification or an insufficient-evidence result. Shared statute references or broad topic labels alone do not establish continuity.

Inference may propose a synopsis and semantic comparison. Every factual change must link to the exact official version and supporting source spans; assemble quoted evidence deterministically where practical. Treat source text as untrusted data and preserve an explicit abstention path. Keep source facts separate from the model's interpretation, and offer a reviewable version comparison for material-change findings.

Before activation, evaluate reviewed continuity cases (including SB2427), genuine subject replacements, significant same-subject changes, tabled/pending amendments and insufficient-evidence cases. Measure false unrelated-rewrite alarms as well as missed replacements. Preserve temporal/version errors as failures, not just classification errors. Use a separately versioned evaluation within the approved spending controls; this roadmap note authorizes no additional calls, public alerts or automated outreach.
