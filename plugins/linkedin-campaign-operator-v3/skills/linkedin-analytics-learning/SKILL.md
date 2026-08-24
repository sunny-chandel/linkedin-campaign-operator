---
name: linkedin-analytics-learning
description: Normalize LinkedIn campaign analytics, run controlled experiments, and update a versioned runtime learning layer without editing the governing skill. Use for daily and weekly reviews.
compatibility: Requires campaign analytics, experiment records, and a writable runtime-state directory.
metadata:
  author: sunny
  version: "0.3.2"
---

# LinkedIn analytics and learning

Maintain runtime learning separately from immutable system and skill instructions. Read [learning system](references/learning-system.md) before promoting or rolling back a finding.

## Automated execution

In automated mode, collect every available metric, compute the valid comparisons, update the ledger, and return control to the parent without asking the owner which metrics, experiments, or adjustments to use. Record unavailable metrics as `unknown`; do not block the daily cycle or fabricate values. If a script fails, preserve its inputs, retry safely, then compute the same documented result through an available fallback. Apply allowed learning changes automatically within the fixed bounds and log every change and trigger. Never modify a fixed campaign invariant or the skill instructions.

## Measurement

1. Capture individual-post and combined analytics using consistent metric definitions.
2. Compare posts only at equal elapsed ages: 24 hours primary, seven days follow-up.
3. Match content pillar, format, region, and audience conditions when possible.
4. Label unmatched comparisons as directional.
5. Track impressions, members reached, in-network and out-of-network distribution, reactions, comments, saves, sends, reposts, clicks when available, follows, profile activity, qualified followers, negative feedback, and campaign conversions.
6. Run `python scripts/compute_metrics.py` for structured records.

## Learning loop

1. Collect authoritative current research, campaign observations, and controlled test results.
2. Record each claim in the learning ledger with source, date, confidence, scope, test, and expiry.
3. Use a 70/20/10 allocation: proven, promising, exploration.
4. Prefer at least four matched comparisons or two consistent weekly cycles before validating a non-official claim.
5. Change a strategy category by no more than ten percentage points in one weekly review.
6. Promote, retain, downgrade, expire, or roll back each active learning.
7. Run `python scripts/update_learning.py` to append a normalized ledger entry.

## Adjustable variables

Runtime learning may change topic weighting, content-pillar weighting, asset format, hook style, information density, post length within voice rules, question style, target type, regional priority, queue ordering, Tier 3 tone within bounds, approved premium-feature priority, and research-source priority.

It may not change consent, identities, action counts, windows, spacing, the new-user gate, cooldowns, hard-blocker definitions, or the skill instructions.
