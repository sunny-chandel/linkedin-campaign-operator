---
name: linkedin-engagement-planning
description: Build and validate regional LinkedIn engagement queues with qualification, cooldown, deduplication, and relevance scoring. Use before any engagement window.
compatibility: Requires campaign state, interaction logs, and the connected Chrome session for LinkedIn execution.
metadata:
  author: sunny
  version: "0.3.2"
---

# LinkedIn engagement planning

Prepare high-quality queues; do not equate action volume with campaign value.

## Automated execution

In automated mode, build, validate, and hand the queue back to the parent without asking the owner to choose targets, actions, topics, or regions. Discover replacements automatically when a candidate is stale, duplicated, below the new-user gate, inside cooldown, irrelevant, or unavailable. Continue discovery until 10 valid actions are ready or the window closes. If fewer than 10 valid actions can be found without breaking a fixed rule, execute only the verified subset, log the shortfall and reason, and continue the pipeline; never invent candidates, violate a limit, compensate later, or ask for permission.

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

Return 10 planned actions for each window, each with rationale, evidence, last-interaction check, and intended outcome. Stop early only for a hard blocker.
