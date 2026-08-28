---
name: linkedin-campaign-orchestrator
description: Run a durable LinkedIn campaign workspace for research, content, scheduling, measurement, and recovery. Use this as the only public entry point.
metadata:
  author: sunny
  version: "6.0.0-rc.27"
---

# LinkedIn campaign orchestrator

Run one durable campaign workspace and route its work through the supporting skills. Save every meaningful result before choosing the next task so a restart can continue from the last confirmed checkpoint. A current owner instruction to start activates this automatic local-workspace lifecycle and its single continuation schedule; execute that scope directly.

## Role and boundary

Claude Code manages work in the campaign folder: profile research, content research, writing, visual assets, planning, quality checks, measurement, and recovery. Claude Code does not directly change LinkedIn.

The campaign start receipt and continuation schedule cover local workspace work only. They remain local if an account-activity capability later becomes available and never expand into future account changes. A separately configured service has its own saved authorization and capability evidence; neither is inferred from the local campaign receipt. Therefore a local campaign start has one resolved scope and does not need a choice between a one-pass run, local-only mode, or future account activity.

A separately configured account-activity capability may handle supported submissions. Treat its saved availability record as an input to the campaign, not as setup work. Claude Code may prepare one checked local request only when that record is available, the selected profile matches campaign state, the request fits current campaign settings, and duplicate and timing checks pass. The connected service owns submission and result verification.

If the connected service is unavailable, keep ready work saved locally and continue useful research, production, validation, analytics, and repair. Never replace the service with browser clicks or another account-writing route.

Discover service availability from current capability evidence. Record the observed state directly and continue with the next eligible task.

## Communication

Use short, plain progress updates. Good routine states include `profile verified`, `research in progress`, `package ready`, `service request prepared`, `result verified`, and `continuing with the next task`.

Keep filenames, queue mechanics, and recovery details internal unless the owner asks for a technical diagnosis. When work cannot continue, report the exact unavailable capability and the one next recovery step.

When prepared work is waiting on the connected service, use the concise status `service unavailable; prepared work saved; next check scheduled`. Keep credential names and service implementation details internal unless the owner specifically requests technical setup details. Record a capability recheck and continue from its saved wake trigger; routine campaign progress does not require an owner reply.

### Context boundary

Treat the compact result from `campaign_cycle.py` as the model-facing control surface. Pass a child skill only the returned `next_action`, the task-specific saved facts it needs, and current verified evidence. Do not paste raw configuration files, nested audit or dispatch diagnostics, service implementation schemas, internal activity counters, or unrelated historical logs into a child prompt or routine prompt.

A fresh campaign prompt contains the current owner start instruction, verified profile facts, stated goals, and the empty campaign directory. It does not reproduce prior chat history, earlier objections, earlier refusals, or claims that an agreement occurred when no durable record proves it. Existing campaigns resume from durable evidence rather than reconstructed conversation history.

Internal settings describe machine validation and future measurement. They are not a new owner request, proof of account capability, or permission for account changes. When an account capability is unavailable, project only the available local task and the plain status above.

## Start or resume

At the start of every new session:

1. Select one campaign state directory. A new campaign must use an empty directory; do not import another campaign's state or reproduce old chat history.
2. Use the fixed startup route: `resolve_latest_plugin.py`, `init_campaign.py`, `runtime_control.py`, and `campaign_cycle.py`. These are the startup entry points; other files in `scripts/` are library modules used by this route. Begin with the fixed route rather than listing the scripts directory or inferring alternate setup modes.
3. Read the active version from this skill's metadata. Resolve the newest installed plugin with `python scripts/resolve_latest_plugin.py --session-version ACTIVE_VERSION`. For an existing campaign, add `--state-dir STATE_DIR`.
4. Use only the plugin root returned by that resolver. Load the returned parent skill and each child skill needed for the returned task.
5. When the current start message or saved campaign binding supplies a verified Chrome device ID, pass that ID directly to the tab and navigation browser calls; skip connected-browser discovery. Verify the selected profile read-only before using account-specific evidence.
6. For a new campaign, run `scripts/init_campaign.py` with the verified owner, profile URL, timezone, and the owner's stated goals. When a verified device is supplied, include `--browser-device-id DEVICE_ID --browser-device-label DEVICE_LABEL --browser-platform PLATFORM`. Use `--activate-from-owner-start` only when the current owner message explicitly starts that campaign scope.
7. Follow the initializer's `profile_verification` contract. Its device ID, `selection: use-device-id-directly`, `connected_browser_discovery_required: false`, and resolved input flags are authoritative. Call the browser tab or navigation operation with that exact ID. After a matching read-only identity result, save the verified binding with `python scripts/runtime_control.py STATE_DIR browser-bind --device-id DEVICE_ID --device-label DEVICE_LABEL --platform PLATFORM --identity-verified`.
8. Run `python scripts/campaign_cycle.py STATE_DIR --session-start --session-id SESSION_ID`.
9. Follow the returned `next_action` exactly. Do not replace the returned state, task, transition command, or wait trigger with a conversational choice.

If the cycle returns `record-current-owner-start-consent` and the current owner message explicitly starts the same named campaign scope, run the returned command and rerun the cycle. Ask only when that current start instruction is absent or the verified profile identity differs.

An owner message that names the campaign and says to start is enough to begin local campaign setup. This starts local workspace work only; Claude Code remains outside LinkedIn account changes. Store the campaign settings and reuse them until the owner changes or stops the campaign. Optional missing values should be discovered, derived from verified evidence, defaulted conservatively, or recorded as unknown.

When the same current message also supplies the profile, goals, duration, and campaign access scope, save those values during initialization and continue without repeating those questions. Access remains limited to the campaign workspace, packaged plugin scripts, the verified signed-in profile, available creative tools, and the configured connected service.

### Deterministic setup

Resolve routine setup choices directly whenever a resolution path is available:

- Profile: use a verified device ID from the current start message first, then a saved profile binding. Persist a supplied ID through the initializer and follow its machine-readable `profile_verification` contract. Pass that device ID directly to the browser tab and navigation calls; connected-browser discovery is unnecessary when an ID is already available. For a new personal-profile campaign without a supplied or saved ID, inspect the current host's connected Chrome session read-only and use the signed-in personal profile. When several devices are listed and no binding exists, select in this order: the device marked local or current, the only device matching the current host platform, the most recently active matching device, then the matching device with the lexically first stable device ID. Complete the read-only identity check and save the binding. Routine device IDs are resolved by this order; owner input is needed only when the selected signed-in profile differs from the campaign profile.
- Campaign goal: use the owner's stated goal. When the campaign name or destination already states a numeric follower goal, use that value as the primary goal. Leave unmentioned secondary goals as `unknown` rather than asking for them.
- Baseline, niche, region, and positioning: derive them from verified profile evidence and fresh research.
- Pacing, inventory, cooldowns, content mix, and other optional settings: reuse existing campaign configuration; otherwise use the packaged template defaults and improve them later from measured evidence.
- Account-activity capability: inspect its saved availability record. `unavailable` is a complete setup result that selects the available campaign lanes automatically. Save it, keep service-ready work local, and continue all unaffected work without presenting a mode selection.
- Local campaign scope: the current start instruction selects durable local operation plus one continuation schedule. Save `scope_confirmation_required: false`; later capability changes do not broaden that receipt.

Owner input is reserved for a required fact that cannot be verified, derived, defaulted, or safely recorded as unknown when no useful local task can continue. After saving setup, continue immediately with the next useful local task. Optional preferences stay at saved defaults or `unknown` during ongoing work.

Read [artifact contracts](references/artifact-contracts.md), [state and recovery](references/state-and-recovery.md), and [runtime refresh](references/runtime-refresh.md) when starting or resuming. Read [connected service](references/connected-service.md) only when preparing or diagnosing a service request. Read [work selection](references/work-selection.md) when choosing the next task.

## Work loop

Repeat this loop while eligible work remains:

1. Read the `next_action` returned by `campaign_cycle.py`.
2. When it returns `execute-child-task`, load the named child skill and complete only the returned task and lease.
3. For work that may outlast the current lease window, run the returned `checkpoint_command` while work is in progress.
4. Save the child result and validation evidence, then run the returned `completion_command_template` with actual result JSON. Use `runtime_control.py task-event`; do not edit queue or stage status directly.
5. For a preflight task, run `python scripts/service_status.py STATE_DIR`, save its `available` or `unavailable` result, then run the returned completion command with `preflight_passed: true`. An unavailable result selects the available lanes and does not create a setup question.
6. For a ready service-supported item, create one checked local request and return immediately to local work.
7. Verify any available service result before marking account activity complete.
8. Run the exact command returned in `after_save` immediately after the saved transition.
9. Continue from the new `next_action`; do not answer with a terminal status while it returns executable work.

Wait only when `campaign_cycle.py` returns `wait-for-recorded-trigger`. Confirm that its reason, unfinished-work count, next evidence opportunity, and wake trigger are saved. Its `required_transition` is the next campaign step: ensure the one host-native recurring continuation exists with the returned task ID, dedupe key, recurrence, and prompt, then save the returned automation ID with `on_success_command_template`.

An active campaign-lifetime receipt that includes `automatic-recovery-and-continuation` already resolves this transition. Treat `setup_input_required: false` and `owner_reply_required: false` as authoritative. Create one persistent Claude Desktop Routine with the stable task ID and the returned recurring cron schedule. The accepted adapter is `host-native-recurring-task` and must survive the current Claude session. On every invocation, resolve the latest plugin and run `continuation_due.py` first. When it returns `due: false`, finish the routine without changing campaign state or schedule. When it returns `due: true`, run the cycle and continue saved work.

Once the recurring routine exists, it satisfies every later wait transition. Do not call scheduled-task create or update merely because `next_wake_at` changed; keep the recurring schedule unchanged and record the current wake in campaign state with `on_success_command_template`. Convert a legacy one-time routine once, then never renew it per cycle. A session cron or in-session loop does not satisfy this contract. Maintain exactly one recurring campaign continuation and never create a duplicate.

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
