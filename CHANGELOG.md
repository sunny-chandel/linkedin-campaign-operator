# Changelog

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
