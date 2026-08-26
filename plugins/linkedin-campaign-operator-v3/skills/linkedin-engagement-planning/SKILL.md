---
name: linkedin-engagement-planning
description: Build and validate adaptive LinkedIn action queues with qualified-growth scoring, qualification, cooldown, deduplication, and regional relevance. Use before any proactive action cluster.
metadata:
  author: sunny
  version: "5.0.0"
---

# LinkedIn engagement planning

Prepare high-quality queues for the continuous dispatcher. The shared base ceiling is 100 actions per campaign-local day and is never a target. Genuine direct-inbound replies continue after the base ceiling and use the separate `direct_reply_overage` counter.

Inherit the parent's active campaign-lifetime consent receipt, pinned browser binding, lane circuit, and leased task. Never ask for device selection or action approval. Persist each qualified candidate immediately, and finish every discovery pass through `runtime_control.py reserve-pass` so page, duration, yield, adaptive target, backoff, and restart state are deterministic.

## Automated execution

In automated mode, build, score, validate, and hand the queue back to the parent without asking the owner to choose targets, action types, topics, or regions. Evaluate every eligible comment, reply, reaction, DM, follow, profile view when available, and connection event. Route each action through `proactive`, `soft-reciprocity`, or `direct-inbound`, then choose the action with the strongest predicted qualified-growth value. Discover replacements automatically when a candidate is stale, duplicated, below the new-user gate, inside cooldown, irrelevant, unavailable, or below the 65-point action threshold. Execute only the verified subset and reduce the correct budget counter; never invent candidates, force a mix, violate a limit, compensate later, or ask for permission.

## Priority order

1. Genuine direct-inbound comments, replies, and DMs.
2. Qualified reciprocity signals from comments, replies, likes, reactions, follows, profile views when available, connections, and acceptances.
3. Fresh posts from established hub accounts already in the target list.
4. Relevant adjacency signals from trusted professional conversations.
5. Premium searches, alerts, and insights.
6. Current topic and regional relevance.

## Qualification and cooldown

- Apply the 3,000-follower gate only when adding a new target.
- Do not apply the gate to direct replies or people already in the target list.
- Before queueing proactive or soft-reciprocal activity, check the interaction log.
- Do not proactively engage the same person more than once in 72 hours or more than twice in seven days.
- Direct replies, incoming DMs, and conversations initiated by the other person are exempt but must be logged in the `direct-inbound` lane.
- Run `python scripts/check_cooldown.py` when structured interaction data is available.

Read [queue rules](references/queue-rules.md) for scoring and output fields.

## Action constraints

- A reaction, comment, reply, DM, follow, or connection each counts as one action.
- Avoid repetitive response-bank text and repeated targeting.
- Every response must be relevant to the specific post or conversation.
- Run `python scripts/rank_actions.py <candidates> --threshold 65 --limit 10` for structured candidate sets.
- After each confirmed external action, run `python scripts/record_action.py <state-dir> <action.json>` so lane metadata and the correct base or overage counter are committed.
- A proactive or mixed burst contains at most 10 actions and stops earlier when candidate quality drops below 65, expected marginal value declines, or the base budget is exhausted.
- Proactive and soft-reciprocity actions consume the shared 100-action base budget. Genuine direct replies use the base budget until 100, then continue under `direct-reply-overage`.
- A reaction to a reciprocal action raises relationship strength but never bypasses cooldown.
- Maintain an adaptive reserve sized for the next two likely bursts and observed candidate-staleness rate.
- Never use a fixed cluster interval. Apply the learned concentration penalty and let the parent dispatcher choose the next wake from evidence.

Return up to 10 planned actions for each burst, each with lane, triggering signal, relationship strength, budget classification, scheduling rationale, score components, evidence, last-interaction check, and intended qualified-growth outcome. Stop early only for a hard blocker.
