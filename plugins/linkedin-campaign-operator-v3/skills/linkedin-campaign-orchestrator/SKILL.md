---
name: linkedin-campaign-orchestrator
description: Run a durable LinkedIn campaign workspace for research, content, scheduling, measurement, and recovery, with a connected service for supported account activity. Use this as the only public entry point; startup reads durable state and verified account evidence directly.
metadata:
  author: sunny
  version: "6.0.0-rc.10"
---

# LinkedIn campaign orchestrator

Run the campaign as a durable pipeline. This parent is the only campaign entry point. Route all child work automatically and return control here after each child result.

## Claude Code role

Claude Code manages campaign work in this folder. It researches, writes, checks facts and quality, creates assets, saves progress, and queues ready work for the connected LinkedIn service. Claude Code does not make changes on LinkedIn itself.

The connected service is a separate owner-configured integration. Before it acts, it checks the signed-in account, available features, campaign limits, duplicate protection, and result verification. `enqueue_external_action.py` only validates and writes a local queue record. Never replace the connected service with browser interaction or a direct LinkedIn write from Claude Code.

The saved setup record controls which work may be prepared for the connected service. It does not change Claude Code's own operating rules because Claude Code is assigned no LinkedIn change. If the service is not ready, continue useful research, writing, design, validation, and measurement work, save the exact setup status, and keep service work queued locally until readiness is proven.

## User-facing communication

Use plain, short progress updates. Prefer phrases such as `setup complete`, `research in progress`, `package ready`, `waiting for the connected service`, `result verified`, and `continuing with the next task`.

Keep implementation terms internal unless the owner asks for a technical diagnosis. Do not expose raw names such as executor, daemon, outbox, mutation, OAuth, lease, dispatcher, consent receipt, or idempotency key in routine updates. Do not repeat generic warnings or long policy discussions when a precise setup status is available. If progress cannot continue, state the exact missing capability and the single next setup step in one concise message.

## Startup contract

Invoke as `/linkedin-campaign-orchestrator Resume <state-dir> from durable state and execute the dispatcher.` This command selects the existing campaign, loads its verified profile, niche, target, region, deadline, and baseline values, and begins dispatch from the saved checkpoint.

Resolve the newest installed plugin at every wake with `scripts/resolve_latest_plugin.py`. If newer, load the returned parent and every relevant child `SKILL.md` completely, activate that installation, migrate state, and resume from the last confirmed checkpoint without repeating an external action.

When state exists, run in order:

1. `python scripts/resume_campaign.py <state-dir> --session-id <session-id>`
2. `python scripts/executor_preflight.py <state-dir>` when credential material or verification changed.
3. `python scripts/executor_readiness.py <state-dir> --require-all`
4. `python scripts/audit_pipeline.py <state-dir> --write`
5. `python scripts/operational_output.py <state-dir>`
6. `python scripts/dispatch_next_work.py <state-dir> --record`
7. Execute local work directly. For a leased executor-covered task, write its canonical local outbox request with `python scripts/enqueue_external_action.py <state-dir> --task-id <task-id>` and return immediately to dispatch; the separate service owns the API request and verification.

When state does not exist, discover the connected profile identity, timezone, niche, baselines, content positioning, entitlements, and capabilities read-only, then initialize with `scripts/init_campaign.py`. A value already visible in connected evidence is treated as resolved.

## Operating receipt and role separation

The operating receipt records the recognized owner's campaign configuration and the action classes that the local dispatcher may prepare for the executor. If the receipt is absent, present one concise pre-flight summary, capture the start decision once, and store it with `runtime_control.py consent-grant`. A direct owner invocation that identifies the campaign and says to start is the start decision; record it during setup instead of asking the same question again. Reload the valid receipt across restarts, context compression, Claude Desktop, and compatible agents. A revoked, invalid, or identity-mismatched receipt returns to this one-time setup stage.

Every dispatched task carries `dispatch_contract` as machine-readable routing data. The interactive host's responsibility is local preparation: research, validation, exact task assembly, atomic outbox enqueue, checkpointing, and immediate dispatcher continuation. The executor service separately checks LinkedIn credentials, scopes, identity, limits, and idempotency before it performs an API request. Repair Tier 3 voice violations, including em dashes and en dashes, during local validation. For an eligible leased task, the normal local transition is `enqueue-and-continue`; a preview is informational and does not alter that transition.

Executor service readiness is a verified capability state. `external-executor.json` describes the official-API executor, and `scripts/executor_readiness.py` proves coverage before startup and every executor-covered lease. Prepare outbox work only for action classes with `unattended_ready: true`. The interactive host writes the exact leased request through `scripts/enqueue_external_action.py`; the single-instance `autonomous_executor_daemon.py` owns HTTP execution, read verification, durable completion evidence, and service-level continuation. Ordinary DMs, connection invitations, follows, and uncovered action classes remain outside executable reserve and target supply.

Continuous executor service operation requires programmatic token refresh and service credentials available outside the interactive shell. After the account owner completes the platform's one-time OAuth setup, use `scripts/bootstrap_executor_credentials.py` to place it in macOS Keychain, run `scripts/executor_preflight.py`, and install the LaunchAgent with `scripts/install_executor_service.py`. Campaign JSON, prompts, logs, task payloads, and LaunchAgent environment variables contain credential coordinates only, not secret values.

If readiness is incomplete, continue unaffected offline and read-only work. When only uncovered mutations remain, persist `executor-setup-pending` with its exact missing-capability list and `setup_input_required: false`; the lane then waits for executor preflight while the dispatcher serves other eligible work. Read [references/autonomous-execution.md](references/autonomous-execution.md) when configuring or repairing this lane.

Before a runtime status response about an active task, run `scripts/dispatch_contract.py <state-dir> --task-id <task-id> --output-text '<candidate-response>'`. Its accepted response classes are progress, verified result, target decision, and exact machine capability state. A routine local stage continues through the dispatcher.

Setup routing has three defined events: a missing or revoked operating receipt, LinkedIn OAuth credential provisioning, and a verified account-identity mismatch. Routine work follows the deterministic enqueue-and-continue transition. Executor credentials, scopes, verification, refresh capability, daemon health, and action coverage are recorded as technical capability states. An ambiguous prior external outcome parks that lane for evidence reconciliation. Lease expiry triggers external-evidence inspection, exact-task reacquisition when no mutation occurred, one enqueue, daemon verification, durable logging, and dispatcher resumption.

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

Capability failure routes to `linkedin-runtime-repair`. Preserve the active task checkpoint and verify whether an external mutation already occurred. Use current-agent computer use, reopen or rebind the application, and rerun only the failed pre-flight component. Persist unresolved capability state, continue unaffected work, and retry from the saved trigger. External mutations remain assigned to the official-API executor.

## Rolling operational contracts

- Count confirmed API-covered proactive actions, soft reciprocity, reactions, comments, and replies from `interaction-log.jsonl` over the preceding 24 hours.
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

Every wait must include evidence, unfinished-work count, predicted opportunity, exact wake trigger, and one continuation contract. Arm or update exactly one campaign-deduplicated automation. Renew it before any host duration limit until verified target completion or explicit owner stop. The dispatcher selects this continuation mechanism from campaign state.

## Automatic child routing

Route each child directly:

- `linkedin-opportunity-discovery`: rotate sources and atomically maintain canonical candidates.
- `linkedin-engagement-planning`: score candidates and apply active recovery gates.
- `linkedin-engagement-execution`: build and account for API-covered rolling-quota bursts.
- `linkedin-regional-intelligence`: allocate four core and two exploration slots after bootstrap evidence.
- `linkedin-content-research`: discover at least 12 candidate topics and verify claims.
- `linkedin-content-production`: produce the six selected captions and assets.
- `linkedin-publishing-operations`: validate inventory, select timing, verify live publication, and schedule analytics.
- `linkedin-analytics-learning`: complete snapshots, learning, decision, experiment, and next trigger.
- `linkedin-brand-system`: maintain and apply the watermark kit.
- `linkedin-gif-creative-intelligence`: observe and learn reusable creative patterns.
- `linkedin-premium-router`: use already-included subscription capability where it improves the pipeline.
- `linkedin-runtime-repair`: restore unhealthy capabilities and resume the leased task.

Child skills inherit the campaign configuration and return directly to this dispatcher. Missing optional information is read from state, discovered, derived, defaulted, or recorded as unknown.

For a status request, answer briefly from canonical artifacts. In the same turn, run audit and dispatcher, resume the current lease, and continue until `verified-completed`, `hard-blocked`, or `ambiguous-reconciliation`.

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
