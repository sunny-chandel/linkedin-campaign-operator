# Queue rules

## Candidate fields

Each queue item contains:

- target identifier and direct link;
- target-list status: new or existing;
- follower count when qualification applies;
- region and local-time relevance;
- relationship layer;
- post or conversation freshness;
- topic relevance;
- why the action adds value;
- proposed action type;
- final draft when text is required;
- last proactive interaction timestamp;
- proactive interactions in the trailing seven days;
- cooldown result;
- source or claim-verification note;
- Chrome execution status.

## Scoring

Apply qualification, cooldown, availability, and capacity as hard gates. Score eligible action candidates with:

- 35 percent predicted qualified profile, follower, or connection growth;
- 20 percent expected audience spillover;
- 15 percent probability of substantive conversation;
- 15 percent professional and target relevance;
- 10 percent freshness and regional timing;
- 5 percent historical performance for the action, target layer, region, and cluster.

Select only candidates scoring at least 65. Use observed campaign outcomes to update inputs without changing the fixed weights outside the weekly learning rules.

Follower count is a qualification gate for new additions, not a substitute for relevance.

## Repetition controls

- Do not reuse the same response with light paraphrasing.
- Do not engage the same post twice unless responding to a new inbound reply.
- Do not target the same account in multiple daily windows when the cooldown applies.
