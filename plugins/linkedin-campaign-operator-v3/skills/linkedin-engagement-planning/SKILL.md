---
name: linkedin-engagement-planning
description: Build a relevant LinkedIn engagement plan by checking quality, timing, prior contact, duplicates, and regional fit before preparing any activity.
metadata:
  author: sunny
  version: "6.0.0-rc.19"
---

# LinkedIn engagement planning

Select high-quality, currently relevant conversation opportunities without repeating people, posts, or response patterns.

Inherit the campaign configuration and current planning task. Use the configured action classes, limits, regions, quality floor, and cooldowns. Persist each qualified candidate immediately so a restart does not lose discovery work.

## Planning workflow

1. Start with genuine inbound conversation evidence and current relationship signals.
2. Consider fresh posts from relevant accounts already supported by campaign evidence.
3. Check topic fit, professional relevance, freshness, region, and potential to add useful context.
4. Apply account identity, availability, previous-contact, cooldown, duplicate, and campaign-limit gates before drafting.
5. Score eligible items with `python scripts/rank_actions.py` using the current campaign mode and a small requested limit.
6. Draft only the selected items and save machine-readable rejection reasons for the rest.
7. Return the strongest eligible item to `linkedin-engagement-execution`.

Do not create filler activity when no quality candidate exists. Rotate to a different evidence source, save the next check, and return to the parent.

Read [queue rules](references/queue-rules.md) for candidate fields, scoring, cooldown, and repetition checks.
