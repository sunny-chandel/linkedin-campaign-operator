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

## Experiment requirements

- One primary variable.
- Comparable control.
- Primary and secondary metrics.
- Equal-age measurement.
- Audience, region, topic, format, and time recorded.
- Predefined success, failure, and rollback thresholds.
- Four matched comparisons or two consistent weekly cycles preferred for non-official claims.

## Strategy allocation

- 70% validated approaches.
- 20% promising approaches.
- 10% exploration.

Move no category by more than ten percentage points per weekly review.

Rollback a learning after repeated comparable underperformance, material negative feedback, stronger contradictory evidence, source retraction, feature change, or loss of effect after normalization.
