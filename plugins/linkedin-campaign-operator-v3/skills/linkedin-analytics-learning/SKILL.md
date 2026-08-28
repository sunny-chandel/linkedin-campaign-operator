---
name: linkedin-analytics-learning
description: Review LinkedIn campaign results, compare experiments, and save useful lessons for future work. Use for daily and weekly reviews.
metadata:
  author: sunny
  version: "6.0.0-rc.14"
---

# LinkedIn analytics and learning

Turn verified campaign results into durable, bounded learning. Read [learning system](references/learning-system.md) before promoting or rolling back a finding.

Inherit the campaign configuration and current measurement task. Save every snapshot, comparison, learning decision, experiment decision, and next measurement trigger before returning to the parent.

## Measurement

1. Capture available post and campaign metrics using consistent definitions.
2. Compare posts at equal ages when possible.
3. Match content pillar, format, region, audience, and timing conditions.
4. Label unmatched comparisons as directional.
5. Record unavailable metrics as `unknown` rather than estimating them.
6. Run `python scripts/compute_metrics.py` for structured records.

Every snapshot produces a provisional or validated learning record, an experiment registration or explicit `no-change` decision, and a next measurement trigger.

## Learning loop

1. Combine authoritative current research, campaign observations, and controlled tests.
2. Record each claim with source, date, confidence, scope, test, and expiry.
3. Prefer validated approaches while preserving a smaller share for promising and exploratory ideas.
4. Validate changes with comparable evidence over time.
5. Change one strategy category gradually and log the reason.
6. Promote, retain, downgrade, expire, or roll back each active learning.
7. Run `python scripts/update_learning.py` for normalized ledger entries.
8. Update scheduling and performance models with `python scripts/update_scheduling_model.py`.

Learning may adjust topic, format, timing, region, research priority, queue order, response style within the voice guide, and subscription-feature priority. It may not alter the selected account, owner goals, configured limits, cooldowns, duplicate rules, or skill instructions.
