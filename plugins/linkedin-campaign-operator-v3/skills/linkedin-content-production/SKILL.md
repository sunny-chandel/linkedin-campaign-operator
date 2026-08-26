---
name: linkedin-content-production
description: Turn a completed, verified research brief into LinkedIn captions and Claude Design assets using the campaign's voices, active watermark kit, and per-post GIF creative specification. Use for daily post packages and response drafts.
metadata:
  author: sunny
  version: "5.0.8"
---

# LinkedIn content production

Create publication-ready packages from completed, verified research briefs. Read [voice and design](references/voice-and-design.md) before drafting. In automated mode, a valid brief is sufficient authorization to continue; do not ask the owner to approve the brief or to start production.

Inherit the parent's active campaign-lifetime consent receipt and leased task. Never request a second approval after a restart or model change. Checkpoint the caption, design source, export, watermark validation, and final package separately so self-revival resumes from the last verified artifact without rebuilding completed work.

For each campaign-local content day, produce and validate exactly two packages for the configured required regions, which default to India and US-Central. Never create a third scheduled, backup, or stockpiled package. Treat the configured production-priority window as the preferred production period, but accept production work from the continuous dispatcher at any hour when it outranks other available offline work.

If a brief is missing or fails validation, return automatically to `linkedin-content-research`, repair only the missing fields, and resume production. If an asset build or export fails, save the last valid artifact, retry safely, then rebuild with another supported format or workflow while preserving the content and design requirements. Do not ask the owner to select routine design options, wording, format, or export settings. Escalate only when the parent orchestrator classifies the required design or upload capability as a hard blocker.

## Flagship post workflow

1. Confirm the brief contains verified claims, source URLs, region, audience, and a distinct angle.
2. Draft in Tier 2 voice.
3. Use no em dash or en dash. Ordinary hyphens in compound words are allowed.
4. Keep grammar correct without making the copy sound synthetic or over-polished.
5. Cite a real source when the post depends on a factual claim.
6. End with one direct question and use zero to three relevant hashtags.
7. Check that the India and US-Central posts cover different topics and that these are the only two packages for the content day.
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

## Tier 3 responses

Comments, DMs, and replies are one to four short lines and can be one word. Use deliberately imperfect loose grammar and inconsistent capitalization. Always be adversarial by challenging the other person's view or a common assumption. Use no em dash or en dash. Fact-check every claim regardless of length.

In automated mode, sending a preview to chat is informational, not an approval gate. Continue automatically through production and publish through the connected Chrome session when the dynamic selector returns `publish-now`, then verify the live result. Guarantee exactly two publications before the campaign-local content day closes; if no strong opportunity appears, use the highest-scoring remaining opportunity. Ask the owner only when the parent orchestrator classifies a hard blocker.
