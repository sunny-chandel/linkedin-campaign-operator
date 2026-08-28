---
name: linkedin-gif-creative-intelligence
description: Observe high-performing LinkedIn GIF creators, measure their visual and motion patterns, select the strongest reference per post, and maintain a self-growing GIF rule library. Use during creator observation and before GIF production.
metadata:
  author: sunny
  version: "6.0.0-rc.8"
---

# LinkedIn GIF creative intelligence

Learn professional GIF construction from current high-information, high-interaction LinkedIn references and convert it into exact build specifications for Claude Design.

Inherit the parent's campaign configuration and leased task. Checkpoint every captured reference, measurement, promoted pattern, deletion result, and creative specification so a restarted session continues from the last durable result.

## Creator observation

1. Maintain 12 core high-performing creators and eight rotating discoveries across India, US-Central, and UK/EU.
2. Apply the 3,000-follower gate when adding a new creator. Inspect up to two current relevant GIF posts per creator; never fabricate or fill a missing reference.
3. Run LinkedIn observation when the continuous dispatcher selects creator research and the LinkedIn lane is available. During the 9:00 PM to 2:00 AM IST production-priority period, prefer stored validated references unless a higher-value fresh observation is selected.
4. Record public engagement, follower count, post age, topic, region, information quality, and reference location.
5. Inspect available GIF files with `python scripts/inspect_gif.py <gif>`.
6. Measure typography, color roles, spacing, margins, grid, panel count, simultaneous elements, information density, transitions, easing, scene order, and loop quality through visual analysis.

## Per-post selection

Normalize public engagement within the same follower tier and post-age cohort. Score every eligible reference with `python scripts/score_gif_references.py <index>` using 30 percent information quality, 25 percent normalized engagement, 20 percent visual execution, 15 percent recency, and 10 percent audience fit.

For every GIF post, promote the highest-ranked applicable pattern immediately and produce `gif-creative-spec.json`. The spec contains exact canvas, typography, color, spacing, layout, density, motion, loop, safe-area, and watermark requirements.

Read [GIF pattern system](references/gif-pattern-system.md) for schemas, scoring, deletion, and Claude Design handoff.

## Self-growing rules

- Add and update runtime patterns as evidence changes.
- A single new reference may permanently delete a contradictory older learning when its score is at least 85 and at least 15 points above the old pattern.
- Run `python scripts/promote_gif_pattern.py <library> <candidate> --capture-root <dir>` for deterministic promotion and deletion.
- Deletion removes the old runtime pattern and its supporting capture without retaining a rollback copy.
- Use only positive production standards: refined typography, balanced density, compact layouts, coordinated multi-element scenes, clear hierarchy, smooth pacing, consistent color tokens, and seamless looping.

## Format boundary

This release learns GIF patterns only. Static images, documents, and native video remain on the existing content-production path.
