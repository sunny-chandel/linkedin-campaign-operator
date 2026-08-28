---
name: linkedin-regional-intelligence
description: Allocate the six-post LinkedIn portfolio across core and exploratory regions using demographic observations, time-zone opportunity, performance, and spillover learning. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.7"
---

# LinkedIn regional intelligence

Read `regional-performance.json`, equal-age analytics, qualified-target activity, audience location and seniority, and timing history. Store observations with evidence and confidence.

Until sufficient evidence exists, allocate two India, two US, one UK/EU, and one APAC slot. Thereafter allocate four core and two exploratory slots using 70/20/10 learning while retaining at least one India and one US slot.

Run `python scripts/allocate_regions.py <state-dir> --record`. Return the six slots, mode, supporting evidence, time-zone opportunity scores, and next exploration measurement to the parent. Do not publish or produce content directly.
