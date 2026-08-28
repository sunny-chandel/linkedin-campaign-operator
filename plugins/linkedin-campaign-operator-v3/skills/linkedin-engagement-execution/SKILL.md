---
name: linkedin-engagement-execution
description: Prepare canonical LinkedIn engagement bursts under rolling 24-hour quotas, official-API coverage, idempotent evidence, and action-debt accounting. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.8"
---

# LinkedIn engagement execution

Inherit the campaign configuration and prepare the burst leased by the parent. Calculate output from canonical evidence with `scripts/rolling_output.py`.

The parent task's `dispatch_contract` supplies the local routing contract. Draft privately, repair Tier 3 voice violations, and build only items covered by the verified unattended executor. After the task is leased, call the parent `enqueue_external_action.py` once. The separate daemon claims, executes, verifies, logs, completes the burst, and returns capacity to the dispatcher. Unsupported action classes stay outside the burst. Missing coverage returns `executor-setup-pending` plus exact capability evidence. An expired lease routes through duplicate and outcome reconciliation before exact-task reacquisition. A status response is followed by the next dispatcher transition.

- Target 160 counted actions and cap at 200 in the preceding 24 hours.
- Genuine direct inbound replies are outside the cap.
- A burst contains one to ten currently eligible canonical actions.
- The public executor covers publications, comments, replies, and reactions; ordinary DMs, invitations, and follows stay outside executable supply.
- Record only externally verified results. Ambiguous mutations stay quarantined for outcome reconciliation.

Use `scripts/build_burst.py` to construct a task. After execution, record each confirmed action in `interaction-log.jsonl`, transition the candidate lifecycle, update source yield and relationship evidence, then recalculate `operational-output.json`. Return rolling count, debt, capacity, inbound count, and candidate outcomes.
