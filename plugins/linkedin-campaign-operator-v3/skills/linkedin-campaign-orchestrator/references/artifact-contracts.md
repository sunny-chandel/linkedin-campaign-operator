# Artifact contracts v6

Store mutable artifacts outside the plugin.

## Canonical evidence

- `interaction-log.jsonl`: confirmed actions, lane, signal, relationship, budget class, rationale, outcome, and timestamp.
- `publication-evidence.jsonl`: unique verified post identity, package, region, publication and verification times.
- `engagement-opportunities.json`: candidate identity, source, lane, gates, score, freshness, cooldown, followers, action type, lifecycle, expiry, relationship, and evidence.
- `signal-events.jsonl`, `task-events.jsonl`, `schedule-decisions.jsonl`, `opportunity-health.jsonl`, `repair-events.jsonl`: append-only runtime evidence.

## Controllers

- `operational-output.json`: rolling 24-hour action and post counts, targets, caps, debts, checkpoints, and evidence availability.
- `content-pipeline.json`: 12 topic candidates, six briefs, six-package inventory, freshness, portfolio roles, stage lifecycle, replacements, and four analytics checkpoints per post.
- `regional-performance.json`: observations, current allocation, timing performance, audience demographics, spillover, and exploration state.
- `repair-state.json`: failure, checkpoint, recovery attempts, Codex handoff, result, verification, retry trigger, and task resumption.
- `campaign-state.json`: lifecycle, consent snapshot, rolling mirrors, browser binding, lane circuits, continuity, and current controller links.
- `work-queue.json`: leased and idempotent tasks.
- `stage-ledger.json`: artifact-backed completion claims.

## Supporting state

Preserve configuration, consent, brand and watermark assets, creator and GIF learning, premium inventory and utilization, analytics, learning ledger, experiments, and the Working Algorithm Model.

The pipeline is:

`regional allocation` → `12 candidate topics` → `six briefs` → `six validated packages` → `publication decision` → `live evidence` → `30m/2h/6h/24h analytics` → `learning and experiment decision` → `replenishment`

Every artifact records schema version, campaign ID, timestamps, producer, active plugin version, validation status, evidence references, uncertainty, and next trigger. The auditor rejects claimed completion when required files or stage evidence are absent.
