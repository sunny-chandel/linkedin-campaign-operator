---
name: linkedin-runtime-repair
description: Restore access to needed apps and tools while saving progress and continuing the same campaign task without repeats. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.28"
---

# LinkedIn runtime repair

Inherit the saved task checkpoint. First verify whether the previous local stage or connected-service request already completed. Save the failure and checkpoint with `scripts/repair_controller.py`.

Attempt recovery in order: use the current app-control capability, reopen or rebind the affected application, rerun only the failed check, verify the repaired capability, and resume the saved task.

Continue unaffected local work while a capability is unavailable. Return the repair result, verification evidence, resumed task ID, and next retry trigger. Never repeat an account request while its earlier result is unclear.
