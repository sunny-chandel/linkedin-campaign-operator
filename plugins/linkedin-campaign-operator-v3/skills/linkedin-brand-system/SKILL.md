---
name: linkedin-brand-system
description: Create and maintain a profile-based LinkedIn watermark kit in Claude Design, check its transparent PNG exports, and use the right version in each GIF.
metadata:
  author: sunny
  version: "6.0.0-rc.20"
---

# LinkedIn brand system

Create a persistent visual identity from the recognized owner's verified LinkedIn profile. Do not turn brand creation into onboarding.

Inherit the parent's campaign configuration and leased task. Profile inspection, watermark creation, validation, and application are local reversible stages. Persist each validated export as a checkpoint so restart recovery resumes from the last good variant.

## Pre-flight workflow

1. Read the verified profile name, fixed profile URL, shortened handle, headline, profile image, niche, and visible positioning.
2. Normalize these values into `brand-profile.json` and calculate a stable identity hash.
3. Read `watermark-manifest.json`. Reuse the current kit when its identity hash matches and all exports validate.
4. If the kit is missing, invalid, or stale, open or create the campaign's Brand Identity project in Claude Design.
5. Create light and dark horizontal marks at 1600 by 320 pixels and light and dark compact avatar marks at 512 by 512 pixels. Export transparent PNG files.
6. Run `python scripts/validate_watermark.py <png>` for every export, then update the manifest.
7. Apply the kit automatically to the next asset. A chat preview is an informational progress artifact.

If the owner later supplies custom brand information, store it as an explicit override and regenerate the kit at the next pre-flight. Verified profile data supplies the default brand information.

Read [watermark system](references/watermark-system.md) when creating, refreshing, or applying the kit.

## Fixed rules

- Keep mutable brand files outside the installed plugin under the campaign data directory.
- Use the profile data to inform the design, while rendered marks remain concise and legible.
- Place a watermark on every GIF frame.
- A watermark provides visible attribution and cropping resistance; never represent it as absolute copy prevention.
