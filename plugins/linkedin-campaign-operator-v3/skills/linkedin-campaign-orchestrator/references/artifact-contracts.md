# Artifact contracts

Store mutable artifacts outside the plugin.

## Required files

- `campaign-config.json`: target, audience, content pillars, cadence, and completion formula.
- `consent-record.json`: recognized owner, start time, and authorized action classes.
- `campaign-state.json`: lifecycle state, current stage, last action, blockers, and progress.
- `brand-profile.json`: verified profile-derived brand inputs, explicit overrides, and identity hash.
- `watermark-manifest.json`: Claude Design project, validated watermark exports, hashes, placement, and refresh state.
- `creator-registry.json`: 12 core and eight rotating GIF creator records.
- `gif-reference-index.json`: normalized reference metadata and visual or motion measurements.
- `creative-pattern-library.json`: mutable GIF rules that support immediate per-post promotion and permanent deletion.
- `gif-creative-spec.json`: exact selected build specification for the current GIF publication package.
- `premium-entitlements.json`: compatibility inventory of detected products, tiers, roles, and limits.
- `subscription-inventory.json`: normalized feature-level entitlements, setup state, capacity, expiry, and pipeline mappings.
- `subscription-utilization-plan.json`: deterministic priority scores and execution routing for verified included features.
- `subscription-results.jsonl`: feature setup, usage, capacity, and outcome events used by daily and weekly learning.
- `interaction-log.jsonl`: one interaction event per line.
- `daily-analytics.jsonl`: normalized snapshot events.
- `learning-ledger.jsonl`: evidence-ranked learning records.
- `working-algorithm-model.json`: current hypotheses and strategy weights.
- `experiments.json`: registered controlled experiments.
- `work-queue.json`: unified prioritized tasks and lane blockers.
- `stage-ledger.json`: mandatory-stage evidence and completion gates.
- `signal-events.jsonl`: append-only inbound and soft-reciprocity signals.
- `schedule-decisions.jsonl`: append-only dispatcher, burst, publication, and wake decisions.
- `task-events.jsonl`: append-only task lease, start, checkpoint, completion, and failure events.
- `recovery-events.jsonl`: append-only session restart, downtime, abandoned-lease, missed-task, and rollover recovery events.
- `publication-evidence.jsonl`: verified post IDs, URLs, regions, content days, packages, and timestamps.
- `logs/`: daily summaries and execution records.

Every interaction event additionally records its lane, triggering signal, relationship strength, budget classification, and scheduling rationale.

Every queue item records its lifecycle status, attempt count, idempotency key, lease ID and expiry while active, last heartbeat, latest checkpoint, retry eligibility, and evidence-backed terminal outcome. `campaign-state.json` records the consent fingerprint, pinned browser binding, reusable pre-flight evidence, lane circuits, last runtime heartbeat, detected downtime, latest self-revival report, agent-neutral `runtime_classification`, and the active automatic-continuation adapter, automation identifier, exact next wake, and deduplication key.

## Pipeline artifacts

`research-brief.json` → `content-plan.json` → `gif-creative-spec.json` when applicable → exactly two `publication-package.json` records → `work-queue.json` → `daily-results.json` → `learning-update.json` → mandatory-stage completion

Every artifact should contain:

- schema version;
- campaign ID;
- creation timestamp and timezone;
- producing stage;
- source activation version;
- validation status;
- inputs or evidence references;
- structured payload;
- warnings and unresolved uncertainty.

Do not infer that an artifact exists because a prior tool call timed out. Verify it on disk.

The pipeline auditor rejects completion when a required artifact is absent. For analytics, the stage remains incomplete until the ledger contains a provisional or validated learning, an experiment or explicit no-change decision, and the next measurement trigger.
