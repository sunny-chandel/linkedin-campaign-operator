---
name: linkedin-campaign-orchestrator
description: Run Sunny Chandel's persistent organic LinkedIn 10k/10k operating system with Chrome-first pre-flight, adaptive engagement, GIF intelligence, profile-derived branding, live skill refresh, state recovery, and auditable execution. Use for complete daily cycles and continued execution toward 10,000 followers and 10,000 connections; do not treat it as an advertising campaign builder.
compatibility: Requires Chrome control, code execution, internet access, and a writable campaign-data directory. Asset cycles require Claude Design and file-upload capabilities.
metadata:
  author: sunny
  version: "0.4.0"
---

# LinkedIn campaign orchestrator

Run the campaign as a stateful pipeline. Treat this skill as the governing layer; use the other installed LinkedIn campaign skills when their descriptions match the current stage.

This is a preconfigured organic profile-growth operating system for Sunny Chandel. It is not an advertising, lead-generation, B2B setup, or generic campaign builder. The locked objective is 10,000 followers and 10,000 connections, with no deadline unless Sunny later sets one. India, US-Central, and UK/EU are the fixed operating regions.

## Non-negotiable operating rules

- Lock the target and automation envelope before entering automated mode.
- Invoking this skill or telling it to start records the recognized owner's consent for the complete fixed system. Do not ask for another setup approval or routine action confirmation.
- Use connected Chrome for LinkedIn pre-flight, reading, publishing, comments, replies, DMs, reactions, and other scheduled campaign actions.
- Any interactive verification, technical signal, access message, wrong login, or identity mismatch is a hard blocker. Stop and tell Sunny exactly what must be corrected.
- Keep system and skill instructions immutable during a campaign. Store learning in runtime state, not in this skill.
- Do not stop after one daily cycle. Continue until verified achievement, explicit user stop, or a hard blocker.
- Persistent execution never overrides the configured action clusters, 80-action daily ceiling, 60-minute proactive-cluster spacing, qualification gate, or cooldowns.

For exact state definitions and recovery rules, read [state and consent](references/state-and-consent.md).

## Startup behavior

Start with Chrome pre-flight. Do not initialize a generic campaign, create a setup visualization, display an onboarding questionnaire, produce a marketing brief, or ask for configuration before checking Chrome.

The package already fixes these values; never ask for them during startup:

- owner: Sunny Chandel;
- objective: organic profile growth to 10,000 followers and 10,000 connections;
- deadline: none;
- timezone: Asia/Kolkata;
- regions: India, US-Central, and UK/EU;
- daily schedule, action limits, qualification rule, cooldowns, and content voices defined below.

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

Completing Window 4 ends the daily cycle, not the campaign.

## Live instruction refresh

At pre-flight and before every scheduled stage, run `python ${CLAUDE_SKILL_DIR}/scripts/resolve_latest_plugin.py --session-version 0.4.0`. If a newer installed version exists, use `/reload-plugins` in the active session when callable. Otherwise read the returned latest orchestrator and required supporting skill files completely, record the direct-loaded version in campaign state, revalidate state, and continue from the last confirmed stage without repeating external actions.

Read [runtime plugin refresh](references/runtime-refresh.md) for the exact version-resolution, reload, direct-load, and component-boundary behavior.

## Pre-flight

Run once before every daily cycle, in this order:

1. Call `list_connected_browsers` and confirm the intended Chrome device. If Chrome is unavailable or the device is wrong, stop and ask Sunny only to connect or select the correct Chrome device.
2. Open LinkedIn in the connected Chrome session and confirm it is logged in as Sunny Chandel by matching the displayed identity and fixed profile URL. Read the current profile name, handle, headline, image, niche, and visible positioning. If logged out or on the wrong account, stop and ask Sunny only to correct the login.
3. Open Claude Design and confirm its dashboard or projects load. If unavailable, stop and report that exact blocker.
4. Confirm the `file_upload` capability is loaded. Never click a native file-input button directly; locate the input with page-reading tools and use `file_upload` with the local path. The upload cap is 10 MB per call.
5. Inspect the latest available Chrome, Claude Design, computer-use, and upload capabilities needed for the cycle and use the current supported workflow.
6. Run `linkedin-brand-system`. Reuse a valid profile-matched watermark kit or create and validate it in Claude Design, then make it active automatically.
7. Run `linkedin-premium-router` to inventory active LinkedIn paid entitlements, plan tiers, roles, limits, credits, and expiry information; calculate `subscription-utilization-plan.json`; and complete eligible setup for already-included features.
8. Read current followers, connections, recent content, and available analytics from the connected account, and save discovered values to campaign state.
9. Load or initialize campaign configuration, consent, current state, unresolved failures, runtime learning, active experiments, strategy weights, creator registry, GIF pattern library, and the Working Algorithm Model.
10. Recalculate target progress. If achieved, save final evidence and mark `completed`; otherwise continue immediately from the next valid pipeline stage.

Any hard-blocking pre-flight failure stops the cycle at that point with no partial run. Recoverable or optional pre-flight gaps use the automatic fallback rules, are recorded as `unknown` when necessary, and do not stop the cycle. Do not replace a failed Chrome check with a generic questionnaire.

Do not reopen a locked target during pre-flight. A missing optional goal-tracking feature is not a blocker.

## Automatic skill routing

The owner invokes this parent skill for the complete system. Route to the installed supporting skills without asking the owner to invoke them separately:

- use `linkedin-premium-router` during pre-flight, whenever an entitlement changes, before a stage that depends on a paid feature, and during the weekly retrospective;
- use `linkedin-brand-system` during pre-flight and before every GIF export;
- use `linkedin-gif-creative-intelligence` during daytime creator observation and before every GIF production stage;
- use `linkedin-content-research` for source discovery, trend checks, topic selection, and claim verification;
- use `linkedin-content-production` after a research brief is complete;
- use `linkedin-engagement-planning` before every identification pass and engagement window;
- use `linkedin-analytics-learning` for equal-age snapshots, end-of-day logging, experiments, and weekly learning reviews.

Return control to this orchestrator after each supporting stage, update persistent state, and continue from the next valid pipeline stage.

Automated mode is execution, not a planning conversation. Never ask whether to run a required supporting skill, prerequisite, pre-flight step, recovery step, queue, analysis, or content stage. Do not ask questions such as “want me to run research and production?” Announce the stage as a status update and execute it immediately. Ask Sunny only for the exact intervention required to clear a hard blocker defined in this skill.

If a required publication package is missing, incomplete, stale, or invalid, automatically run its missing prerequisites in dependency order: `linkedin-content-research` → `linkedin-content-production` → publication-package validation. The research and production backfill may run outside Block 0 because it does not touch LinkedIn. It must not move publishing or engagement outside their fixed windows, increase action counts, or create more than the next required India and US-Central pair. If the package becomes valid while its publishing window is still open, continue directly to publication without requesting approval. If the window closes first, record the missed publish and prepare the next valid package; do not compensate outside the schedule.

Every supporting skill inherits the active consent and automation state from this parent. A subskill must never create an onboarding step, request routine approval, ask the owner to invoke another skill, or return a “what should I do next?” choice. Resolve missing non-sensitive inputs in this order: read persistent state, inspect the connected account or existing artifacts, derive from verified evidence, then use the fixed campaign default or record `unknown`. Regenerate missing or invalid artifacts from the nearest valid upstream artifact. Use a documented base-flow fallback when an optional tool, metric, source, or premium feature is unavailable. Return a structured result to this orchestrator after every stage, including partial results and recovery notes, so the pipeline always advances or enters an explicit lifecycle state.

For recoverable failures, save state, verify the last observable outcome, retry safely up to the configured limit, select the best valid fallback, and continue without asking. Never terminate merely because a preferred source, candidate, metric, asset format, or premium feature is unavailable. Only `hard-blocked`, `completed`, or `user-stopped` may halt execution. When waiting for the next fixed window, use an available scheduling or wait mechanism and continue from stored state; do not ask the owner to restart the pipeline.

## Daily pipeline

All times are IST.

### Block 0: 9:00 PM-2:00 AM

No LinkedIn access after pre-flight. Research current primary sources and trustworthy trends, update the learning ledger, produce two different post-and-asset packages, and register experiments. Prepare one India package and one US-Central package. Do not stockpile beyond the next pair.

### Cluster 1: 5:00-5:45 AM

US West Coast evening and Singapore morning. Perform 10 engagement actions. No publishing.

### Identification pass: 6:00-9:00 AM

Prioritize replies to the campaign owner, then hub-account content, adjacency signals, subscription-utilization-plan features, and current trends. Apply the new-user qualification gate and cooldown before saving the Window 2 queue.

### Cluster 2: 7:00-7:30 AM

During the identification pass, run the first adaptive gap cluster with up to 10 highest-scoring qualified actions.

### Window 2 and Cluster 3: 9:00-10:00 AM

Ensure the India package exists using the automatic missing-package recovery rule above. Publish at approximately 9:00, verify it is live, run up to 10 actions from 9:10-10:00, handle genuine inbound replies through approximately 11:00 AM, and log results.

### Cluster 4 and midday pass: 11:30 AM-12:00 PM

Check active replies, run up to 10 highest-scoring qualified actions, and prepare the UK/EU queue.

### Cluster 5: 1:30-2:20 PM

Perform 10 UK/EU engagement actions. Capture equal-age analytics and paid-feature usage and outcomes.

### Creative observation pass: 3:00-4:00 PM

Run `linkedin-gif-creative-intelligence` against 12 core and eight rotating creators. Store qualified GIF references for the next content cycle.

### Cluster 6: 4:00-4:30 PM

Run up to 10 highest-scoring qualified actions.

### Cluster 7: 5:30-6:00 PM

Run up to 10 highest-scoring qualified actions with US East and US-Central relevance.

### Afternoon pass: 6:00-7:00 PM

Prepare the US-Central queue and update target lists, response-bank observations, and experiment notes.

### Window 4 and Cluster 8: 7:00-9:00 PM

Ensure the US-Central package exists using the automatic missing-package recovery rule above. Publish at approximately 7:00, verify it is live, run up to 10 actions from 7:45-8:30, handle genuine inbound replies through approximately 9:00 PM, pull end-of-day analytics, update paid-feature usage and remaining capacity, and update the full log.

## Fixed campaign invariants

- Two posts per complete day, no more than 10 actions in a proactive cluster, and no more than 80 total engagement actions per day.
- Eight proactive clusters are available, with at least 60 minutes between the end of one cluster and the start of the next. Genuine inbound replies are event-driven, count toward the daily ceiling, and reduce later proactive capacity.
- The 80-action value is an adaptive ceiling, not a quota. Execute only candidates scoring at least 65 through `linkedin-engagement-planning` and never compensate for skipped actions.
- The 3,000-follower qualification gate applies only to new target additions, not direct replies or existing targets.
- Do not initiate proactive engagement with the same person more than once in 72 hours or twice in seven days. Direct inbound conversations are exempt but logged.
- Premium actions count toward the same totals.
- Subscription optimization can reprioritize and configure already-included features, but it cannot purchase, upgrade, start a paid trial, change billing, accept a contract, or alter any fixed campaign invariant.
- Tier 2 and Tier 3 content rules remain active; load the content-production skill for their exact definitions.
- Fact-check every public factual claim.
- Chat previews are informational during active automated mode.
- A technical signal is a hard blocker. After it is resolved, disable gap clusters, run the four original windows at five actions for two clean cycles, return to 40 actions for three clean cycles, then restore the adaptive ceiling unless a newer consent version states otherwise.

## Recovery and completion

Use [state and consent](references/state-and-consent.md) to classify failures. Verify ambiguous external outcomes before retrying. Never repeat a post, message, or comment merely because a tool timed out.

At the end of every stage, update the artifacts described in [artifact contracts](references/artifact-contracts.md). Mark the campaign complete only when the configured target formula passes and its evidence is saved.
