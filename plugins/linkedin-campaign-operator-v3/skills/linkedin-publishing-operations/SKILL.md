---
name: linkedin-publishing-operations
description: Keep a ready collection of LinkedIn posts, maintain variety and spacing, confirm published results, schedule reviews, and catch up delayed work. Used automatically by the campaign orchestrator.
metadata:
  author: sunny
  version: "6.0.0-rc.11"
---

# LinkedIn publishing operations

Use `content-pipeline.json` and `publication-evidence.jsonl` as the publishing ledger. Maintain six validated unpublished normal packages, six verified posts as the rolling target, and eight as the rolling cap.

Before publication verify research brief, claims, caption, asset, watermark, package validation, freshness, portfolio role, timing score, and the absolute 120-minute spacing floor. The six normal portfolio slots must include India and US, at least four pillars, at least three format treatments, and no consecutive topic, angle, or format repeat. Keep at most one unpublished recovery package.

Before live execution, complete the leased `rolling-output-evaluation` task with either a scored `publish-now` decision of at least 65 or `continue-investigation` plus an exact future `next_evaluation_at`. Live state begins only after external verification, not when an asset becomes ready.

When the dispatcher leases the resulting `publication-execution` task, call the parent `enqueue_external_action.py`. It derives the exact validated caption and media path from the canonical package. The interactive host's stage ends after the atomic enqueue; the outbox daemon uploads the image, publishes through the official API, read-verifies the post URN, and records completion evidence. Missing daemon readiness is the technical state `executor-setup-pending` with an exact capability list.

Run `scripts/publishing_ledger.py` to audit inventory or record verified publication evidence. After publication, mark the package published, create the replenishment requirement, and schedule snapshots at 30, 120, 360, and 1,440 minutes. Revalidate packages after an outage and regenerate stale ones. Ambiguous publications remain quarantined until their original outcome is reconciled.
