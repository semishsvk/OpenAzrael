# OpenAzrael KG-001 gate status

`tools/kg001_status_v112.py` and `data/tests/kg001_status_v112.json` are the current
evidence-driven gate summary. The recorded tested source `6528d438ab2b14d344fb0e19f83ba5d5e699cd60` has
**G00-G09 PASS** and **G10 PENDING_MANUAL_USER**. Overall release status is
**AWAITING_RUNTIME_OR_MANUAL** and final_tag_allowed is false.

Final graphics/icon integration is included in the tested commit; Windows export and smoke checks are PASS. G10 remains manual pending.

The older `tools/kg001_status_v111.py` and regenerated `kg001_status_v111.json`
remain a legacy status view. Its source-only READY/SOURCE_* values and
PRE_RUNTIME_READY summary are not the current release-gate decision. Runtime
inputs in that view are now updated from the recorded PASS evidence.

Only literal PASS for every G00-G10 permits `demo-known-good-001`. G10 must be
completed by the actual manual checklist and is never inferred from automation.
