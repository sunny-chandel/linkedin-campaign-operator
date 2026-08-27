# Continuous adaptive dispatch

## Work selection

Run `audit_pipeline.py <state-dir> --write` and `dispatch_next_work.py <state-dir> --record` at every wake and after every completed task. Execute the returned task, update its artifact and stage status, then dispatch again. A `wait` decision is valid only when no task or mandatory stage is executable now and the recorded wake trigger is supported by current evidence. A future `retry-wait` task may remain unfinished while the dispatcher waits for its exact eligibility time.

`--record` leases the selected task for the configured duration. Record `task-event start` before work, checkpoint every durable result, and record either evidence-backed completion or a retryable failure. Task states are `pending`, `leased`, `running`, `retry-wait`, `recovering`, `missed-recovering`, and terminal outcomes. A restart expires abandoned leases and resumes from the latest checkpoint. Idempotency keys prevent the same daily package, publication, or recovery task from being created twice.

The campaign-local rollover is transactional and runs before selection. It archives the previous day's counters, activates valid packages for the new day, reconstructs region-specific publication tasks, creates the new mandatory stages, resets the base budget, and preserves verified publication evidence. It never carries yesterday's `2/2` publication count into today.

Do not run repeated fixed-duration sleep commands. Compute the next wake from the earliest predicted inbound event, future task eligibility, publication opportunity, queue-staleness event, analytics trigger, content deadline, recovery requirement, or subscription-capacity event. Record the evidence, predicted opportunity, unfinished-work count, and wake trigger in `schedule-decisions.jsonl`.

## Automatic continuation

Continuation is part of dispatch, not an owner preference. Every wait decision returns `continuation.mode: automatic`, `owner_input_required: false`, a campaign-level deduplication key, the exact wake time, and an ordered host-adapter list. Before ending the current turn, automatically arm or update the first available adapter: host-native scheduled wake, host-native heartbeat, then dynamic in-session loop. Record the successful adapter and automation identifier through `runtime_control.py continuation-event --event armed`. On a wake, record `--event woke` and run the normal self-revival sequence.

Never present scheduled execution, a loop, manual check-back, or “keep going” as choices. If an adapter is unavailable, record the failure and fall through to the next adapter. Reuse one automation per campaign and update its next wake rather than creating parallel runs. Only after every configured adapter is technically unavailable may continuation become an exact capability blocker; it never becomes a routine approval request.

## Engagement lanes and accounting

- `direct-inbound`: genuine comments, replies, and direct messages. These bypass new-target qualification and proactive cooldown. They consume the base budget until 100, then increment `direct_reply_overage` and continue.
- `soft-reciprocity`: likes, reactions, follows, visible profile views, and accepted connections. Inspect the newest visible relevant posts and select at most one action. Apply the active recovery tier's new-target follower, cooldown, and score gates. If none qualifies, retain the relationship signal without acting.
- `proactive`: hub accounts, adjacency signals, premium discovery, and current regional or topic opportunities. Apply all qualification, score, deduplication, and cooldown gates.

Candidate rejection is normal work, not a blocker. A candidate that fails qualification, region/relevance, cooldown, availability, marginal value, or the score threshold is logged and discarded for the current opportunity before any draft is prepared. The dispatcher must continue discovery or select another eligible task; it must never route a rejected candidate to the owner for an exception.

Every action record includes lane, triggering signal, relationship strength, budget class, score or direct-inbound exemption, scheduling rationale, observed result, and evidence. A reaction to a reciprocal action increases relationship strength but never bypasses cooldown.

## Opportunity health, adaptive bursts, and canonical supply

Run `evaluate_opportunity_health.py <state-dir> --record` after every wake, publication, burst, analytics checkpoint, and generation pass. Score equal-age impressions at 25 percent, engagement rate at 20, profile-view velocity at 20, follower and connection growth at 10, action pace at 15, and canonical reserve coverage plus source yield at 10. Use trailing seven-day comparable medians. Missing metrics are excluded and remaining weights renormalized; fewer than three comparable observations reduces confidence instead of inventing zeroes.

Expected cumulative action pace is 20 at 25 percent of the local day, 45 at 50 percent, 70 at 75 percent, and 100 at close. Activate recovery after two health scores below 70 or when actual actions fall below half expected pace. Exit only after two consecutive evaluations with health at least 80 and pace at least 90 percent.

Recovery tiers are immutable: normal is score 65, 3,000 new-target followers, 72-hour cooldown; expansion is 60, 2,000, 48; intensive is 55, 1,000, 24. Never go lower, and always enforce at most two proactive interactions per person in seven days.

A proactive burst contains no more than 10 combined proactive and soft-reciprocal actions. Start a burst only when the Working Algorithm Model predicts positive marginal value from qualified-candidate density, regional opportunity, audience spillover, historical performance, remaining base capacity, and current concentration. There is no fixed interval. Recent concentration lowers the opportunity score and decays according to observed campaign outcomes.

`engagement-opportunities.json` is canonical. Every record carries identity, source, lane, score, active gate, freshness, cooldown, follower count, action type, lifecycle, expiry, and evidence. Derive reserve coverage only from currently eligible records. When one or more are eligible, dispatch a burst of up to ten before another search. After execution atomically update action count, lifecycle, concentration, source yield, relationship evidence, and prediction.

Rotate discovery through the eight configured sources and use 70/20/10 proven, promising, and exploration allocation. Each pass records attempts, accepted candidates, rejection reasons, staleness, actions, replies, profile views, and follower outcomes. Low yield sets an exact `not_before`, selects a different next source, and continues offline work. It never increases the reserve target or creates a `reconcile-work-queue` loop.

Prevent starvation: after two consecutive selections of the same non-urgent task type, select the highest-ranked different eligible type. Direct inbound, due publication, pre-flight, lane recovery, and mandatory recovery remain exempt.

## Dynamic publication and recovery content

Maintain exactly two normal validated packages for India and US-Central. After both are published, active recovery may prepare one additional package. Never store more than one unpublished recovery package.

Evaluate publication opportunities dynamically with `select_publish_time.py`. Guarantee two normal posts. Recovery publication additionally requires active recovery, 120 minutes since the previous publication, preceding velocity below 85 percent of baseline or cannibalization below 0.35, a fresh source, distinct angle and pillar or format, and score at least 65. Collect `performance-recovery-analytics` and reevaluate before creating another. Publish from two through six posts, never seven.

## Completion and blocker behavior

A stage cannot be complete until `audit_pipeline.py` validates its required artifacts. Analytics completion requires a learning record, either an experiment registration or an explicit no-change decision, and a next measurement trigger. Raw snapshots alone are incomplete.

Chrome loss, login failure, account-identity mismatch, unavailable capability, or a transient page failure enters automatic technical recovery. Retry safely up to two times, preserve external-outcome evidence, continue offline research, analytics, production, queue scoring from saved evidence, creative work, and logging, and run an automatic probe after cooldown. Resume the affected lane automatically after verification. A missing pinned browser remains recoverable through at least three scheduled probe cycles; unrelated connected devices are ignored and never become an owner-choice prompt. Request owner input only when automatic continuation and recovery are exhausted and neither lane nor a future wake path can advance.
