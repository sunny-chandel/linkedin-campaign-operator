# Changelog

## 6.0.0-rc.27 — Host-Supported Hourly Continuation

- Uses the fastest persistent cadence accepted by Claude Desktop Routines: hourly.
- Retains the read-only due gate and create-once routine contract from rc.26.
- Allows for the host's documented randomized schedule delay when validating wake latency.

## 6.0.0-rc.26 — Create-Once Recurring Continuation

- Replaces per-wait one-time schedule updates with one recurring Claude Desktop Routine.
- Adds a read-only due gate so early recurring checks finish without changing campaign state.
- Prevents concurrent work by deferring while a live task lease exists and recovers expired leases when due.
- Keeps the recurring schedule unchanged at later waits, avoiding the host's always-confirm scheduled-task update control.

## 6.0.0-rc.25 — Compact Model Context

- Projects campaign-cycle output down to the current task, transition, and essential evidence instead of exposing nested runtime diagnostics.
- Keeps raw configuration, internal counters, service schemas, and unrelated historical logs out of child and continuation prompts.
- Requires fresh prompts to use current owner instructions and verified durable evidence without fabricating prior agreement or reproducing earlier conversation history.

## 6.0.0-rc.24 — Persistent Desktop Continuation

- Require the campaign continuation to survive the current Claude session.
- Select the persistent Claude Desktop Routine/scheduled-task adapter as the sole accepted continuation host.
- Return the preferred host capability and persistence requirement directly in the wait transition.
- Treat session cron and in-session loops as incomplete continuation attempts rather than durable success.
- Migrate existing campaign configuration to the persistent-adapter contract and add regression coverage.

## 6.0.0-rc.23 — Explicit Local Campaign Scope

- Define the owner start receipt and host continuation as automatic local-workspace operation only.
- State prominently that later account-activity capability changes never broaden the local receipt into future account changes.
- Return a machine-readable campaign-scope contract with scope confirmation already resolved.
- Remove obsolete LinkedIn mutation classes and high-volume activity settings from the public consent template and migration output.
- Reframe service configuration as a separate input whose authorization is never inferred from the campaign start.

## 6.0.0-rc.22 — Initializer-Pinned Browser Verification

- Accept the supplied Chrome device ID, label, and platform in the initializer and persist them before profile verification.
- Return a machine-readable profile-verification contract that selects the exact device directly and resolves routine setup input.
- Make connected-browser discovery unnecessary when a pinned device ID is already available.
- Add clean-start regression coverage for the persisted pending binding, direct-selection contract, and verified transition.

## 6.0.0-rc.21 — Deterministic Host Continuation

- Return one machine-readable continuation transition at every durable wait, including the stable task ID, dedupe key, wake time, prompt, and success-record command.
- Mark that transition `execute-now` with owner reply and setup input explicitly resolved by the active campaign-lifetime receipt.
- Direct Claude Code to create or update the same host-native schedule immediately and save its returned automation ID.
- Preserve the host's own required tool-permission control as the only possible one-time UI gate.
- Add regression coverage for the full wait-to-continuation contract.

## 6.0.0-rc.20 — Fixed Public Startup Surface

- Limit model-facing startup to resolver, initializer, runtime control, and campaign-cycle entry points.
- Remove service provisioning, credential bootstrap, direct account-action, enqueue, installer, and background-runner implementations from the public plugin package.
- Rename remaining capability libraries with neutral status-oriented names and make the public preflight command return a concise available/unavailable result.
- Define `unavailable` as a complete setup result that selects all available campaign lanes without presenting a mode choice.
- Add a release test that prevents removed setup surfaces from returning to the public scripts directory.

## 6.0.0-rc.19 — Single Durable Wait After Health Refresh

- Treat a deferred publication decision's `next_evaluation_at` as a first-class wake so both its publication task and evaluation task leave the immediate reconciliation set.
- Restore a completed health task if a stale lease is encountered and prevent the dispatcher from re-leasing the same completed task.
- Reuse the earliest durable wake, or the configured automatic heartbeat when no timed task exists, after the daily health refresh finds no executable work.
- Add a regression test that dispatches the same completed-health state twice and verifies a stable wait with no task lease.

## 6.0.0-rc.18 — Complete Inventory Before Transition

- Validates the configured topic-candidate, brief, and ready-package counts inside the durable completion command.
- Returns exact missing counts when content replenishment is incomplete instead of letting the audit silently reopen it.
- Makes the production skill read task-provided inventory targets before it begins parallel research.

## 6.0.0-rc.17 — Direct Verified Browser Binding

- Uses a verified Chrome device ID from the current start message or saved campaign binding directly in browser calls.
- Skips connected-browser discovery when that stable ID is available, avoiding the host picker that discovery requires.
- Preserves the rc.16 durable checkpoint, completion, redispatch, and recorded-wait flow.

## 6.0.0-rc.16 — Deterministic Browser and Task Transitions

- Added exact runtime commands to each dispatched task for checkpoints, durable completion, and immediate redispatch.
- Made fresh local browser selection deterministic and required the verified device binding to be saved immediately after initialization.
- Required preflight completion to be recorded through the runtime event command so a completed setup step cannot remain leased.

## 6.0.0-rc.15 — Portable Readiness Checks

- Kept credential readiness evidence-based when the host does not provide the macOS Keychain command.
- Preserved the rc.14 deterministic clean-start cycle while making its validation portable across Claude and CI hosts.

## 6.0.0-rc.14 — Deterministic Clean Start

- Added one script-driven campaign cycle for migration, validation, recovery, audit, and next-task dispatch.
- Added explicit clean-start support for follower-growth and impression-window goals with a campaign deadline.
- Made a current owner start request record campaign scope once, while keeping service availability evidence-based.
- Required every saved task transition to return immediately to the deterministic cycle instead of ending from conversational judgment.

## 6.0.0-rc.13 — Deterministic Routine Setup

- Added evidence-driven startup rules for profile binding, campaign goals, optional settings, and connected-service availability.
- Made packaged defaults and explicit unknown values the normal fallback for optional setup fields.
- Prevented optional cadence, secondary-goal, device, and service-identification questions from stopping the next useful local task.

## 6.0.0-rc.12 — Clear Internal Campaign Instructions

- Reworked the orchestrator and child skill bodies around a simple local-workspace and connected-service boundary.
- Removed fixed high-volume activity language and service implementation setup from model-facing instructions.
- Replaced fixed batch assumptions with campaign-configured pacing, inventory, cooldown, and quality rules.
- Simplified recovery, work selection, engagement planning, publishing, and analytics guidance.
- Added regression coverage for every model-facing Markdown surface.

## 6.0.0-rc.11 — Plain-Language Public Plugin Surfaces

- Rewrote the marketplace card, plugin summaries, and every skill summary in short, calm language.
- Removed internal implementation terms and activity counts from public descriptions while preserving the underlying campaign behavior.
- Added a release check that prevents technical wording from returning to public plugin descriptions.

## 6.0.0-rc.10 — Plain-Language Claude Code Experience

- Rewrote the public Claude Code role and connected-service boundary in calm, plain language.
- Added a user-facing communication contract that keeps internal implementation terms out of routine updates.
- Replaced generic warnings and long technical explanations with concise capability status and one exact next setup step.

## 6.0.0-rc.9 — Explicit Interactive-Host Boundary

- Made the responsibility boundary explicit at the top of the public orchestrator: the interactive host performs local preparation and outbox writes only, while the separate official-API service owns every externally visible change.
- Clarified that the operating receipt configures dispatcher eligibility and does not replace host action-confirmation rules.
- Added release-contract coverage that prohibits browser or direct interactive-host write fallbacks.

## 6.0.0-rc.8 — Calm Unattended Runtime

- Replaced legacy interactive-control fields with neutral operating receipts, deterministic dispatch contracts, and executor readiness states.
- Removed the Codex repair path from the campaign runtime; application recovery is local and external mutations remain assigned to the official LinkedIn API executor.
- Added migration cleanup for legacy control keys in campaign state, executor state, consent records, and queued tasks so fresh Claude sessions cannot inherit the earlier interaction loop.

## 6.0.0-rc.7 — System Install Refresh

- Publishes the complete 13-skill repair as a distinct package version so Claude Desktop cannot reuse the earlier installation record.
- Keeps the neutral enqueue-and-dispatch role separation introduced in rc.5 and the clean-state migration introduced in rc.6.
- Preserves campaign state, action evidence, executor queues, and idempotency contracts during reinstall.

## 6.0.0-rc.6 — Clean-State Migration

- Normalized existing campaign configuration to the neutral `unattended-official-api` mode during migration so fresh Claude sessions receive the same rc.5 responsibility model as newly initialized campaigns.

## 6.0.0-rc.5 — Neutral Interactive Context

- Reframed Claude-facing instructions around a calm separation of responsibilities: the interactive task prepares and enqueues canonical work, while the official-API service owns mutation and verification.
- Removed adversarial approval, observer, permission, and policy-debate wording from skill context and replaced it with deterministic dispatcher transitions and machine-readable setup states.
- Kept Codex outside the normal operating loop; Codex is now described only as an exceptional local repair path for broken capability or plugin updates.

## 6.0.0-rc.4 — Supervised Autonomous API Runtime

- Added a durable external-action outbox and single-instance executor daemon so Claude enqueues canonical work while a local LaunchAgent performs and verifies covered LinkedIn API mutations without per-action chat approval.
- Added macOS Keychain credential storage, programmatic access-token refresh, token introspection, actor and scope preflight, and a fail-closed service installer that refuses to start until unattended readiness is proven.
- Migrated reactions to LinkedIn's current Reactions API, added image upload and availability polling for media publications, and made uncertain post-mutation failures permanently ambiguous instead of automatically retrying.

## 6.0.0-rc.3 — Zero-Human Capability-Gated Execution

- Replaced the observer review bridge with a verified autonomous-executor contract; no person, observer, or host-interactive fallback is permitted while the campaign runs.
- Added deterministic readiness and official LinkedIn API execution helpers with action-class coverage, scope and identity evidence, idempotency, external verification, and ambiguous-outcome protection.
- Dispatcher supply now excludes uncovered mutations and returns `autonomous-executor-unavailable` instead of an approval prompt or loop, while unaffected offline and read-only work continues.

## 6.0.0-rc.2 — Deterministic Routine-Action Authorization

- Added a machine-readable authorization contract to every dispatched task so active campaign-lifetime consent deterministically preapproves qualified routine LinkedIn actions.
- Added an output guard that rejects approval-seeking responses such as “Post this?” and requires immediate execution, verification, durable logging, and dispatcher resumption.
- Made lease expiry and owner status questions non-terminal: reconcile exactly-once evidence, reacquire the same task, and continue automatically.
- Preserved and tested source-specific discovery backoff and rotation so low-yield discovery cannot create duplicate work or silently stop the activity pipeline.

## 6.0.0-rc.1 — Rolling Output and Runtime Repair

- Replaced calendar-day action accounting with canonical rolling 24-hour output: 160 counted actions targeted, 200 capped, and genuine direct inbound tracked outside the cap.
- Added a canonical 40-opportunity reserve, atomic discovery upserts, relationship-only proactive DMs, ten-action bursts, source-specific backoff, and immediate source rotation.
- Replaced the two-post pipeline with six normal publications, up to two recovery publications, a six-package rolling inventory, 12-topic research selection, regional diversification, portfolio diversity rules, and a 120-minute spacing floor.
- Added 30-minute, 2-hour, 6-hour, and 24-hour measurement schedules with mandatory learning and decision artifacts.
- Added regional intelligence, publishing operations, engagement execution, opportunity discovery, and scoped runtime repair child skills while retaining one public parent entry point.
- Added schema 2.0 migration, canonical output reconstruction, restart-safe leases, deduplicated continuation renewal, and scoped Codex repair handoff.

## 5.1.0 — Adaptive Opportunity Recovery

- Added a weighted opportunity-health controller with missing-metric renormalization, confidence, daily action milestones, and persisted activation/exit streaks.
- Replaced reserve counters with canonical `engagement-opportunities.json` lifecycle records and immediate 1–10 action bursts.
- Added source-yield rotation, exact low-yield `not_before` decisions, and eliminated generic reconciliation loops.
- Added normal, expansion, and intensive score/follower/cooldown tiers while retaining the twice-per-seven-days person limit and 100-action hard ceiling.
- Expanded publishing from exactly two to a measured range of two through six, with one recovery package at a time, 120-minute spacing, velocity/cannibalization gates, and mandatory post-recovery analytics.
- Added migration of legacy candidates, opportunity-health history, expanded Working Algorithm Model dimensions, crash-restored recovery state, and acceptance coverage for the 9/100 incident replay.

## 5.0.9 — Recovery-state reconciliation

- recomputed agent-neutral lifecycle classification during every runtime reconciliation;
- cleared obsolete lane-probe wakes automatically after the recovered lane became ready;
- added migration regression coverage for stale recovery metadata.

## 5.0.8 — Deterministic skill entry

- made direct `/linkedin-campaign-orchestrator` invocation the canonical launch path;
- prohibited unbounded filesystem scans when resolving the installed plugin;
- aligned all skill metadata, Claude and Codex manifests, state templates, and public release copy.

## 5.0.7 — Lane-dependent wake routing

- mapped LinkedIn tasks behind a recovering lane to the lane's scheduled probe;
- prevented blocked-lane work from generating fake reconciliation tasks;
- added live-outage regression coverage for zero-question probe continuation.

## 5.0.6 — Pinned-browser probe recovery

- made a temporarily missing pinned browser an automatic transient lane recovery;
- prohibited questions about unrelated connected devices while a binding exists;
- required at least three scheduled probe cycles before browser absence can become a critical blocker.

## 5.0.5 — Zero-question automatic continuation

- made future `retry-wait` tasks produce an exact wake instead of fake reconciliation work;
- added a host-neutral automatic-continuation contract with one deduplicated campaign wake;
- prohibited scheduled-agent, heartbeat, loop, and manual-check-back choice prompts;
- persisted continuation adapter state and added due-wake regression coverage.

## 5.0.4 — Agent-neutral runtime classification

- made Claude, Codex, and other compatible agents use one durable lifecycle-classification contract;
- made lane recovery clear stale intervention requirements and recalculate the lifecycle state;
- exposed persisted runtime classification in campaign status and self-revival results;
- added regression coverage for identical recovered-state interpretation across agents.

## 5.0.3 — Pinned-browser continuity

- made an exact stored Chrome device ID authoritative across fresh sessions;
- required direct browser selection with the pinned ID instead of an interactive device picker;
- made display-label changes and unrelated connected devices non-ambiguous;
- added release-contract coverage for zero-question pinned-browser reuse.

## 5.0.2 — Deterministic rejection and restart reconciliation

- made candidate qualification mandatory before drafting or surfacing an engagement action;
- made failed gates and sub-65 scores automatic rejections that continue discovery without owner escalation;
- added machine-readable `owner_input_required` and `next_step` ranker directives;
- reconciled pending publication stages from verified publication evidence after a restart;
- added regression coverage for below-gate autonomous rejection and evidence-backed publication recovery.

## 1.1.0 — Reliable autonomous recovery

- added a campaign-lifetime consent receipt that reloads across model, client, and machine restarts;
- added deterministic session self-revival, downtime detection, task leases, checkpoints, retry backoff, and missed-work reconciliation;
- added campaign-local transactional day rollover so stale publication counters cannot block a new day;
- added pinned-browser reuse, reusable pre-flight evidence, lane circuit breakers, and automatic offline fallback;
- added adaptive reserve sizing, bounded discovery passes, and anti-starvation task rotation;
- generalized the recovery runtime to each campaign's configured owner, profile, timezone, and required regions;
- added restart, consent persistence, browser recovery, circuit breaker, reserve, and rollover acceptance tests.

## 1.0.0 — Public release

- converted the original single-owner campaign into a reusable public operator;
- added configurable owner, profile, timezone, niche, baselines, and growth goals;
- added a Codex plugin manifest and repository marketplace;
- retained Claude Code marketplace installation;
- changed campaign day accounting to use the configured local timezone;
- added public documentation, examples, website, launch assets, and an MIT license;
- added acceptance coverage for custom public campaign initialization.

## 0.5.0

- introduced continuous adaptive dispatch, reciprocity, dynamic publishing, runtime instruction refresh, pipeline audits, and persistent learning.
