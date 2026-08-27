---
name: linkedin-campaign-orchestrator
description: Run the complete persistent organic LinkedIn growth system with rolling 24-hour engagement and publishing contracts, regional diversification, research, content production, analytics, runtime repair, and crash-safe continuation. Use this as the only public entry point; do not turn it into an advertising-campaign questionnaire.
metadata:
  author: sunny
  version: "6.0.0-rc.1"
---

# LinkedIn campaign orchestrator

Run the campaign as a durable pipeline. This parent is the only owner-facing entry point. Route all child work automatically and return control here after each child result.

## Startup contract

Invoke as `/linkedin-campaign-orchestrator Resume <state-dir> from durable state and execute the dispatcher.` Never replace startup with a marketing form or ask for discoverable profile, niche, target, region, deadline, or baseline information.

Resolve the newest installed plugin at every wake with `scripts/resolve_latest_plugin.py`. If newer, load the returned parent and every relevant child `SKILL.md` completely, activate that installation, migrate state, and resume from the last confirmed checkpoint without repeating an external action.

When state exists, run in order:

1. `python scripts/resume_campaign.py <state-dir> --session-id <session-id>`
2. `python scripts/audit_pipeline.py <state-dir> --write`
3. `python scripts/operational_output.py <state-dir>`
4. `python scripts/dispatch_next_work.py <state-dir> --record`
5. Execute the leased task, persist evidence, then repeat from step 2.

When state does not exist, discover the connected profile identity, timezone, niche, baselines, content positioning, entitlements, and capabilities read-only. Initialize with `scripts/init_campaign.py`; do not ask for information visible in Chrome or existing artifacts.

## One-time consent

If no valid receipt exists, tell the recognized owner that pre-flight will run and the configured campaign will then operate autonomously. Ask one direct consent question. On approval, store it with `runtime_control.py consent-grant`. Reload that campaign-lifetime receipt across restarts, context compression, Claude, Codex, and compatible agents. Do not ask routine approvals again unless the receipt is revoked, missing or invalid, or the verified account identity changes.

## Pre-flight and repair

Reuse unexpired pre-flight evidence. Recheck only missing, expired, changed, or failed components:

1. Resolve the pinned Chrome device and verify the stored profile identity.
2. Confirm the LinkedIn session is usable.
3. Confirm Claude Design is usable.
4. Confirm file upload is available; locate the file input semantically and upload by path.
5. Inspect current Chrome, Claude Design, computer-use, and upload capability routes.
6. Route to `linkedin-brand-system`; create or validate the profile-derived watermark.
7. Route to `linkedin-premium-router`; inventory and configure already-included features.
8. Capture visible profile baselines, recent content, analytics, and account signals.
9. Load every canonical state, queue, evidence, analytics, learning, experiment, subscription, brand, and repair artifact.
10. Recalculate targets and rolling operational output.

Capability failure routes to `linkedin-runtime-repair`. Preserve the active task checkpoint and verify whether an external mutation already occurred. Try current-agent computer use, reopen or rebind the application, and rerun only the failed pre-flight component. If unresolved, run `codex doctor --json`, then create a scoped ephemeral Codex repair task. Codex may recover the application or session, repair deterministic campaign state, or reinstall the already-approved plugin version. It may not modify skill instructions, source code, Git history, or publish content. Continue unaffected work and retry automatically when Codex is unavailable.

## Rolling operational contracts

- Count confirmed proactive actions, soft reciprocity, reactions, comments, follows, connections, and relationship-qualified outbound DMs from `interaction-log.jsonl` over the preceding 24 hours.
- Maintain at least 160 qualified counted actions and never exceed 200 in any rolling 24 hours.
- Genuine direct inbound replies are additional, remain outside the 200 cap, and continue when useful.
- Keep each proactive burst at 10 or fewer. One eligible canonical candidate is enough to create a burst.
- Keep at least 40 currently executable records in `engagement-opportunities.json`; no counter may claim supply without canonical records.
- Maintain at least six and at most eight verified publications in the preceding 24 hours, calculated from `publication-evidence.jsonl`.
- Maintain six validated unpublished normal packages and replenish one after every publication.
- Apply an absolute 120-minute publication-spacing floor.
- Outage deficits remain open as action or post debt. Recover them without exceeding the rolling caps or duplicating activity.

Growth in impressions, profile views, connections, and followers is measured and optimized. Never represent those growth outcomes as guaranteed.

## Dispatcher order

At every wake and after every task, choose the highest-value eligible work:

1. Runtime repair, identity failure, or active external-outcome ambiguity.
2. Genuine direct inbound.
3. Due publication or publishing-debt recovery.
4. Mandatory stage or analytics recovery.
5. Canonical engagement burst execution.
6. Opportunity discovery until executable reserve reaches 40.
7. Regional allocation and six-package replenishment.
8. Scheduled 30-minute, 2-hour, 6-hour, or 24-hour analytics.
9. Research, experiments, creator intelligence, subscription utilization, and learning.
10. Wait only when no validated work is executable.

Do not select the same non-urgent task type more than twice when another type is eligible. A low-yield discovery source receives its own exact backoff; immediately rotate to another source while action debt remains. Never enter a generic reconciliation or fixed-duration sleep loop.

Every wait must include evidence, unfinished-work count, predicted opportunity, exact wake trigger, and one continuation contract. Arm or update exactly one campaign-deduplicated automation. Renew it before any host duration limit until verified target completion or explicit owner stop. Never ask the owner to choose an automation, timer, heartbeat, or manual check-back.

## Automatic child routing

Route without owner questions:

- `linkedin-opportunity-discovery`: rotate sources and atomically maintain canonical candidates.
- `linkedin-engagement-planning`: score candidates and apply active recovery gates.
- `linkedin-engagement-execution`: build and account for rolling-quota bursts and relationship-only outbound DMs.
- `linkedin-regional-intelligence`: allocate four core and two exploration slots after bootstrap evidence.
- `linkedin-content-research`: discover at least 12 candidate topics and verify claims.
- `linkedin-content-production`: produce the six selected captions and assets.
- `linkedin-publishing-operations`: validate inventory, select timing, verify live publication, and schedule analytics.
- `linkedin-analytics-learning`: complete snapshots, learning, decision, experiment, and next trigger.
- `linkedin-brand-system`: maintain and apply the watermark kit.
- `linkedin-gif-creative-intelligence`: observe and learn reusable creative patterns.
- `linkedin-premium-router`: use already-included subscription capability where it improves the pipeline.
- `linkedin-runtime-repair`: restore unhealthy capabilities and resume the leased task.

Child skills inherit consent and never create onboarding, ask the owner to invoke another skill, or offer a “what next?” choice. Missing optional information is read from state, discovered, derived, defaulted, or recorded as unknown.

## Opportunity discovery and engagement

Rotate by measured 70/20/10 source allocation through direct inbound, own-post audiences, existing targets and hubs, hub audiences, regional searches, premium signals, second-degree and accepted connections, creators, adjacency topics, and fresh technical discussions.

Recovery tiers remain exact:

- normal: score 65, 3,000 followers for new targets, 72-hour cooldown;
- expansion: 60, 2,000, 48 hours;
- intensive: 55, 1,000, 24 hours.

Never go below intensive. Keep the maximum of two proactive interactions per person in seven days. Direct inbound is exempt. Proactive DMs require an existing connection and stored prior-interaction evidence. Candidate execution outranks another search. After every burst, atomically update candidate lifecycle, interaction evidence, rolling output, concentration, source yield, relationship strength, and next prediction.

## Six-post content engine

Maintain at least 12 scored candidate topics, select six distinct research briefs, then build six validated packages. Every brief records region, demographic hypothesis, freshness expiry, portfolio role, competing angle, and intended growth outcome. Every package must complete research, claim verification, caption, asset, watermark, validation, publication decision, live verification, analytics, and learning.

Bootstrap allocation is two India, two United States, one UK/EU, and one APAC post. After sufficient evidence, retain four core-region and two exploratory-region slots while keeping at least one India and one US post. Each six-post portfolio uses at least four content pillars and three format treatments. Do not repeat topic, angle, or format consecutively.

Select exact publication timing from regional activity, qualified-target activity, freshness, network velocity, prior-post velocity, equal-age history, format and pillar history, cannibalization, and rolling post debt. The six normal posts are mandatory. Up to two recovery posts may be published one at a time, with at most one unpublished recovery package. Revalidate freshness after an outage and regenerate stale content.

## Analytics and learning

Measure every verified post at 30 minutes, 2 hours, 6 hours, and 24 hours. Track impressions, engagement rate, profile views, follower and connection growth, audience location, seniority, topic, format, timing, and regional spillover. Apply learning continuously to regional, topic, timing, format, action-type, source-yield, and follower-conversion models using 70/20/10 proven, promising, and exploration allocation.

Analytics completion requires all four: snapshot, provisional or validated learning, experiment or explicit no-change decision, and next measurement trigger. Store learning in runtime artifacts; never rewrite this skill during a campaign.

## State integrity and completion

`engagement-opportunities.json`, `interaction-log.jsonl`, and `publication-evidence.jsonl` are canonical for supply and output. `operational-output.json`, `content-pipeline.json`, `regional-performance.json`, and `repair-state.json` are derived durable controllers. Use leases and idempotency keys. Verify ambiguous outcomes before retrying. Preserve confirmed history, consent, experiments, analytics, subscription state, and watermark assets through migration and restart.

Mark the campaign `completed` only when the configured follower and connection target formula passes with saved evidence. Meeting the rolling operational contracts completes the current operating obligation, not the campaign.
