# Continuous adaptive dispatch

## Work selection

Run `audit_pipeline.py <state-dir> --write` and `dispatch_next_work.py <state-dir> --record` at every wake and after every completed task. Execute the returned task, update its artifact and stage status, then dispatch again. A `wait` decision is valid only when the work queue contains no unfinished task, the mandatory stage ledger contains no unfinished stage, and the recorded wake trigger is supported by current evidence.

Do not run repeated fixed-duration sleep commands. Compute the next wake from the earliest predicted inbound event, publication opportunity, queue-staleness event, analytics trigger, content deadline, recovery requirement, or subscription-capacity event. Record the evidence, predicted opportunity, unfinished-work count, and wake trigger in `schedule-decisions.jsonl`.

## Engagement lanes and accounting

- `direct-inbound`: genuine comments, replies, and direct messages. These bypass new-target qualification and proactive cooldown. They consume the base budget until 100, then increment `direct_reply_overage` and continue.
- `soft-reciprocity`: likes, reactions, follows, visible profile views, and accepted connections. Inspect the newest visible relevant posts and select at most one action. New targets must have at least 3,000 followers. Every action must pass cooldown and score at least 65. If none qualifies, retain the relationship signal without acting.
- `proactive`: hub accounts, adjacency signals, premium discovery, and current regional or topic opportunities. Apply all qualification, score, deduplication, and cooldown gates.

Every action record includes lane, triggering signal, relationship strength, budget class, score or direct-inbound exemption, scheduling rationale, observed result, and evidence. A reaction to a reciprocal action increases relationship strength but never bypasses cooldown.

## Adaptive bursts and reserve

A proactive burst contains no more than 10 combined proactive and soft-reciprocal actions. Start a burst only when the Working Algorithm Model predicts positive marginal value from qualified-candidate density, regional opportunity, audience spillover, historical performance, remaining base capacity, and current concentration. There is no fixed interval. Recent concentration lowers the opportunity score and decays according to observed outcomes and platform feedback.

Forecast the next two likely bursts and maintain an adaptive reserve based on expected burst size and recent candidate-staleness or rejection rates. If reserve coverage is weak, investigation and discovery outrank waiting. Do not force an action or lower the score threshold.

## Dynamic publication

Maintain exactly two validated packages: India and US-Central. The production priority block is 9:00 PM-2:00 AM IST, but direct inbound and exceptionally strong adaptive opportunities may interrupt it.

Evaluate publication opportunities without fixed times or spacing. Use `select_publish_time.py <opportunities> --state-dir <state-dir> --record` so the decision is appended to `schedule-decisions.jsonl`. Score regional activity, qualified-target activity, topic freshness, current network velocity, the previous post's engagement velocity, historical equal-age performance, format/pillar fit, remaining-day opportunity, and a dynamic cannibalization risk from the other post's live distribution. Use 70 percent proven timing, 20 percent promising timing, and 10 percent exploration. Publish exactly two posts per IST content day; use the best final remaining opportunity if the model has not selected one earlier.

## Completion and blocker behavior

A stage cannot be complete until `audit_pipeline.py` validates its required artifacts. Analytics completion requires a learning record, either an experiment registration or an explicit no-change decision, and a next measurement trigger. Raw snapshots alone are incomplete.

Chrome loss, interactive verification, identity mismatch, warning, or restriction blocks the LinkedIn lane. Retry safely up to two times, preserve external-outcome evidence, and continue offline research, analytics, production, queue scoring from saved evidence, creative work, and logging. Resume LinkedIn automatically after verification. Mark the entire campaign hard-blocked only when neither lane can advance.
