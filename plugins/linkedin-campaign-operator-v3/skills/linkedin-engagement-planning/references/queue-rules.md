# Queue rules

## Candidate fields

Each candidate record contains:

- target identifier and direct link;
- source and triggering evidence;
- relationship and previous-contact evidence;
- target-list status;
- region and local-time relevance;
- post or conversation freshness;
- topic and professional relevance;
- why a response would add value;
- proposed item type;
- final draft when text is needed;
- most recent interaction time;
- cooldown and duplicate results;
- claim-verification notes;
- lifecycle status, expiry, and rejection reason.

## Hard checks

Before drafting, confirm the selected account, target availability, relevance, freshness, current campaign limit, cooldown, previous-contact rule, and duplicate result. A failed hard check rejects the candidate for the current opportunity and saves the exact reason.

## Scoring

Score eligible candidates using the weights in campaign configuration. Favor professional relevance, useful contribution, likely substantive conversation, audience fit, freshness, regional timing, and measured past performance. Treat public popularity as context, not a substitute for relevance.

Use the configured quality floor and target-qualification rules. Do not lower the floor merely because the queue is empty.

## Selection and repetition

- Select the strongest currently eligible item.
- Do not reuse the same response with light paraphrasing.
- Do not address the same post twice unless there is new inbound context.
- Do not return to the same account while its cooldown applies.
- Do not create filler activity to satisfy a target.
- If no item qualifies, rotate to another measured source and save the next check.

## Output

Return each selected item with its evidence, score components, timing rationale, previous-contact result, duplicate result, cooldown result, intended value, and next trigger. Keep rejected records in the canonical queue with machine-readable reasons.
