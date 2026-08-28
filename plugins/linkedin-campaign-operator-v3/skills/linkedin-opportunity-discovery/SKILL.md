---
name: linkedin-opportunity-discovery
description: Find and maintain a fresh list of relevant LinkedIn conversations by checking source quality, recency, and campaign fit. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.21"
---

# LinkedIn opportunity discovery

Collect current conversation evidence for the campaign without acting on it.

Inherit the campaign configuration and current discovery task. Rotate among relevant sources based on recent yield, freshness, and regional fit. Give an unproductive source its own next-check time and continue with another useful source.

For each candidate, save identity, source, direct link, topic, region, freshness, target status, relationship evidence, previous-contact evidence, cooldown result, proposed item type, quality evidence, lifecycle status, expiry, and rejection reason.

Write discoveries atomically with `python scripts/upsert_opportunities.py <state-dir> <discoveries.json>`. Return accepted and rejected records, source yield, the current eligible count, and the next source to the parent. Never claim available supply before canonical records exist.
