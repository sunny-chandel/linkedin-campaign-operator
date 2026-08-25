# Watermark system

## Brand profile

`brand-profile.json` contains the campaign ID, profile URL, display name, shortened handle, headline, profile-image reference, niche, discovery timestamp, custom overrides, and identity hash. The hash covers only fields that affect rendered identity.

## Required variants

- `watermark-light-horizontal.png`: 1600 by 320 transparent canvas for dark backgrounds.
- `watermark-dark-horizontal.png`: 1600 by 320 transparent canvas for light backgrounds.
- `watermark-light-compact.png`: 512 by 512 transparent canvas with avatar treatment for dark backgrounds.
- `watermark-dark-compact.png`: 512 by 512 transparent canvas with avatar treatment for light backgrounds.

The horizontal variants use the verified display name and shortened handle. Compact variants may use the verified profile image, display name, and shortened handle when all remain legible.

## Application

- Choose the light or dark variant from the background behind the mark.
- Prefer the horizontal variant when width is available and the compact variant for dense layouts.
- Render at approximately six percent of canvas height, 85 percent opacity, and four percent inset from the nearest edges.
- Keep the mark inside the composition's safe area and visible in every animation frame.
- If local contrast changes during the loop, use a subtle backing treatment from the brand system rather than switching identity mid-loop.

## Manifest

`watermark-manifest.json` records the identity hash, Claude Design project reference, each export path and checksum, dimensions, alpha validation, preferred placement, opacity, created timestamp, and last verified timestamp.

Regenerate only for a missing or invalid file, identity-hash change, or explicit custom-brand override.
