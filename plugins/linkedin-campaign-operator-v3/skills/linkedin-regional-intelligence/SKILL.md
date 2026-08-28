---
name: linkedin-regional-intelligence
description: Balance LinkedIn posts across regions using audience fit, time zones, and past results. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.27"
---

# LinkedIn regional intelligence

Read `regional-performance.json`, comparable analytics, qualified-audience activity, audience location, seniority, and timing history. Save observations with evidence and confidence.

Use the campaign's configured inventory size and required regions. When evidence is sparse, distribute ready packages across the owner's primary regions and one measured exploration opportunity. With sufficient evidence, favor regions producing qualified results while retaining deliberate exploration.

Run `python scripts/allocate_regions.py <state-dir> --record`. Return the configured slots, supporting evidence, time-zone opportunity scores, and next exploration measurement to the parent. Do not publish or produce content directly.
