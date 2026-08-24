# Artifact contracts

Store mutable artifacts outside the plugin.

## Required files

- `campaign-config.json`: target, audience, content pillars, cadence, and completion formula.
- `consent-record.json`: recognized owner, start time, and approved action classes.
- `campaign-state.json`: lifecycle state, current stage, last action, blockers, and progress.
- `premium-entitlements.json`: detected products, tiers, roles, limits, and mappings.
- `interaction-log.jsonl`: one interaction event per line.
- `daily-analytics.jsonl`: normalized snapshot events.
- `learning-ledger.jsonl`: evidence-ranked learning records.
- `working-algorithm-model.json`: current hypotheses and strategy weights.
- `experiments.json`: registered controlled experiments.
- `logs/`: daily summaries and execution records.

## Pipeline artifacts

`research-brief.json` → `content-plan.json` → `publication-package.json` → `engagement-queue.json` → `daily-results.json` → `learning-update.json`

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
