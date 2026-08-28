---
name: linkedin-runtime-repair
description: Restore access to needed apps and tools while saving progress and continuing the same campaign task without repeats. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.11"
---

# LinkedIn runtime repair

Inherit consent and the leased task checkpoint. First verify whether the external action already occurred. Persist the failure and checkpoint with `scripts/repair_controller.py`.

Attempt recovery in order: current-agent computer use; reopen, refresh, or rebind the affected application; rerun only the failed pre-flight component; capability verification; resume the original lease.

Persist the repair request, continue unaffected work, and retry from the saved trigger. External mutations remain assigned to the official-API executor. Return structured repair result, verification evidence, resumed task ID, and retry trigger.
