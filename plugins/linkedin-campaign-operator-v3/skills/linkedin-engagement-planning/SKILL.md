---
name: linkedin-engagement-planning
description: Build and validate adaptive LinkedIn action queues with qualified-growth scoring, qualification, cooldown, deduplication, and regional relevance. Use before any proactive action cluster.
compatibility: Requires campaign state, interaction logs, and the connected Chrome session for LinkedIn execution.
metadata:
  author: sunny
  version: "0.4.0"
---

# LinkedIn engagement planning

Prepare high-quality queues; 80 actions is a ceiling and never a requirement.

## Automated execution

In automated mode, build, score, validate, and hand the queue back to the parent without asking the owner to choose targets, action types, topics, or regions. Evaluate every eligible comment, reply, reaction, DM, and connection request, then choose the action with the strongest predicted qualified-growth value. Discover replacements automatically when a candidate is stale, duplicated, below the new-user gate, inside cooldown, irrelevant, unavailable, or below the 65-point action threshold. Execute only the verified subset and reduce the remaining daily capacity; never invent candidates, force a mix, violate a limit, compensate later, or ask for permission.

## Priority order

1. Direct replies to the campaign owner.
2. Fresh posts from established hub accounts already in the target list.
3. Relevant adjacency signals from trusted professional conversations.
4. Premium searches, alerts, and insights.
5. Current topic and regional relevance.

## Qualification and cooldown

- Apply the 3,000-follower gate only when adding a new target.
- Do not apply the gate to direct replies or people already in the target list.
- Before queueing proactive activity, check the interaction log.
- Do not proactively engage the same person more than once in 72 hours or more than twice in seven days.
- Direct replies, incoming DMs, and conversations initiated by the other person are exempt but must be logged.
- Run `python scripts/check_cooldown.py` when structured interaction data is available.

Read [queue rules](references/queue-rules.md) for scoring and output fields.

## Action constraints

- A reaction, comment, reply, or DM each counts as one action.
- Avoid repetitive response-bank text and repeated targeting.
- Every response must be relevant to the specific post or conversation.
- Run `python scripts/rank_actions.py <candidates> --threshold 65 --limit 10` for structured candidate sets.
- A proactive cluster contains at most 10 actions. All actions, including genuine inbound replies, count toward the 80-action daily ceiling.

Return up to 10 planned actions for each cluster, each with score components, rationale, evidence, last-interaction check, and intended qualified-growth outcome. Stop early only for a hard blocker.
