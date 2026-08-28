---
name: linkedin-opportunity-discovery
description: Maintain the canonical LinkedIn engagement opportunity queue by rotating signal sources, validating evidence, applying expiry, atomically upserting candidates, and measuring source yield. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.7"
---

# LinkedIn opportunity discovery

Accept a dispatcher discovery task, inherit its campaign configuration, and return canonical candidate evidence. Routine choices come from the task and current recovery tier.

Read the active recovery tier and rotate through the source recorded on the task. A low-yield source receives source-specific backoff; immediately return the next unblocked source while action debt remains. Allocate future passes 70/20/10 across proven, promising, and exploratory sources.

For every candidate capture identity, source, lane, score evidence, follower evidence, target status, post freshness, cooldown result, weekly interaction count, action type, triggering signal, relationship evidence, lifecycle status, expiry, and rejection reason. Do not increment reserve before records exist.

Write discoveries atomically with `python scripts/upsert_opportunities.py <state-dir> <discoveries.json>`. `engagement-opportunities.json` is the only candidate-count authority. Return accepted, rejected, canonical eligible count, source yield, backoff, and next source to the parent.
