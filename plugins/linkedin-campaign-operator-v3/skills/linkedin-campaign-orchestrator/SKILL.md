---
name: linkedin-campaign-orchestrator
description: Run Sunny Chandel's persistent organic LinkedIn 10k/10k operating system with continuous 24-hour dispatch, adaptive engagement and reciprocity, dynamic publishing, live skill refresh, state recovery, and auditable execution. Use for complete content days and continued execution toward 10,000 followers and 10,000 connections; do not treat it as an advertising campaign builder.
metadata:
  author: sunny
  version: "0.5.0"
---

# LinkedIn campaign orchestrator

Run the campaign as a stateful pipeline. Treat this skill as the governing layer; use the other installed LinkedIn campaign skills when their descriptions match the current stage.

This is a preconfigured organic profile-growth operating system for Sunny Chandel. It is not an advertising, lead-generation, B2B setup, or generic campaign builder. The locked objective is 10,000 followers and 10,000 connections, with no deadline unless Sunny later sets one. India, US-Central, and UK/EU are the fixed operating regions.

## Non-negotiable operating rules

- Lock the target and automation envelope before entering automated mode.
- Invoking this skill or telling it to start records the recognized owner's consent for the complete fixed system. Do not ask for another setup approval or routine action confirmation.
- Use connected Chrome for LinkedIn pre-flight, reading, publishing, comments, replies, DMs, reactions, and other scheduled campaign actions.
- Any interactive verification, technical signal, access message, wrong login, or identity mismatch blocks the LinkedIn lane. Stop LinkedIn mutations, tell Sunny exactly what must be corrected, and continue valid offline work. Mark the whole pipeline `hard-blocked` only when no authorized offline work can advance.
- Keep system and skill instructions immutable during a campaign. Store learning in runtime state, not in this skill.
- Do not stop after one daily cycle. Continue until verified achievement, explicit user stop, or a hard blocker.
- Persistent execution never overrides the 100-action base ceiling, 10-action proactive-burst cap, qualification gate, cooldowns, or technical rollback. Genuine direct inbound replies may exceed the base ceiling and must be counted separately.

For exact state definitions and recovery rules, read [state and consent](references/state-and-consent.md).

## Startup behavior

Start with Chrome pre-flight. Do not initialize a generic campaign, create a setup visualization, display an onboarding questionnaire, produce a marketing brief, or ask for configuration before checking Chrome.

The package already fixes these values; never ask for them during startup:

- owner: Sunny Chandel;
- objective: organic profile growth to 10,000 followers and 10,000 connections;
- deadline: none;
- timezone: Asia/Kolkata;
- regions: India, US-Central, and UK/EU;
- adaptive dispatcher, action limits, qualification rule, cooldowns, and content voices defined below.

The fixed LinkedIn profile is `https://www.linkedin.com/in/sunny-chandel-6a05bb401/`. Use Chrome and visible profile information, recent content, analytics, and entitlement information to determine current follower and connection baselines, professional niche, content pillars, premium products, and usable capabilities. Never ask for the profile URL, niche, baselines, or premium plan before attempting to discover them.

After Chrome pre-flight passes, continue the existing `sunny-linkedin-10k-10k` state when available. Otherwise initialize `campaign-data/sunny-linkedin-10k-10k/` with `python scripts/init_campaign.py <state-dir>`. For an existing state directory, run `python scripts/migrate_campaign.py <state-dir>` before validation so newly introduced artifacts and safe defaults are added without overwriting campaign data. Migrate any older blank or generic draft to these fixed defaults. Store discovered values when visible; record temporarily unavailable optional values as unknown and continue.

Run `python scripts/validate_campaign.py <state-dir>`. The initializer records active consent from the recognized owner. Do not present a consent questionnaire or activation summary. Ask the owner only for the exact action needed to clear a hard blocker.

## Lifecycle

Use exactly these states:

- `ready`: target and consent are valid; execution has not begun.
- `running`: the pipeline is progressing normally.
- `recovering`: a recoverable failure is being retried or rerouted.
- `hard-blocked`: continuation needs a Chrome connection, login or identity correction, security resolution, or a required capability.
- `completed`: target achievement is verified with evidence.
- `user-stopped`: the recognized owner revoked or paused consent.

Completing two verified publications and their required daily learning ends a content day, not the campaign.

## Live instruction refresh

At pre-flight, every scheduled wake, and before every stage, run the runtime resolver from `runtime_instructions.install_path` when that path is present; otherwise use the resolver under the currently loaded `${CLAUDE_SKILL_DIR}`. Pass `runtime_instructions.active_version` as `--session-version` and the campaign directory as `--state-dir`. If the resolver reports a newer installed version, directly read the returned orchestrator and all returned supporting `SKILL.md` files completely, rerun the resolver with `--activate`, use scripts and assets only from the returned install path, revalidate mutable state, and continue from the last confirmed stage without repeating external actions. This direct-load route is the automatic Claude Desktop path and requires no question, restart, or new session. Use `/reload-plugins` only when the active client explicitly advertises that command.

Read [runtime plugin refresh](references/runtime-refresh.md) for the exact version-resolution, reload, direct-load, and component-boundary behavior.

## Pre-flight

Run once at the start of every content day and again whenever a capability or identity state must be revalidated, in this order:

1. Call `list_connected_browsers` and confirm the intended Chrome device. If Chrome is unavailable or the device is wrong, block only the LinkedIn lane, ask Sunny only to connect or select the correct Chrome device, and continue valid offline work.
2. Open LinkedIn in the connected Chrome session and confirm it is logged in as Sunny Chandel by matching the displayed identity and fixed profile URL. Read the current profile name, handle, headline, image, niche, and visible positioning. If logged out or on the wrong account, block LinkedIn execution, ask Sunny only to correct the login, and preserve offline work that does not depend on new identity evidence.
3. Open Claude Design and confirm its dashboard or projects load. If unavailable, block the creative lane, report that exact blocker, and continue work whose required artifacts can still be produced truthfully.
4. Confirm the `file_upload` capability is loaded. Never click a native file-input button directly; locate the input with page-reading tools and use `file_upload` with the local path. The upload cap is 10 MB per call.
5. Inspect the latest available Chrome, Claude Design, computer-use, and upload capabilities needed for the cycle and use the current supported workflow.
6. Run `linkedin-brand-system`. Reuse a valid profile-matched watermark kit or create and validate it in Claude Design, then make it active automatically.
7. Run `linkedin-premium-router` to inventory active LinkedIn paid entitlements, plan tiers, roles, limits, credits, and expiry information; calculate `subscription-utilization-plan.json`; and complete eligible setup for already-included features.
8. Read current followers, connections, recent content, and available analytics from the connected account, and save discovered values to campaign state.
9. Load or initialize campaign configuration, consent, current state, work queue, stage ledger, signal log, schedule-decision log, unresolved failures, runtime learning, active experiments, strategy weights, creator registry, GIF pattern library, and the Working Algorithm Model.
10. Recalculate target progress. If achieved, save final evidence and mark `completed`; otherwise continue immediately from the next valid pipeline stage.

An identity, warning, restriction, or Chrome failure stops the LinkedIn lane at that point. Continue research, analytics from stored data, queue scoring from saved evidence, content preparation, creative work, subscription analysis, and logging. Recoverable or optional gaps use automatic fallbacks, are recorded as `unknown` when necessary, and do not stop the offline lane. Do not replace a failed Chrome check with a generic questionnaire.

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

Automated mode is execution, not a planning conversation. Never ask whether to run a required supporting skill, prerequisite, pre-flight step, recovery step, queue, analysis, or content stage. Do not ask questions such as “want me to run research and production?” Announce the stage as a status update and execute it immediately. Ask Sunny only for the exact intervention required to clear a hard blocker defined in this skill.

If either required publication package is missing, incomplete, stale, or invalid, automatically run its missing prerequisites in dependency order: `linkedin-content-research` → `linkedin-content-production` → publication-package validation. Produce exactly the next India and US-Central pair and no third package. When a package becomes valid, route it through the dynamic publication selector rather than waiting for a fixed clock time.

Every supporting skill inherits the active consent and automation state from this parent. A subskill must never create an onboarding step, request routine approval, ask the owner to invoke another skill, or return a “what should I do next?” choice. Resolve missing non-sensitive inputs in this order: read persistent state, inspect the connected account or existing artifacts, derive from verified evidence, then use the fixed campaign default or record `unknown`. Regenerate missing or invalid artifacts from the nearest valid upstream artifact. Use a documented base-flow fallback when an optional tool, metric, source, or premium feature is unavailable. Return a structured result to this orchestrator after every stage, including partial results and recovery notes, so the pipeline always advances or enters an explicit lifecycle state.

For recoverable failures, save state, verify the last observable outcome, retry safely up to the configured limit, select the best valid fallback, and continue without asking. Never terminate merely because a preferred source, candidate, metric, asset format, or premium feature is unavailable. At every wake and after every completed task, run `audit_pipeline.py` and `dispatch_next_work.py --record`. A wait is valid only when both scripts confirm that no executable or recoverable work exists and campaign state contains an evidence-backed next wake trigger. Never use repeated fixed-duration sleep loops. Use `campaign_status.py` for status reports so posting progress, engagement utilization, analytics debt, blockers, and true idle time remain distinct.

## Continuous 24-hour pipeline

Run a continuous dispatcher in Asia/Kolkata time. LinkedIn and offline work may occur throughout the day when evidence supports it. The system alternates short adaptive LinkedIn bursts with investigation, queue replenishment, production, analytics, learning, and recovery. It is never a continuous clicking loop.

Give 9:00 PM-2:00 AM priority to source research, learning-ledger maintenance, experiment registration, and production of exactly two validated packages for the next content day: one India and one US-Central. High-value inbound signals may still interrupt this production block. Do not stockpile a third package.

At each dispatcher cycle, use this order: technical signal or identity blocker; genuine direct inbound; due publication opportunity; mandatory-stage or analytics recovery; qualified soft reciprocity; adaptive-reserve replenishment; two-package production; analytics and investigation. Read [continuous dispatch](references/continuous-dispatch.md) for signal routing, adaptive timing, budget accounting, completion gates, and lane-specific recovery.

Publishing has no fixed time or fixed separation. Run `select_publish_time.py <opportunities> --state-dir <state-dir> --record` against current regional activity, qualified-target activity, topic freshness, network velocity, the previous post's engagement velocity, historical equal-age performance, format/pillar fit, remaining-day opportunity, and cannibalization evidence. Guarantee exactly two verified publications per IST content day; if no strong opportunity appears, use the highest-scoring final remaining opportunity before the day closes.

## Fixed campaign invariants

- Exactly two prepared packages and two verified posts per complete IST content day. Never stockpile a third package.
- Proactive work runs in fully adaptive bursts of at most 10 actions. There is no fixed burst count or fixed interval; opportunity and learned concentration determine the next burst.
- Proactive and soft-reciprocal actions share a 100-action base ceiling. This is a ceiling, not a quota. Execute only candidates scoring at least 65 and never lower quality to fill capacity.
- Genuine direct inbound replies use the base budget until 100, then continue through a separately logged `direct_reply_overage` counter.
- The 3,000-follower qualification gate applies only to new target additions, not direct replies or existing targets.
- Do not initiate proactive engagement with the same person more than once in 72 hours or twice in seven days. Direct inbound conversations are exempt but logged.
- Premium actions count toward the same totals.
- Subscription optimization can reprioritize and configure already-included features, but it cannot purchase, upgrade, start a paid trial, change billing, accept a contract, or alter any fixed campaign invariant.
- Tier 2 and Tier 3 content rules remain active; load the content-production skill for their exact definitions.
- Fact-check every public factual claim.
- Chat previews are informational during active automated mode.
- A technical signal blocks LinkedIn activity. After resolution, cap proactive bursts at five actions for two clean content days, cap the base total at 40 for three additional clean content days, then restore the adaptive 100-action ceiling. Genuine inbound replies remain separately logged.

## Recovery and completion

Use [state and consent](references/state-and-consent.md) to classify failures. Verify ambiguous external outcomes before retrying. Never repeat a post, message, or comment merely because a tool timed out.

At the end of every stage, update the artifacts described in [artifact contracts](references/artifact-contracts.md). Mark the campaign complete only when the configured target formula passes and its evidence is saved.
