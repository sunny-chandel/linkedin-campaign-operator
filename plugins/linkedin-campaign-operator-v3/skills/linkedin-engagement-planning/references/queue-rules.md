# Queue rules

## Candidate fields

Each queue item contains:

- target identifier and direct link;
- lane: `proactive`, `soft-reciprocity`, or `direct-inbound`;
- triggering signal and signal-event identifier when applicable;
- relationship strength before the proposed action;
- budget classification: `rolling-base` or `direct-inbound-outside-cap`;
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
- existing-connection and prior-interaction evidence for any proactive DM.

## Scoring

Apply qualification, cooldown, availability, and base-budget capacity as hard gates for proactive and soft-reciprocal work. Direct-inbound work is exempt from the score, qualification, and cooldown gates, but still requires the correct verified account and a working connection. Score eligible proactive and soft-reciprocal candidates with:

- 35 percent predicted qualified profile, follower, or connection growth;
- 20 percent expected audience spillover;
- 15 percent probability of substantive conversation;
- 15 percent professional and target relevance;
- 10 percent freshness and regional timing;
- 5 percent historical performance for the action, target layer, region, and current opportunity state.

Select candidates at the active tier floor: 65 normal, 60 expansion, or 55 intensive. New-target follower gates are respectively 3,000, 2,000, and 1,000; cooldowns are 72, 48, and 24 hours. Never go below intensive and always retain the twice-per-seven-days limit.

Follower count is a qualification gate for new additions, not a substitute for relevance.

Run hard gates before drafting any action text. A failed hard gate or score below the active tier is a terminal rejection for that opportunity. Persist its machine-readable reason in the canonical queue and continue discovery automatically. If selected is empty, rotate to the next measured-yield source; if selected contains even one candidate, dispatch it without waiting for a batch of ten.

## Reciprocity routing

- Comments, replies, and genuine DMs enter `direct-inbound`.
- Likes, reactions, follows, profile views when available, and connection acceptances create `soft-reciprocity` candidates.
- For a soft signal, inspect the person's newest visible relevant posts and retain at most one qualifying opportunity.
- Apply the active tier's new-target follower gate, cooldown, relevance, and score threshold.
- If no post qualifies, retain the relationship signal without forcing an action.
- A response to a reciprocal action updates relationship strength but does not reset or bypass cooldown.

## Budget and burst controls

- The rolling 24-hour counted-action target is 160 and hard cap is 200.
- Proactive and soft-reciprocal actions stop at the rolling cap.
- Direct inbound replies remain outside the cap and continue when useful.
- Every burst is capped at 10 actions.
- Do not manufacture low-quality actions to fill a burst or action debt.
- Maintain at least 40 currently executable canonical opportunities while rolling capacity remains.
- Stop a reserve pass after five pages, eight minutes, target completion, qualified yield below the configured floor, or declining marginal value. Persist every accepted candidate immediately and record the pass through the parent runtime so low-yield backoff and task rotation survive restart.

## Repetition controls

- Do not reuse the same response with light paraphrasing.
- Do not engage the same post twice unless responding to a new inbound reply.
- Do not target the same account again while the cooldown applies, regardless of when the dispatcher wakes.
