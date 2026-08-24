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

Rank by:

1. direct inbound relevance;
2. professional and topic fit;
3. freshness and timing;
4. existing relationship quality;
5. likelihood of a substantive conversation;
6. regional fit;
7. risk of repetition.

Follower count is a qualification gate for new additions, not a substitute for relevance.

## Repetition controls

- Do not reuse the same response with light paraphrasing.
- Do not engage the same post twice unless responding to a new inbound reply.
- Do not target the same account in multiple daily windows when the cooldown applies.
