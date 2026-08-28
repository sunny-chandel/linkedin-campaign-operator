---
name: linkedin-campaign-orchestrator
description: Run a durable LinkedIn campaign workspace for research, content, scheduling, measurement, and recovery, with a connected service for supported account activity. Use this as the only public entry point.
metadata:
  author: sunny
  version: "6.0.0-rc.14"
---

# LinkedIn campaign orchestrator

Run one durable campaign workspace and route its work through the supporting skills. Save every meaningful result before choosing the next task so a restart can continue from the last confirmed checkpoint.

## Role and boundary

Claude Code manages work in the campaign folder: profile research, content research, writing, visual assets, planning, quality checks, measurement, and recovery. Claude Code does not directly change LinkedIn.

A separately installed connected service may handle supported account activity. Treat that service as an existing capability, not something to build or configure from this skill. Claude Code may prepare one checked local service request only when the service is available, the selected profile matches campaign state, the request is within current campaign settings, and duplicate and timing checks pass. The connected service owns submission and result verification.

If the connected service is unavailable, keep ready work saved locally and continue useful research, production, validation, analytics, and repair. Never replace the service with browser clicks or another account-writing route.

Discover service availability from current capability evidence. Record the observed state directly and continue with the next eligible task.

## Communication

Use short, plain progress updates. Good routine states include `profile verified`, `research in progress`, `package ready`, `service request prepared`, `result verified`, and `continuing with the next task`.

Keep filenames, queue mechanics, and recovery details internal unless the owner asks for a technical diagnosis. When work cannot continue, report the exact unavailable capability and the one next recovery step.

## Start or resume

At the start of every new session:

1. Resolve the newest installed plugin with `scripts/resolve_latest_plugin.py`.
2. Use only the plugin root returned by that resolver. Load the newest parent skill and each child skill needed for the returned task.
3. Select one campaign state directory. A new campaign must use an empty directory; do not import another campaign's state or reproduce old chat history.
4. Verify the selected profile read-only before using account-specific evidence.
5. For a new campaign, run `scripts/init_campaign.py` with the verified owner, profile URL, timezone, and the owner's stated goals. Use `--activate-from-owner-start` only when the current owner message explicitly starts that campaign scope.
6. Run `scripts/campaign_cycle.py STATE_DIR --session-start --session-id SESSION_ID`.
7. Follow the returned `next_action` exactly. Do not replace the returned state, task, or wait trigger with a conversational choice.

If the cycle returns `record-current-owner-start-consent` and the current owner message explicitly starts the same named campaign scope, run the returned command and rerun the cycle. Ask only when that current start instruction is absent or the verified profile identity differs.

An owner message that names the campaign and says to start is enough to begin local campaign setup. This starts local workspace work only; Claude Code remains outside LinkedIn account changes. Store the campaign settings and reuse them until the owner changes or stops the campaign. Optional missing values should be discovered, derived from verified evidence, defaulted conservatively, or recorded as unknown.

When the same current message also supplies the profile, goals, duration, and campaign access scope, save those values during initialization and continue without repeating those questions. Access remains limited to the campaign workspace, packaged plugin scripts, the verified signed-in profile, available creative tools, and the configured connected service.

### Deterministic setup

Resolve routine setup choices directly whenever a resolution path is available:

- Profile: use the saved profile binding. For a new personal-profile campaign, inspect the current host's connected Chrome session read-only and use the signed-in personal profile. If several devices are listed and no binding exists, choose the device matching the current host platform; save that device binding after identity verification.
- Campaign goal: use the owner's stated goal. When the campaign name or destination already states a numeric follower goal, use that value as the primary goal. Leave unmentioned secondary goals as `unknown` rather than asking for them.
- Baseline, niche, region, and positioning: derive them from verified profile evidence and fresh research.
- Pacing, inventory, cooldowns, content mix, and other optional settings: reuse existing campaign configuration; otherwise use the packaged template defaults and improve them later from measured evidence.
- Connected service: inspect capability records and running service evidence. If readiness is not proven, record `unavailable`, keep service-ready work local, and continue all unaffected work.

Owner input is reserved for a required fact that cannot be verified, derived, defaulted, or safely recorded as unknown when no useful local task can continue. After saving setup, continue immediately with the next useful local task. Optional preferences stay at saved defaults or `unknown` during ongoing work.

Read [artifact contracts](references/artifact-contracts.md), [state and recovery](references/state-and-recovery.md), and [runtime refresh](references/runtime-refresh.md) when starting or resuming. Read [connected service](references/connected-service.md) only when preparing or diagnosing a service request. Read [work selection](references/work-selection.md) when choosing the next task.

## Work loop

Repeat this loop while eligible work remains:

1. Read the `next_action` returned by `campaign_cycle.py`.
2. When it returns `execute-child-task`, load the named child skill and complete only the returned task and lease.
3. Save the child result and validation evidence before changing task status.
4. For a ready service-supported item, create one checked local request and return immediately to local work.
5. Verify any available service result before marking account activity complete.
6. Run `scripts/campaign_cycle.py STATE_DIR` again immediately after the saved transition.
7. Continue from the new `next_action`; do not answer with a terminal status while it returns executable work.

Wait only when `campaign_cycle.py` returns `wait-for-recorded-trigger`. Confirm that its reason, unfinished-work count, next evidence opportunity, and wake trigger are saved. Maintain one campaign continuation schedule and update it rather than creating duplicates.

If a capability is unavailable, save that observation and rerun the cycle. The dispatcher may route another local task or `linkedin-runtime-repair`; capability absence by itself is not a reason to invent a manual workflow or end the campaign.

## Task priority

Choose work in this order unless current evidence supports a better local decision:

1. Repair a required capability or reconcile an unclear prior result.
2. Process genuine inbound conversation evidence.
3. Complete a due publication package or scheduled measurement.
4. Finish missing research, claim verification, caption, asset, watermark, or package validation.
5. Prepare one currently relevant engagement item that passes campaign rules.
6. Refresh relevant conversation opportunities.
7. Replenish the configured content inventory.
8. Review analytics, experiments, regional evidence, and learning.

Use the campaign configuration for quantity, pacing, inventory, regions, and cooldowns. Do not invent activity to satisfy a numeric target, exceed configured limits, or treat an outcome such as follower growth as guaranteed.

## Child routing

- `linkedin-opportunity-discovery`: collect fresh, relevant conversation evidence.
- `linkedin-engagement-planning`: check relevance, timing, prior contact, duplicates, and campaign limits.
- `linkedin-engagement-execution`: prepare one checked service-ready engagement item and record its verified result.
- `linkedin-regional-intelligence`: allocate content opportunities across relevant regions.
- `linkedin-content-research`: create evidence-ranked briefs and verify claims.
- `linkedin-content-production`: create validated captions and visual packages.
- `linkedin-publishing-operations`: maintain ready inventory, select timing, and record verified publication evidence.
- `linkedin-analytics-learning`: collect comparable measurements and update durable learning.
- `linkedin-brand-system`: maintain and apply the profile-based watermark kit.
- `linkedin-gif-creative-intelligence`: learn and apply reusable GIF patterns.
- `linkedin-premium-router`: use verified, already-included subscription features when useful.
- `linkedin-runtime-repair`: restore an unavailable capability and resume the saved task.

Each child returns its saved result, evidence, and next trigger to this parent. For status requests, answer briefly from saved artifacts, then continue the current local task when one is already in progress.

## Quality and integrity

- Use verified sources for factual claims.
- Keep account identity, timing, cooldown, duplicate, and content-quality checks current.
- Save completed evidence before retrying after a timeout or restart.
- Treat an unclear prior account result as unresolved until the connected service supplies verification.
- Preserve confirmed history, content, analytics, experiments, learning, brand assets, and repair checkpoints across restarts.
- Mark the campaign complete only when its configured goal formula passes with saved evidence or the owner stops it.
- Never claim a capability, profile fact, result, prior agreement, or completed step without current or durable evidence.
