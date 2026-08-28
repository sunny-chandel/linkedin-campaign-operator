---
name: linkedin-analytics-learning
description: Normalize LinkedIn campaign analytics, run controlled experiments, and update a versioned runtime learning layer without editing the governing skill. Use for daily and weekly reviews.
metadata:
  author: sunny
  version: "6.0.0-rc.10"
---

# LinkedIn analytics and learning

Maintain runtime learning separately from immutable system and skill instructions. Read [learning system](references/learning-system.md) before promoting or rolling back a finding.

Inherit the parent's campaign configuration and leased task. Checkpoint every saved snapshot, learning, experiment decision, and measurement trigger through the parent runtime before returning control.

## Automated execution

In automated mode, collect every available metric, compute valid comparisons, update the ledger, and return control to the parent. The active experiment plan supplies metrics and bounded adjustments. Record unavailable metrics as `unknown`; keep the daily cycle moving with truthful available evidence. If a script fails, preserve its inputs, retry safely, then compute the same documented result through an available fallback. Apply allowed learning changes automatically within the fixed bounds and log every change and trigger. Fixed campaign invariants and skill instructions remain unchanged.

Raw analytics alone never complete the analytics stage. Every snapshot must produce a provisional or validated learning record, an experiment registration or explicit `no-change` decision, and a next measurement trigger. Write those completion fields to the mandatory stage ledger before the parent auditor can mark the stage complete.

## Measurement

1. Capture individual-post and combined analytics using consistent metric definitions.
2. Capture and compare every verified post at equal ages of 30 minutes, 2 hours, 6 hours, and 24 hours.
3. Match content pillar, format, region, and audience conditions when possible.
4. Label unmatched comparisons as directional.
5. Track impressions, engagement rate, profile views, follower and connection growth, audience location and seniority, topic, format, timing, regional spillover, members reached, distribution, reactions, comments, saves, sends, reposts, clicks when available, substantive conversation depth, action lane and burst source, response latency, concentration, staleness, GIF pattern, and campaign conversions.
6. Run `python scripts/compute_metrics.py` for structured records.

## Learning loop

1. Collect authoritative current research, campaign observations, and controlled test results.
2. Record each claim in the learning ledger with source, date, confidence, scope, test, and expiry.
3. Use a 70/20/10 allocation: proven, promising, exploration.
4. Prefer at least four matched comparisons or two consistent weekly cycles before validating a non-official claim.
5. Change a strategy category by no more than ten percentage points in one weekly review.
6. Promote, retain, downgrade, expire, or roll back each active learning.
7. Run `python scripts/update_learning.py` to append a normalized ledger entry.
8. Update publication-time, response-latency, regional-opportunity, concentration, candidate-staleness, source-yield, gate-tier, action-type, recovery-post, action-to-profile-view, follower-conversion, format, topic, and regional-spillover observations in `working-algorithm-model.json`.
9. After every recovery publication, write its equal-age result, update `opportunity-health.jsonl`, and return control before another recovery package can be prepared.
9. Append every adaptive timing choice and its measured result to `schedule-decisions.jsonl`.
10. Use `python scripts/update_scheduling_model.py <working-algorithm-model.json> <model-name> <observation.json>` for deterministic model updates.

## Adjustable variables

Runtime learning may change topic weighting, content-pillar weighting, hook style, GIF information density, post length within voice rules, question style, target type, regional priority, queue ordering, action-score inputs, Tier 3 tone within bounds, configured premium-feature priority, research-source priority, publication opportunity scoring, response-latency priority, adaptive reserve size, and concentration-penalty decay.

It may not change consent, identities, the six-to-eight rolling publication contract, the 160-action target, the 200-action cap, the 10-action burst cap, direct-inbound outside-cap behavior, active recovery gates, cooldowns, runtime repair scope, or skill instructions.
