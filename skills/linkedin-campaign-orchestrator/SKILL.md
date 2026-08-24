---
name: linkedin-campaign-orchestrator
description: Run Sunny Chandel's persistent organic LinkedIn 10k/10k operating system with Chrome-first pre-flight, fixed windows, state recovery, and auditable execution. Use for complete daily cycles and continued execution toward 10,000 followers and 10,000 connections; do not treat it as an advertising campaign builder.
compatibility: Requires Chrome control, code execution, internet access, and a writable campaign-data directory. Asset cycles require Claude Design and file-upload capabilities.
metadata:
  author: sunny
  version: "0.3.0"
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
- Persistent execution never overrides the fixed daily windows, gaps, action counts, qualification gate, or cooldowns.

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

After Chrome pre-flight passes, continue the existing `sunny-linkedin-10k-10k` state when available. Otherwise initialize `campaign-data/sunny-linkedin-10k-10k/` with `python scripts/init_campaign.py <state-dir>`. Migrate any older blank or generic draft to these fixed defaults. Store discovered values when visible; record temporarily unavailable optional values as unknown and continue.

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

## Pre-flight

Run once before every daily cycle, in this order:

1. Call `list_connected_browsers` and confirm the intended Chrome device. If Chrome is unavailable or the device is wrong, stop and ask Sunny only to connect or select the correct Chrome device.
2. Open LinkedIn in the connected Chrome session and confirm it is logged in as Sunny Chandel by matching the displayed identity and fixed profile URL. If logged out or on the wrong account, stop and ask Sunny only to correct the login.
3. Open Claude Design and confirm its dashboard or projects load. If unavailable, stop and report that exact blocker.
4. Confirm the `file_upload` capability is loaded. Never click a native file-input button directly; locate the input with page-reading tools and use `file_upload` with the local path. The upload cap is 10 MB per call.
5. Inspect the latest available Chrome, Claude Design, computer-use, and upload capabilities needed for the cycle and use the current supported workflow.
6. Inventory active LinkedIn premium entitlements, plan tiers, roles, limits, credits, and expiry information visible in the connected account.
7. Read current followers, connections, profile positioning, recent content, and available analytics from the connected account, and save discovered values to campaign state.
8. Load or initialize campaign configuration, consent, current state, unresolved failures, runtime learning, active experiments, strategy weights, and the Working Algorithm Model.
9. Recalculate target progress. If achieved, save final evidence and mark `completed`; otherwise continue immediately from the next valid pipeline stage.

Any pre-flight failure stops the cycle at that point with no partial run. Do not replace a failed Chrome check with a generic questionnaire.

Do not reopen a locked target during pre-flight. A missing optional goal-tracking feature is not a blocker.

## Automatic skill routing

The owner invokes this parent skill for the complete system. Route to the installed supporting skills without asking the owner to invoke them separately:

- use `linkedin-premium-router` during pre-flight and whenever an entitlement changes;
- use `linkedin-content-research` for source discovery, trend checks, topic selection, and claim verification;
- use `linkedin-content-production` after a research brief is complete;
- use `linkedin-engagement-planning` before every identification pass and engagement window;
- use `linkedin-analytics-learning` for equal-age snapshots, end-of-day logging, experiments, and weekly learning reviews.

Return control to this orchestrator after each supporting stage, update persistent state, and continue from the next valid pipeline stage.

## Daily pipeline

All times are IST.

### Block 0: 9:00 PM-2:00 AM

No LinkedIn access after pre-flight. Research current primary sources and trustworthy trends, update the learning ledger, produce two different post-and-asset packages, and register experiments. Prepare one India package and one US-Central package. Do not stockpile beyond the next pair.

### Window 1: 5:00-6:00 AM

US West Coast evening and Singapore morning. Perform 10 engagement actions. No publishing.

### Identification pass: 6:00-9:00 AM

Prioritize replies to the campaign owner, then hub-account content, adjacency signals, premium insights, and current trends. Apply the new-user qualification gate and cooldown before saving the Window 2 queue.

### Window 2: 9:00-10:30 AM

Publish the India package, verify it is live, perform 10 engagement actions, handle fast replies through approximately 11:00 AM, and log results.

### Midday pass: 11:00 AM-1:30 PM

Check active replies and prepare the UK/EU queue.

### Window 3: 1:30-3:00 PM

Perform 10 UK/EU engagement actions. Capture equal-age analytics and premium insights.

### Afternoon pass: 3:00-7:00 PM

Prepare the US-Central queue and update target lists, response-bank observations, and experiment notes.

### Window 4: 7:00-9:00 PM

Publish the US-Central package, verify it is live, perform 10 engagement actions, handle fast replies through approximately 9:30 PM, pull end-of-day analytics, and update the full log.

## Fixed campaign invariants

- Two posts per complete day and no more than 10 engagement actions in each of four windows.
- Never compensate for missed actions by exceeding a later window.
- Real multi-hour gaps remain intact.
- The 3,000-follower qualification gate applies only to new target additions, not direct replies or existing targets.
- Do not initiate proactive engagement with the same person more than once in 72 hours or twice in seven days. Direct inbound conversations are exempt but logged.
- Premium actions count toward the same totals.
- Tier 2 and Tier 3 content rules remain active; load the content-production skill for their exact definitions.
- Fact-check every public factual claim.
- Chat previews are informational during active automated mode.
- A technical signal is a hard blocker. After resolution, resume at five actions per window unless a newer consent version states otherwise.

## Recovery and completion

Use [state and consent](references/state-and-consent.md) to classify failures. Verify ambiguous external outcomes before retrying. Never repeat a post, message, or comment merely because a tool timed out.

At the end of every stage, update the artifacts described in [artifact contracts](references/artifact-contracts.md). Mark the campaign complete only when the configured target formula passes and its evidence is saved.
