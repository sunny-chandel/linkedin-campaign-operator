# GIF pattern system

## Creator registry

`creator-registry.json` stores 12 core creators and eight rotating creators with profile URL, follower count, niche, region, reason for inclusion, discovery date, and last observation. Replace rotating creators when stronger qualified candidates appear.

## Reference index

Each `gif-reference-index.json` item contains:

- reference and creator IDs;
- direct post and local capture references;
- follower tier and post-age cohort;
- reactions, comments, reposts, and normalized engagement percentile;
- information-quality, visual-execution, recency, and audience-fit values from zero to one;
- canvas, file size, frames, duration, loop, palette, transparency, typography, color, grid, panels, density, transitions, easing, and scene sequence;
- conflicting pattern ID when applicable.

Age cohorts are 0-24 hours, 1-3 days, 4-7 days, and 8-30 days. Follower tiers are 3,000-9,999, 10,000-49,999, 50,000-249,999, and 250,000 or more. Rank weighted public interactions within the matching cohort rather than comparing raw totals across unlike creators.

## Reference scoring

`reference_score = 100 × (0.30 × information_quality + 0.25 × normalized_engagement + 0.20 × visual_execution + 0.15 × recency + 0.10 × audience_fit)`

Select the highest score that matches the current post's content requirements and passes validation. Record unavailable public metrics as unknown and exclude them from unsupported claims.

## Permanent deletion

If a selected reference identifies `contradicts_pattern_id`, the promotion helper deletes the old pattern only when the new score is at least 85 and at least 15 points greater than the old score. It deletes only capture paths resolved inside the declared capture root. This deletion is irreversible and intentionally has no rollback record.

## Creative specification

`gif-creative-spec.json` contains the selected reference ID and score; canvas dimensions; frame count; duration and frame-timing sequence; loop count and seam; font families or closest available alternatives; font sizes, weights, and line heights; color tokens; margins and grid; panels and simultaneous elements; per-scene copy limits; transitions and easing; watermark variant, placement, scale, and opacity; mobile-legibility checks; and export limits.

LinkedIn GIF output must remain within 100 MB, 500 frames, and 36,152,320 pixels. Upload it through the supported image-media path, not as native video.
