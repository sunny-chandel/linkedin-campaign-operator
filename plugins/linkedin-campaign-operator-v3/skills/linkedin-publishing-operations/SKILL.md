---
name: linkedin-publishing-operations
description: Maintain the six-package rolling LinkedIn inventory, enforce portfolio diversity and spacing, execute and verify publications, schedule analytics, and recover post debt. Internal child of linkedin-campaign-orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.1"
---

# LinkedIn publishing operations

Use `content-pipeline.json` and `publication-evidence.jsonl` as the publishing ledger. Maintain six validated unpublished normal packages, six verified posts as the rolling target, and eight as the rolling cap.

Before publication verify research brief, claims, caption, asset, watermark, package validation, freshness, portfolio role, timing score, and the absolute 120-minute spacing floor. The six normal portfolio slots must include India and US, at least four pillars, at least three format treatments, and no consecutive topic, angle, or format repeat. Keep at most one unpublished recovery package.

Before live execution, complete the leased `rolling-output-evaluation` task with either a scored `publish-now` decision of at least 65 or `continue-investigation` plus an exact future `next_evaluation_at`. Never mark a package live merely because its asset is ready.

Run `scripts/publishing_ledger.py` to audit inventory or record verified publication evidence. After publication, mark the package published, create the replenishment requirement, and schedule snapshots at 30, 120, 360, and 1,440 minutes. Revalidate packages after an outage and regenerate stale ones. Never duplicate an ambiguous publication.
