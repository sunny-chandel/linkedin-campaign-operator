---
name: linkedin-campaign-orchestrator
description: Run a persistent organic LinkedIn growth operating system with continuous dispatch, adaptive engagement and reciprocity, dynamic publishing, live skill refresh, state recovery, and auditable execution. Use for complete content days and continued execution toward configurable follower and connection goals; do not treat it as an advertising campaign builder.
metadata:
  author: sunny
  version: "5.1.0"
---

# LinkedIn campaign orchestrator

Run the campaign as a stateful pipeline. Treat this skill as the governing layer; use the other installed LinkedIn campaign skills when their descriptions match the current stage.

This is a reusable organic profile-growth operating system. It is not an advertising or lead-generation campaign builder. Its defaults target 10,000 followers and 10,000 connections, while initialization can set the owner, profile, timezone, niche, baselines, and goals. India, US-Central, and UK/EU are the default operating regions.

## Deterministic entry and path resolution

Invoke this installed skill directly as `/linkedin-campaign-orchestrator`; natural-language launchers and parent agents must route to that same skill entry point before investigating the filesystem. Once loaded, use the campaign state's `runtime_instructions.install_path`, `${CLAUDE_SKILL_DIR}`, or the install path returned by `claude plugin list --json`, in that order. Never locate this plugin with `find /`, `find ~`, a recursive scan of `/Users`, Spotlight, or another broad filesystem search. If no deterministic installed path resolves, record an offline runtime-capability blocker and continue work that does not require plugin files.

The normal start command is `/linkedin-campaign-orchestrator Resume <state-dir> from durable state and execute the dispatcher.` Do not replace it with a generic campaign conversation, a marketing questionnaire, or a search for repository copies.

## Non-negotiable operating rules

- Lock the target and automation envelope before entering automated mode.
- On the first run only, when no valid active authorization receipt exists, tell the recognized owner that the system will perform pre-flight checks and then operate the configured campaign autonomously. Ask one direct consent question. After the owner agrees, immediately run `python scripts/runtime_control.py <state-dir> consent-grant --owner "<stored-owner-name>" --source explicit-owner-confirmation`.
- The resulting campaign-lifetime consent record is the durable authority for this campaign across context compression, model changes, Claude restarts, and later sessions. Reload it from disk instead of relying on conversation memory. Never ask for routine approval again while that receipt remains active and the verified account identity has not changed.
- Use connected Chrome for LinkedIn pre-flight, reading, publishing, comments, replies, DMs, reactions, and other scheduled campaign actions.
- Route missing Chrome connections, failed logins, account-identity mismatches, unavailable capabilities, and transient page failures through automatic technical recovery. Continue every unaffected work lane, preserve checkpoints, and resume the affected task as soon as its dependency is available.
- Keep system and skill instructions immutable during a campaign. Store learning in runtime state, not in this skill.
- Do not stop after one daily cycle. Continue until verified achievement or explicit user stop. Technical failures enter recovery and do not end the campaign while valid work remains.
- Persistent execution retains the 100-action base ceiling, 10-action proactive-burst cap, qualification gate, and cooldowns. Genuine direct inbound replies may exceed the base ceiling and must be counted separately.

For exact state definitions and recovery rules, read [state and consent](references/state-and-consent.md).

## Startup and self-revival

When campaign state exists, start by recovering durable state rather than interpreting the visible chat transcript. When it does not exist, begin with a read-only Chrome identity discovery so the owner and profile can be initialized without a questionnaire. Do not create a setup visualization, display a generic campaign form, produce a marketing brief, or ask for discoverable configuration.

The package provides these operating defaults:

- objective: organic profile growth to 10,000 followers and 10,000 connections, unless configured otherwise;
- deadline: none;
- timezone: the campaign-configured IANA timezone;
- regions: India, US-Central, and UK/EU;
- adaptive dispatcher, action limits, qualification rule, cooldowns, and content voices defined below.

Use Chrome and visible profile information, recent content, analytics, and entitlement information to determine the owner name, profile URL, current follower and connection baselines, professional niche, content pillars, premium products, and usable capabilities. Never ask for values that can be discovered from the connected account.

After Chrome pre-flight passes, continue an existing campaign state when available. Otherwise initialize `campaign-data/linkedin-growth/` with `python scripts/init_campaign.py <state-dir> --owner-name <name> --profile-url <url> --timezone <iana-timezone>`, passing discovered values. Optional flags set the niche, baselines, campaign ID, and follower or connection goals. For an existing state directory, run `python scripts/migrate_campaign.py <state-dir>` before validation so newly introduced artifacts and defaults are added without overwriting campaign data. Store discovered values when visible; record temporarily unavailable optional values as unknown and continue.

Then run `python scripts/resume_campaign.py <state-dir> --session-id <current-session-id>`. This is mandatory on every new or resumed compatible-agent session and after a detected machine interruption. It reloads the consent receipt, detects downtime, expires abandoned leases, reconciles the campaign-local content day, reconstructs missing daily tasks from artifacts and evidence, restores safe missed work, closes obsolete time-bound work explicitly, and preserves every confirmed external outcome. Immediately run `audit_pipeline.py --write` and `dispatch_next_work.py --record`, then execute the returned task.

If self-revival reports `consent-required`, ask the single initial consent question and store the answer. If it loads an active receipt, do not mention consent as a question and do not seek confirmation again. Run `python scripts/validate_campaign.py <state-dir>` after consent is active. Store discovered optional values when visible; record temporarily unavailable values as `unknown` and continue.

Self-revival catches up safe missed work after downtime but never fabricates activity, duplicates an ambiguous external mutation, publishes an obsolete prior-day package, or makes up missed engagement volume. Recover analytics, research, state, current-day publication, and still-valid signal work; close stale time-bound tasks with evidence and create the correct current-day replacement.

## Lifecycle

Lifecycle and blocker classification is agent-neutral. Claude, Codex, and every compatible agent must derive it from the same durable runtime evidence, never from model identity, chat wording, or private interpretation. Run the deterministic runtime controls and treat `runtime_classification` in `campaign-state.json` as authoritative: identical evidence must always produce the same state and next-action eligibility.

Use exactly these states:

- `ready`: target and consent are valid; execution has not begun.
- `running`: the pipeline is progressing normally.
- `recovering`: a recoverable failure is being retried or rerouted.
- `hard-blocked`: continuation needs a Chrome connection, login or identity correction, security resolution, or a required capability.
- `completed`: target achievement is verified with evidence.
- `user-stopped`: the recognized owner revoked or paused consent.

Completing the required minimum two verified publications and their daily learning ends the normal content obligation, not the campaign. Opportunity recovery may add up to four measured recovery posts, never exceeding six total publications in a content day.

## Live instruction refresh

At pre-flight, every scheduled wake, and before every stage, run the runtime resolver from `runtime_instructions.install_path` when that path is present; otherwise use the resolver under the currently loaded `${CLAUDE_SKILL_DIR}`. Pass `runtime_instructions.active_version` as `--session-version` and the campaign directory as `--state-dir`. If the resolver reports a newer installed version, directly read the returned orchestrator and all returned supporting `SKILL.md` files completely, rerun the resolver with `--activate`, use scripts and assets only from the returned install path, revalidate mutable state, and continue from the last confirmed stage without repeating external actions. This direct-load route is the automatic Claude Desktop path and requires no question, restart, or new session. Use `/reload-plugins` only when the active client explicitly advertises that command.

Read [runtime plugin refresh](references/runtime-refresh.md) for the exact version-resolution, reload, direct-load, and component-boundary behavior.

## Pre-flight

Run once at the start of every content day and again whenever a capability or identity state must be revalidated, in this order:

Before using a browser tool, run `python scripts/runtime_control.py <state-dir> preflight-status`. Reuse every unexpired passed component. Recheck only missing or expired components, a changed browser connection, a navigation/authentication failure, or a visible identity change.

1. Read `dispatcher.browser_binding.device_id` before browser discovery. Call `list_connected_browsers`, match that exact device ID, and immediately call the browser-selection tool with that ID as an explicit argument. Never invoke an interactive browser chooser without the stored device ID, never use an owner-question tool for device selection, and never ask the owner to choose repeatedly. An exact device-ID match is unambiguous even when its display label or ordinal changes; ignore other connected devices and do not present them as choices. If the stored device ID is absent, prefer the local macOS device, verify it read-only against the profile identity stored in the consent record, and persist it with `runtime_control.py browser-bind`; if it does not match, test remaining connected devices read-only and bind the first verified match. Replace an existing binding only after an explicit owner reset. If a stored pinned device is temporarily absent, do not ask about other devices and do not offer a device-choice prompt. Record a transient LinkedIn-lane failure, continue valid offline work, and automatically arm the returned lane-probe wake. Only after at least three scheduled probe cycles fail and neither lane nor any future wake path can advance may the exact connection correction be reported as a critical blocker.
2. Open LinkedIn in the pinned Chrome session and confirm it matches the owner name and full profile URL stored in the consent record. On first initialization, discover and store those values. Read the current profile name, handle, headline, image, niche, and visible positioning. Record passed checks with `runtime_control.py preflight-record`. If the pinned device is temporarily unavailable, retry through the configured circuit breaker, continue offline work, and probe automatically later. If logged out or on the wrong account, request only the exact login correction.
3. Open Claude Design and confirm its dashboard or projects load. If unavailable, block the creative lane, report that exact blocker, and continue work whose required artifacts can still be produced truthfully.
4. Confirm the `file_upload` capability is loaded. Never click a native file-input button directly; locate the input with page-reading tools and use `file_upload` with the local path. The upload cap is 10 MB per call.
5. Inspect the latest available Chrome, Claude Design, computer-use, and upload capabilities needed for the cycle and use the current supported workflow.
6. Run `linkedin-brand-system`. Reuse a valid profile-matched watermark kit or create and validate it in Claude Design, then make it active automatically.
7. Run `linkedin-premium-router` to inventory active LinkedIn paid entitlements, plan tiers, roles, limits, credits, and expiry information; calculate `subscription-utilization-plan.json`; and complete eligible setup for already-included features.
8. Read current followers, connections, recent content, and available analytics from the connected account, and save discovered values to campaign state.
9. Load campaign configuration, the persistent authorization receipt and state snapshot, current state, work queue, task-event log, recovery log, stage ledger, signal log, schedule-decision log, unresolved failures, runtime learning, active experiments, strategy weights, creator registry, GIF pattern library, and the Working Algorithm Model.
10. Recalculate target progress. If achieved, save final evidence and mark `completed`; otherwise continue immediately from the next valid pipeline stage.

A Chrome, login, account-identity, capability, network, or page failure enters automatic technical recovery. Record it through `runtime_control.py lane-event`, continue research, analytics from stored data, queue scoring from saved evidence, content preparation, creative work, subscription analysis, and logging, and let the circuit breaker schedule the next automatic probe. A missing pinned browser uses `transient-failure`, not `hard-blocker`, while automatic probes remain available. Recoverable or optional gaps use automatic fallbacks, are recorded as `unknown` when necessary, and do not stop the offline lane. Do not replace a failed Chrome check with a generic questionnaire or a connected-device choice.

Do not reopen a locked target during pre-flight. A missing optional goal-tracking feature is not a blocker.

## Automatic skill routing

The owner invokes this parent skill for the complete system. Route to the installed supporting skills without asking the owner to invoke them separately:

- use `linkedin-premium-router` during pre-flight, whenever an entitlement changes, before a stage that depends on a paid feature, and during the weekly retrospective;
- use `linkedin-brand-system` during pre-flight and before every GIF export;
- use `linkedin-gif-creative-intelligence` when the dispatcher selects creator observation and before every GIF production stage;
- use `linkedin-content-research` for source discovery, trend checks, topic selection, and claim verification;
- use `linkedin-content-production` after a research brief is complete;
- use `linkedin-engagement-planning` before every adaptive burst, reciprocity route, and reserve-replenishment stage;
- use `linkedin-analytics-learning` for equal-age snapshots, mandatory analytics recovery, schedule outcomes, experiments, and weekly learning reviews.

Return control to this orchestrator after each supporting stage, update persistent state, and continue from the next valid pipeline stage.

Automated mode is execution, not a planning conversation. Never ask whether to run a required supporting skill, prerequisite, pre-flight step, recovery step, queue, analysis, or content stage. Do not ask questions such as “want me to run research and production?” Announce the stage as a status update and execute it immediately. Request owner input only when a required technical dependency cannot be restored automatically and no other valid work can advance.

If either required normal publication package is missing, incomplete, stale, or invalid, automatically run its missing prerequisites in dependency order: `linkedin-content-research` → `linkedin-content-production` → publication-package validation. Produce exactly the next India and US-Central normal pair. A recovery package is separate, is generated only after both normal posts are live, and is limited to one unpublished package at a time. Route every valid package through the dynamic publication selector rather than waiting for a fixed clock time.

Every supporting skill inherits the active consent and automation state from this parent. A subskill must never create an onboarding step, request routine approval, ask the owner to invoke another skill, or return a “what should I do next?” choice. Resolve missing non-sensitive inputs in this order: read persistent state, inspect the connected account or existing artifacts, derive from verified evidence, then use the fixed campaign default or record `unknown`. Regenerate missing or invalid artifacts from the nearest valid upstream artifact. Use a documented base-flow fallback when an optional tool, metric, source, or premium feature is unavailable. Return a structured result to this orchestrator after every stage, including partial results and recovery notes, so the pipeline always advances or enters an explicit lifecycle state.

For recoverable failures, save state, verify the last observable outcome, retry safely up to the configured limit, select the best valid fallback, and continue without asking. Never terminate merely because a preferred source, candidate, metric, asset format, or premium feature is unavailable. At every wake and after every completed task, run `audit_pipeline.py` and `dispatch_next_work.py --record`. A recorded dispatch leases the selected task. Immediately record `task-event start`; checkpoint every useful result; record `complete` with evidence or `fail` with the observed reason. Never modify queue status manually. Expired leases recover automatically after a crash or restart.

Do not select the same non-urgent task type more than twice consecutively when another eligible type exists. Publication, direct inbound, pre-flight, lane recovery, and mandatory recovery are exempt. A wait is valid only when both scripts confirm that no work is executable now and campaign state contains an evidence-backed next wake trigger. Future `retry-wait` work is deferred work, not reconciliation debt. Never use repeated fixed-duration sleep commands. Use `campaign_status.py` for status reports so posting progress, engagement utilization, analytics debt, blockers, continuity, consent state, browser binding, continuation state, and true idle time remain distinct.

Every `wait` result includes an automatic continuation contract. Before ending the turn, arm or update exactly one deduplicated host wake for the returned `predicted_next_opportunity`, then record it with `runtime_control.py continuation-event --event armed`. Select the first available adapter in the returned priority list: a host-native scheduled wake, a host-native heartbeat, then a dynamic in-session loop. If one adapter fails, record `--event failed` and try the next automatically. Never ask the owner to choose between a scheduled agent, heartbeat, loop, or manual check-back. Never expose continuation setup as a question. On wake, record `--event woke`, run self-revival, audit, and dispatch immediately. Reuse the existing automation for later wake times instead of creating duplicates.

## Continuous 24-hour pipeline

Run a continuous dispatcher in the campaign-configured timezone. LinkedIn and offline work may occur throughout the day when evidence supports it. The system alternates short adaptive LinkedIn bursts with investigation, queue replenishment, production, analytics, learning, and recovery. It is never a continuous clicking loop.

Give the configured production priority window to source research, learning-ledger maintenance, experiment registration, and production of the two normal validated packages for the next content day: one India and one US-Central. High-value inbound signals may still interrupt this production block. Do not stockpile extra normal posts or more than one unpublished recovery package.

At every wake, publication, burst, analytics checkpoint, and discovery pass, evaluate opportunity health and persist the active tier. Then use this order: technical recovery; genuine direct inbound; due publication; mandatory-stage recovery; canonical engagement burst; opportunity generation; normal or recovery content; recovery analytics; general analytics and investigation. Read [continuous dispatch](references/continuous-dispatch.md) for the exact controller, source ladder, adaptive timing, budget accounting, completion gates, and lane-specific recovery.

`engagement-opportunities.json` is the only source of truth for executable candidates. Its currently eligible records determine reserve coverage; a numeric checkpoint can never claim supply. If one candidate is eligible, create an `engagement-burst` immediately instead of searching for a full batch. Each burst contains at most ten actions. Record discovery with `runtime_control.py opportunity-pass` and execution with `runtime_control.py burst-complete`. A low-yield pass receives an exact `not_before`, rotates to a different source, and allows offline work; never create a generic queue-reconciliation loop.

Publishing has no fixed clock time. Guarantee the two normal regional posts, then allow recovery posts one at a time only while recovery is active. A recovery publication requires at least 120 minutes since the prior post, either preceding velocity below 85 percent of its equal-age baseline or cannibalization risk below 0.35, fresh source evidence, a distinct topic angle and pillar or format, and a publication score of at least 65. Collect analytics and reevaluate health after each recovery post. Publish at least two and never more than six posts per local content day.

## Fixed campaign invariants

The opportunity-health score uses trailing seven-day comparable medians: equal-age impressions 25 percent, engagement rate 20, profile-view velocity 20, follower and connection growth 10, action pace 15, and canonical reserve coverage plus discovery yield 10. Exclude unavailable metrics and renormalize the remaining weights. Until three comparable observations exist, retain a reduced-confidence score. Activate recovery after two scores below 70 or whenever actions are below half the expected pace. Exit only after two consecutive scores at least 80 with pace at least 90 percent.

Rotate discovery by measured yield through: direct inbound and notifications; own-post signals; existing targets and hubs; qualified participants on strong hub posts; regional and topic search; available premium signals; relevant second-degree and newly accepted connections; then creator registry, adjacency, trends, and fresh primary-source discussions. Allocate discovery 70/20/10 across proven, promising, and exploratory sources. Rejections and staleness change source allocation, never the canonical count or the quality floor.

- Exactly two normal prepared packages and at least two verified posts per complete local content day. Opportunity recovery may raise the daily publication total to six; never store more than one unpublished recovery package and never publish a seventh.
- Proactive work runs in fully adaptive bursts of at most 10 actions. There is no fixed burst count or fixed interval; opportunity and learned concentration determine the next burst.
- Proactive and soft-reciprocal actions share a 100-action daily target and hard ceiling. The opportunity controller tracks 20 actions by 25 percent of the day, 45 by half, 70 by three quarters, and 100 by close. Never exceed 100 or force invalid actions to fill a deficit.
- Genuine direct inbound replies use the base budget until 100, then continue through a separately logged `direct_reply_overage` counter.
- Recovery gates are exact: normal uses score 65, 3,000 new-target followers, and 72 hours; expansion uses 60, 2,000, and 48 hours; intensive uses 55, 1,000, and 24 hours. Never go below the intensive tier. New-target follower gates do not apply to direct replies or existing targets.
- Do not initiate proactive engagement with the same person more than twice in seven days. Apply the active tier cooldown. Direct inbound conversations are exempt but logged.
- Premium actions count toward the same totals.
- Subscription optimization can reprioritize and configure already-included features, but it cannot purchase, upgrade, start a paid trial, change billing, accept a contract, or alter any fixed campaign invariant.
- Tier 2 and Tier 3 content rules remain active; load the content-production skill for their exact definitions.
- Fact-check every public factual claim.
- Chat previews are informational during active automated mode.

## Recovery and completion

Use [state and consent](references/state-and-consent.md) to classify failures. Verify ambiguous external outcomes before retrying. Never repeat a post, message, or comment merely because a tool timed out.

At the end of every stage, update the artifacts described in [artifact contracts](references/artifact-contracts.md). Mark the campaign complete only when the configured target formula passes and its evidence is saved.
