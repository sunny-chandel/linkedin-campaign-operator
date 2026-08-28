---
name: linkedin-publishing-operations
description: Keep a ready collection of LinkedIn posts, maintain variety and spacing, confirm published results, schedule reviews, and catch up delayed work. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.23"
---

# LinkedIn publishing operations

Use `content-pipeline.json` and `publication-evidence.jsonl` as the publishing ledger. Maintain the ready-package inventory and pacing configured by the campaign.

Before a package becomes service-ready, verify its research brief, claims, caption, asset, watermark, freshness, portfolio role, timing evidence, spacing, and duplicate result. Keep regional, pillar, and format variety aligned with current campaign settings.

When the connected service reports publishing capability as available, return one checked local publication request to the parent. The connected service owns upload, publication, and result verification. If it is unavailable, keep the package ready and continue other local work.

Run `scripts/publishing_ledger.py` to audit inventory or record a verified publication. After a verified result, mark the package published, add the configured replenishment requirement, and schedule the campaign's measurement checkpoints. Revalidate packages after an outage and replace stale ones. An unclear publication result remains unresolved until the original request can be verified.
