# Runtime learning system

The learning layer is mutable operational state. It never edits the skill.

## Learning record

Record:

- ID, discovery date, source URL, source tier, and publication date;
- paraphrased claim and relevant audience, region, format, and account type;
- supporting and conflicting evidence;
- connected campaign observations;
- confidence and status;
- proposed experiment and thresholds;
- adjustable variables affected;
- fixed variables;
- last validation and expiry dates.

Statuses: `observed`, `hypothesis`, `testing`, `provisionally-supported`, `validated`, `contradicted`, `rolled-back`, `expired`, `archived`.

## Working Algorithm Model

Maintain evidence-ranked hypotheses about professional relevance, semantic alignment, relationship proximity, audience history, quality and trust, freshness, format, measurable reading behavior, engagement types, network distribution, negative feedback, regional differences, consistency, and premium signals.

Maintain explicit scheduling models for:

- publication timing and cannibalization risk;
- response latency and inbound value decay;
- regional opportunity;
- recent action concentration and penalty decay;
- candidate staleness and reserve replacement demand.
- source yield and action-to-profile-view or follower conversion;
- topic, format, timing, audience demographics, and regional spillover.

Each scheduling observation records the evidence time, context, prediction, selected decision, measured result, confidence, and next measurement trigger. A wait decision is itself an experimentable schedule decision and must be compared with the opportunity that actually appeared.

## Experiment requirements

- One primary variable.
- Comparable control.
- Primary and secondary metrics.
- Equal-age measurement at 30 minutes, 2 hours, 6 hours, and 24 hours.
- Audience, region, topic, format, and time recorded.
- Predefined success, failure, and rollback thresholds.
- Four matched comparisons or two consistent weekly cycles preferred for non-official claims.

## Strategy allocation

- 70% validated approaches.
- 20% promising approaches.
- 10% exploration.

Move no category by more than ten percentage points per weekly review.

Rollback a learning after repeated comparable underperformance, material negative feedback, stronger contradictory evidence, source retraction, feature change, or loss of effect after normalization.

GIF creative patterns use the separate mutable `creative-pattern-library.json`. A dominant contradictory GIF reference follows the immediate permanent-deletion rule in `linkedin-gif-creative-intelligence`; do not duplicate that deleted pattern into this append-only ledger.
