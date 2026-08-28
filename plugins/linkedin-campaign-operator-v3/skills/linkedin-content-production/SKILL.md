---
name: linkedin-content-production
description: Turn verified research into ready-to-use LinkedIn captions, response drafts, and Claude Design assets that match the campaign voice and visual style.
metadata:
  author: sunny
  version: "6.0.0-rc.14"
---

# LinkedIn content production

Create publication-ready packages from completed research briefs. Read [voice and design](references/voice-and-design.md) before drafting.

Inherit the campaign configuration and current production task. Save the caption, design source, export, watermark validation, and final package separately so a restart resumes from the last verified artifact.

Maintain the ready-package inventory configured by the parent. Replenish only the missing inventory and avoid stockpiling stale work. If a brief fails validation, return to `linkedin-content-research`, repair the missing fields, and resume this package.

## Package workflow

1. Confirm the brief contains verified claims, source URLs, region, audience, and a distinct angle.
2. Draft in the configured voice.
3. Use no em dash or en dash. Ordinary hyphens in compound words are allowed.
4. Keep grammar natural and accurate.
5. Cite a real source when a factual claim depends on it.
6. End with one direct question and use zero to three relevant hashtags when suitable.
7. Check portfolio variety against the configured regions, pillars, and formats.
8. Create an asset brief with hierarchy, copy limits, dimensions, accessibility, and attribution.
9. For a GIF, run `linkedin-gif-creative-intelligence` before building the asset.
10. Apply the current validated watermark.
11. Build and refine the asset in Claude Design.
12. Verify legibility, factual accuracy, specification conformance, and export integrity.
13. Return the completed package to `linkedin-publishing-operations`.

## Package contents

Include the final caption, asset path, alt text, sources, claim notes, target region, freshness, timing evidence, experiment ID when present, duplicate result, watermark identity, format details, and validation evidence for each completed stage.

Short response drafts should be specific to the conversation, useful, factually checked, and concise. Avoid canned phrasing, forced disagreement, or deliberate grammar mistakes.
