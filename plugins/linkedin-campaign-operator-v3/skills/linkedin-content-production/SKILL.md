---
name: linkedin-content-production
description: Turn a completed, verified research brief into LinkedIn captions and Claude Design assets using the campaign's voices, active watermark kit, and per-post GIF creative specification. Use for daily post packages and response drafts.
metadata:
  author: sunny
  version: "6.0.0-rc.8"
---

# LinkedIn content production

Create publication-ready packages from completed, verified research briefs. Read [voice and design](references/voice-and-design.md) before drafting. In automated mode, a valid brief is the complete input contract for production.

Inherit the parent's campaign configuration and leased task. A restart or model change resumes the same stage. Checkpoint the caption, design source, export, watermark validation, and final package separately so self-revival resumes from the last verified artifact without rebuilding completed work.

Maintain six validated unpublished normal packages in the rolling inventory and replenish one after every publication. Build from the six selected briefs and regional allocation. When the dispatcher issues recovery content, produce exactly one fresh, distinct package and store no second unpublished recovery package.

If a brief is missing or fails validation, return automatically to `linkedin-content-research`, repair only the missing fields, and resume production. If an asset build or export fails, save the last valid artifact, retry safely, then rebuild with another supported format or workflow while preserving the content and design requirements. Campaign state and the portfolio model select routine design options, wording, format, and export settings. Escalate only when the parent orchestrator classifies the required design or upload capability as a hard blocker.

## Flagship post workflow

1. Confirm the brief contains verified claims, source URLs, region, audience, and a distinct angle.
2. Draft in Tier 2 voice.
3. Use no em dash or en dash. Ordinary hyphens in compound words are allowed.
4. Keep grammar correct without making the copy sound synthetic or over-polished.
5. Cite a real source when the post depends on a factual claim.
6. End with one direct question and use zero to three relevant hashtags.
7. Validate the six-post portfolio: at least one India and one US package, four or more pillars, three or more format treatments, and no consecutive topic, angle, or format repeat.
8. Create an asset brief with hierarchy, copy limits, dimensions, accessibility requirements, and source attribution.
9. When the asset is a GIF, run `linkedin-gif-creative-intelligence` and require a valid `gif-creative-spec.json` before build.
10. Load the current `watermark-manifest.json` and route the correct validated watermark variant.
11. Build and iterate in Claude Design using the current supported workflow.
12. Export, verify legibility, content accuracy, GIF specification conformance, and watermark presence on every frame, then produce a publication package.
13. Pass each completed package to the parent's dynamic publication selector. Do not assign a fixed window or fixed separation.

## Publication package contract

Include:

- final caption;
- final asset path or export reference;
- alt text;
- source list;
- claim-verification notes;
- target region and dynamic opportunity evidence;
- publication-time score components, cannibalization state, and latest allowed opportunity;
- experiment ID, if applicable;
- duplicate check result;
- final validation status.
- watermark variant and manifest identity hash;
- GIF reference, pattern, metrics, and creative-spec validation when applicable.
- region, demographic hypothesis, freshness expiry, portfolio role, competing angle, intended growth outcome, content pillar, and format treatment;
- stage evidence for research, claims, caption, asset, watermark, validation, and publication decision.

## Tier 3 responses

Comments and replies are one to four short lines and can be one word. Use deliberately imperfect loose grammar and varied capitalization. Add value by constructively challenging a view or a common assumption. Use no em dash or en dash. Fact-check every claim regardless of length.

In automated mode, a chat preview is an informational progress artifact. Continue through production and return the validated package to publishing operations. Maintain six verified normal publications in the rolling 24-hour window. Recovery publications may raise the total to eight, with eight as the cap.
