---
name: linkedin-analytics-learning
description: Normalize LinkedIn campaign analytics, run controlled experiments, and update a versioned runtime learning layer without editing the governing skill. Use for daily and weekly reviews.
metadata:
  author: sunny
  version: "5.0.3"
---

# LinkedIn analytics and learning

Maintain runtime learning separately from immutable system and skill instructions. Read [learning system](references/learning-system.md) before promoting or rolling back a finding.

Inherit the parent's active campaign-lifetime consent receipt and leased task. Never ask for a separate approval. Checkpoint every saved snapshot, learning, experiment decision, and measurement trigger through the parent runtime before returning control.

## Automated execution

In automated mode, collect every available metric, compute the valid comparisons, update the ledger, and return control to the parent without asking the owner which metrics, experiments, or adjustments to use. Record unavailable metrics as `unknown`; do not block the daily cycle or fabricate values. If a script fails, preserve its inputs, retry safely, then compute the same documented result through an available fallback. Apply allowed learning changes automatically within the fixed bounds and log every change and trigger. Never modify a fixed campaign invariant or the skill instructions.

Raw analytics alone never complete the analytics stage. Every snapshot must produce a provisional or validated learning record, an experiment registration or explicit `no-change` decision, and a next measurement trigger. Write those completion fields to the mandatory stage ledger before the parent auditor can mark the stage complete.

## Measurement

1. Capture individual-post and combined analytics using consistent metric definitions.
2. Compare posts only at equal elapsed ages: 24 hours primary, seven days follow-up.
3. Match content pillar, format, region, and audience conditions when possible.
4. Label unmatched comparisons as directional.
5. Track impressions, members reached, in-network and out-of-network distribution, reactions, comments, saves, sends, reposts, clicks when available, follows, profile activity, qualified followers, connections, substantive conversation depth, action lane and burst source, response latency, regional opportunity, concentration state, candidate staleness, selected GIF pattern, and campaign conversions.
6. Run `python scripts/compute_metrics.py` for structured records.

## Learning loop

1. Collect authoritative current research, campaign observations, and controlled test results.
2. Record each claim in the learning ledger with source, date, confidence, scope, test, and expiry.
3. Use a 70/20/10 allocation: proven, promising, exploration.
4. Prefer at least four matched comparisons or two consistent weekly cycles before validating a non-official claim.
5. Change a strategy category by no more than ten percentage points in one weekly review.
6. Promote, retain, downgrade, expire, or roll back each active learning.
7. Run `python scripts/update_learning.py` to append a normalized ledger entry.
8. Update publication-time, response-latency, regional-opportunity, concentration, and candidate-staleness observations in `working-algorithm-model.json`.
9. Append every adaptive timing choice and its measured result to `schedule-decisions.jsonl`.
10. Use `python scripts/update_scheduling_model.py <working-algorithm-model.json> <model-name> <observation.json>` for deterministic model updates.

## Adjustable variables

Runtime learning may change topic weighting, content-pillar weighting, hook style, GIF information density, post length within voice rules, question style, target type, regional priority, queue ordering, action-score inputs, Tier 3 tone within bounds, approved premium-feature priority, research-source priority, publication opportunity scoring, response-latency priority, adaptive reserve size, and concentration-penalty decay.

It may not change consent, identities, the exactly-two-post requirement, the 100-action base ceiling, the 10-action burst cap, direct-inbound overage behavior, the new-user gate, cooldowns, hard-blocker definitions, or the skill instructions.
