# Saved-evidence verification — 2026-10-28

This four-file package verifies disclosed tool-observation pilot metadata only.
It does not contain private native code/state, tool or judgment bodies, cues,
features, actor IDs, or a complete native execution replay.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B verify.py
```

The verifier checks exact uppercase MANIFEST.json, the complete four-file
inventory, every other file's SHA256 and byte size, the strict evidence schema,
context/operation bindings and disclosed arithmetic. It performs no native
operation and generates no new AI judgment. These checks cannot reconstruct
undisclosed operations or independently prove exported claims. Hashes identify
local records; they are not external signatures or hardware attestation.

Actual pilot results and the two synthetic engineering rounds are separate.
The initial initialize used revision 1; the reviewed original-input-return
correction used revision 2 before semantic indexing/continuation. No run was
discarded or restarted. A pre-index diagnostic had a prospective plan but no
separate pre-call cue-span/review artifact; it was not a scored continuation.
The continuation cue choices use hash-bound pre-call span/review records.
One tool event and its AI interpretation are not two independent experiences.
The new changed-copy judgment was saved in native LRE but was not indexed or
subsequently recalled; this does not establish recurrent learning.
No human/private conversation was fetched or used. The previous delayed study
is separate and unchanged. Provider/model metadata is unverified and null.

The existing project LICENSE applies; this package grants no new license to
private native dependencies. Read the dated JA/EN study for all limits.
