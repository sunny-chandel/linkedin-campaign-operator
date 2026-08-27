---
name: linkedin-engagement-execution
description: Execute canonical LinkedIn engagement bursts under rolling 24-hour quotas, relationship-only outbound DM rules, idempotent evidence, and action-debt accounting. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.1"
---

# LinkedIn engagement execution

Inherit consent and execute the burst leased by the parent. Calculate output with `scripts/rolling_output.py`; never trust calendar-day or checkpoint counters.

- Target 160 counted actions and cap at 200 in the preceding 24 hours.
- Genuine direct inbound replies are outside the cap.
- A burst contains one to ten currently eligible canonical actions.
- Proactive DMs require an existing connection plus stored prior-interaction evidence.
- Verify the external result before recording it. Do not retry an ambiguous mutation.

Use `scripts/build_burst.py` to construct a task. After execution, record each confirmed action in `interaction-log.jsonl`, transition the candidate lifecycle, update source yield and relationship evidence, then recalculate `operational-output.json`. Return rolling count, debt, capacity, inbound count, and candidate outcomes.
