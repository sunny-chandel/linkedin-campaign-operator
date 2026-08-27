---
name: linkedin-runtime-repair
description: Recover unhealthy Chrome, Claude Design, upload, computer-use, Codex, or campaign runtime capabilities while preserving checkpoints and resuming the original task. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.1"
---

# LinkedIn runtime repair

Inherit consent and the leased task checkpoint. First verify whether the external action already occurred. Persist the failure and checkpoint with `scripts/repair_controller.py`.

Attempt recovery in order: current-agent computer use; reopen, refresh, or rebind the affected application; rerun only the failed pre-flight component; `codex doctor --json`; scoped ephemeral Codex repair; capability verification; resume the original lease.

Codex repair may recover an application or session, repair deterministic campaign state, or reinstall the already-approved plugin version. It may not modify skill instructions, source code, Git history, or publish LinkedIn content. If Codex is unavailable, persist the request, continue unaffected work, and retry automatically. Return structured repair result, verification evidence, resumed task ID, and retry trigger.
