---
name: linkedin-premium-router
description: Review active LinkedIn subscription features and plan how to use included benefits within the campaign. Use for setup and weekly feature reviews.
metadata:
  author: sunny
  version: "6.0.0-rc.14"
---

# LinkedIn subscription optimizer

Use verified features that are already active and included for the selected account. The base campaign must continue when an optional feature is unavailable.

Inherit the campaign configuration and current review task. Save entitlement evidence, reversible setup, capacity, routing, and measured results so a restart does not repeat completed work.

1. Inspect visible product and feature access read-only.
2. Confirm current feature details from official documentation.
3. Record unknown values as unknown rather than inferring access or limits.
4. Normalize verified features into `subscription-inventory.json`.
5. Run `python scripts/score_subscription_features.py subscription-inventory.json --output subscription-utilization-plan.json`.
6. Use eligible, reversible, already-included features only where they support an existing campaign stage.
7. Log the setup, reversal path, usage, capacity, and measurable result.
8. Recalculate when access changes or during the weekly review.

Purchases, paid trials, plan changes, billing changes, and contracts remain outside this skill.

Read [subscription optimization](references/subscription-optimization.md) for data contracts and scoring. Read [entitlement routing](references/entitlement-routing.md) for product examples.
