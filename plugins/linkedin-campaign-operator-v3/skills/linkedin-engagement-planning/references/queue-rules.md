# Queue rules

## Candidate fields

Each queue item contains:

- target identifier and direct link;
- lane: `proactive`, `soft-reciprocity`, or `direct-inbound`;
- triggering signal and signal-event identifier when applicable;
- relationship strength before the proposed action;
- budget classification: `base` or `direct-reply-overage`;
- scheduling rationale and regional-opportunity evidence;
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

Apply qualification, cooldown, availability, and base-budget capacity as hard gates for proactive and soft-reciprocal work. Direct-inbound work is exempt from the score, qualification, and cooldown gates, but remains subject to identity and platform blockers. Score eligible proactive and soft-reciprocal candidates with:

- 35 percent predicted qualified profile, follower, or connection growth;
- 20 percent expected audience spillover;
- 15 percent probability of substantive conversation;
- 15 percent professional and target relevance;
- 10 percent freshness and regional timing;
- 5 percent historical performance for the action, target layer, region, and current opportunity state.

Select only candidates scoring at least 65. Use observed campaign outcomes to update inputs without changing the fixed weights outside the weekly learning rules.

Follower count is a qualification gate for new additions, not a substitute for relevance.

## Reciprocity routing

- Comments, replies, and genuine DMs enter `direct-inbound`.
- Likes, reactions, follows, profile views when available, and connection acceptances create `soft-reciprocity` candidates.
- For a soft signal, inspect the person's newest visible relevant posts and retain at most one qualifying opportunity.
- Apply the 3,000-follower gate only to new targets, plus cooldown, relevance, and the score threshold.
- If no post qualifies, retain the relationship signal without forcing an action.
- A response to a reciprocal action updates relationship strength but does not reset or bypass cooldown.

## Budget and burst controls

- The shared base ceiling is 100 actions per campaign-local day.
- Proactive and soft-reciprocal actions stop when the base ceiling is reached.
- Direct-inbound replies consume base capacity while it remains, then increment `direct_reply_overage` and continue.
- Every burst is capped at 10 actions.
- Do not manufacture low-quality actions to fill a burst or the daily budget.
- Calculate reserve coverage from the next two predicted bursts, recent executed burst size, staleness, rejection rate, remaining base capacity, and the configured minimum and maximum. Do not assume two 10-action bursts.
- Stop a reserve pass after five pages, eight minutes, target completion, qualified yield below the configured floor, or declining marginal value. Persist every accepted candidate immediately and record the pass through the parent runtime so low-yield backoff and task rotation survive restart.

## Repetition controls

- Do not reuse the same response with light paraphrasing.
- Do not engage the same post twice unless responding to a new inbound reply.
- Do not target the same account again while the cooldown applies, regardless of when the dispatcher wakes.
