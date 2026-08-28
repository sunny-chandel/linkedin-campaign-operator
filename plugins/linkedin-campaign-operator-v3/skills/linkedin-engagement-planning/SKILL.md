---
name: linkedin-engagement-planning
description: Build and validate adaptive LinkedIn action queues with qualified-growth scoring, qualification, cooldown, deduplication, and regional relevance. Use before any proactive action cluster.
metadata:
  author: sunny
  version: "6.0.0-rc.9"
---

# LinkedIn engagement planning

Prepare high-quality queues for the continuous dispatcher. The rolling 24-hour counted-action target is 160 and the hard cap is 200. Genuine direct inbound replies remain outside the cap and are logged separately.

Inherit the parent's campaign configuration, pinned browser binding, lane circuit, and leased task. Use the pinned device and the executor-covered action classes from state. Persist each qualified candidate immediately, and finish every sourced discovery pass through `runtime_control.py opportunity-pass` so canonical upserts, yield, source-specific backoff, rotation, and restart state are deterministic. `reserve-pass` is only a compatibility checkpoint for legacy unsourced reserve work and must not be used for new `opportunity-discovery` tasks.

## Automated execution

In automated mode, read targets, action classes, topics, and regions from state, then build, score, validate, and hand the queue back to the parent. Evaluate eligible API-covered comments, replies, and reactions plus read-only discovery signals. Route each action through `proactive`, `soft-reciprocity`, or `direct-inbound`, then choose the action with the strongest predicted qualified-growth value. Discover replacements automatically when a candidate is stale, duplicated, below the new-user gate, inside cooldown, irrelevant, unavailable, or below the 65-point action threshold. Enqueue only the verified subset and reduce the correct budget counter after external verification.

Qualification precedes drafting. Materialize discovered candidates, run `rank_actions.py`, and draft only actions from its `selected` array. A failed gate or score is a normal automatic rejection with a machine-readable reason. Continue discovery within the current pass limits and return control to the dispatcher when the pass ends. When no candidate qualifies, return `setup_input_required: false` and `next_step: continue-discovery`.

## Priority order

1. Genuine direct-inbound comments, replies, and DMs.
2. Qualified reciprocity signals from comments, replies, likes, reactions, follows, profile views when available, connections, and acceptances.
3. Fresh posts from established hub accounts already in the target list.
4. Relevant adjacency signals from trusted professional conversations.
5. Premium searches, alerts, and insights.
6. Current topic and regional relevance.

## Qualification and cooldown

- Apply the active recovery tier's follower gate only when adding a new target: 3,000 normal, 2,000 expansion, or 1,000 intensive.
- Do not apply the gate to direct replies or people already in the target list.
- Before queueing proactive or soft-reciprocal activity, check the interaction log.
- Apply the active cooldown tier: 72 hours normal, 48 expansion, or 24 intensive. Never proactively engage the same person more than twice in seven days.
- Direct replies, incoming DMs, and conversations initiated by the other person are exempt but must be logged in the `direct-inbound` lane.
- Run `python scripts/check_cooldown.py` when structured interaction data is available.

Read [queue rules](references/queue-rules.md) for scoring and output fields.

## Action constraints

- A reaction, comment, reply, DM, follow, or connection each counts as one action.
- Avoid repetitive response-bank text and repeated targeting.
- Every response must be relevant to the specific post or conversation.
- Run `python scripts/rank_actions.py <candidates> --mode <normal|expansion|intensive> --limit 10` for structured candidate sets. The tier fixes the exact score and new-target follower floors.
- Treat the ranker output as authoritative. `rejected` items are terminal for the current opportunity; follow the output's `next_step` automatically.
- After each confirmed external action, run `python scripts/record_action.py <state-dir> <action.json>` so lane metadata and the correct base or overage counter are committed.
- A proactive or mixed burst contains at most 10 actions and stops earlier when candidate quality drops below the active tier floor, expected marginal value declines, or the base budget is exhausted. A single qualified canonical record is enough for a one-action burst.

Write accepted candidates to `engagement-opportunities.json`; do not maintain an independent reserve total. Record source passes through `runtime_control.py opportunity-pass` and completed bursts through `runtime_control.py burst-complete` so lifecycle and budget changes are atomic.
- Proactive and soft-reciprocity actions consume rolling capacity up to 200. Genuine direct replies remain outside the cap. Proactive DMs require an existing connection and prior-interaction evidence.
- A reaction to a reciprocal action raises relationship strength while preserving cooldown.
- Maintain an adaptive reserve sized for the next two likely bursts and observed candidate-staleness rate.
- Never use a fixed cluster interval. Apply the learned concentration penalty and let the parent dispatcher choose the next wake from evidence.

Return up to 10 planned actions for each burst, each with lane, triggering signal, relationship strength, budget classification, scheduling rationale, score components, evidence, last-interaction check, and intended qualified-growth outcome. Stop early only for a hard blocker.
