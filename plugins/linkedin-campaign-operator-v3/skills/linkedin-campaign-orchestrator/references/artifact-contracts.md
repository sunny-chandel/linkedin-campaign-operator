# Artifact contracts v6

Store mutable artifacts outside the plugin.

## Canonical evidence

- `interaction-log.jsonl`: confirmed actions, lane, signal, relationship, budget class, rationale, outcome, and timestamp.
- `publication-evidence.jsonl`: unique verified post identity, package, region, publication and verification times.
- `engagement-opportunities.json`: candidate identity, source, lane, gates, score, freshness, cooldown, followers, action type, lifecycle, expiry, relationship, and evidence.
- `signal-events.jsonl`, `task-events.jsonl`, `schedule-decisions.jsonl`, `opportunity-health.jsonl`, `repair-events.jsonl`: append-only runtime evidence.

## Controllers

- `operational-output.json`: current activity and publication counts, configured limits, pending work, checkpoints, and evidence availability.
- `content-pipeline.json`: topic candidates, research briefs, ready-package inventory, freshness, portfolio roles, stage lifecycle, replacements, and measurement checkpoints.
- `regional-performance.json`: observations, current allocation, timing performance, audience demographics, spillover, and exploration state.
- `repair-state.json`: failure, checkpoint, recovery attempts, result, verification, retry trigger, and task resumption.
- `campaign-state.json`: lifecycle, campaign-settings snapshot, current mirrors, profile binding, continuity, and current controller links.
- `work-queue.json`: leased and idempotent tasks.
- `stage-ledger.json`: artifact-backed completion claims.

## Supporting state

Preserve configuration, profile identity, brand and watermark assets, creator and GIF learning, subscription inventory and utilization, analytics, learning ledger, experiments, and the Working Algorithm Model.

The pipeline is:

`regional allocation` → `candidate topics` → `verified briefs` → `validated packages` → `publication decision` → `verified result` → `scheduled analytics` → `learning and experiment decision` → `replenishment`

Every artifact records schema version, campaign ID, timestamps, producer, active plugin version, validation status, evidence references, uncertainty, and next trigger. The auditor rejects claimed completion when required files or stage evidence are absent.
