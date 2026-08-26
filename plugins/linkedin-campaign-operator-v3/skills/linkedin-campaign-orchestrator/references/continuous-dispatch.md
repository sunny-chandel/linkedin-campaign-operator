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
- `soft-reciprocity`: likes, reactions, follows, visible profile views, and accepted connections. Inspect the newest visible relevant posts and select at most one action. New targets must have at least 3,000 followers. Every action must pass cooldown and score at least 65. If none qualifies, retain the relationship signal without acting.
- `proactive`: hub accounts, adjacency signals, premium discovery, and current regional or topic opportunities. Apply all qualification, score, deduplication, and cooldown gates.

Candidate rejection is normal work, not a blocker. A candidate that fails qualification, region/relevance, cooldown, availability, marginal value, or the score threshold is logged and discarded for the current opportunity before any draft is prepared. The dispatcher must continue discovery or select another eligible task; it must never route a rejected candidate to the owner for an exception.

Every action record includes lane, triggering signal, relationship strength, budget class, score or direct-inbound exemption, scheduling rationale, observed result, and evidence. A reaction to a reciprocal action increases relationship strength but never bypasses cooldown.

## Adaptive bursts and reserve

A proactive burst contains no more than 10 combined proactive and soft-reciprocal actions. Start a burst only when the Working Algorithm Model predicts positive marginal value from qualified-candidate density, regional opportunity, audience spillover, historical performance, remaining base capacity, and current concentration. There is no fixed interval. Recent concentration lowers the opportunity score and decays according to observed campaign outcomes.

Forecast the next two likely bursts and calculate the reserve target from recent executed burst size, candidate staleness, rejection rate, remaining budget, and the configured minimum and maximum. Do not default to two full 10-action bursts. Each discovery pass stops after five pages, eight minutes, low qualified yield, target completion, or declining marginal value. Persist candidates as they are found and record the pass immediately. A low-yield or limit-ending pass enters backoff so another work type can run. If reserve coverage is weak, investigation and discovery outrank waiting. Do not force an action or lower the score threshold.

Prevent starvation: after two consecutive selections of the same non-urgent task type, select the highest-ranked different eligible type. Direct inbound, due publication, pre-flight, lane recovery, and mandatory recovery remain exempt.

## Dynamic publication

Maintain exactly two validated packages for the configured required regions, which default to India and US-Central. Use the configured production-priority block, but allow direct inbound and exceptionally strong adaptive opportunities to interrupt it.

Evaluate publication opportunities without fixed times or spacing. Use `select_publish_time.py <opportunities> --state-dir <state-dir> --record` so the decision is appended to `schedule-decisions.jsonl`. Score regional activity, qualified-target activity, topic freshness, current network velocity, the previous post's engagement velocity, historical equal-age performance, format/pillar fit, remaining-day opportunity, and a dynamic cannibalization risk from the other post's live distribution. Use 70 percent proven timing, 20 percent promising timing, and 10 percent exploration. Publish exactly two posts per campaign-local content day; use the best final remaining opportunity if the model has not selected one earlier.

## Completion and blocker behavior

A stage cannot be complete until `audit_pipeline.py` validates its required artifacts. Analytics completion requires a learning record, either an experiment registration or an explicit no-change decision, and a next measurement trigger. Raw snapshots alone are incomplete.

Chrome loss, login failure, account-identity mismatch, unavailable capability, or a transient page failure enters automatic technical recovery. Retry safely up to two times, preserve external-outcome evidence, continue offline research, analytics, production, queue scoring from saved evidence, creative work, and logging, and run an automatic probe after cooldown. Resume the affected lane automatically after verification. A missing pinned browser remains recoverable through at least three scheduled probe cycles; unrelated connected devices are ignored and never become an owner-choice prompt. Request owner input only when automatic continuation and recovery are exhausted and neither lane nor a future wake path can advance.
