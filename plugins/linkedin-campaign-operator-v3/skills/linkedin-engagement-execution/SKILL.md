---
name: linkedin-engagement-execution
description: Prepare checked, relevant LinkedIn engagement work that follows campaign limits and avoids repeats. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.12"
---

# LinkedIn engagement execution

Prepare one currently eligible engagement item selected by `linkedin-engagement-planning`.

Inherit the campaign configuration, candidate evidence, and current task. Draft the item privately, apply the voice guide, and verify relevance, timing, cooldown, previous-contact, and duplicate checks.

When the connected service reports the required capability as available, return one checked local service request to the parent. The connected service owns submission and result verification. If the capability is unavailable, save the item as ready and continue other local work.

Record only verified results in `interaction-log.jsonl`. An unclear result remains unresolved until the original request can be checked. After a verified result, update candidate lifecycle, source yield, relationship evidence, and current campaign capacity, then return control to the parent.
