---
name: linkedin-premium-router
description: Detect active LinkedIn paid products and map relevant entitled features into a campaign without changing fixed limits. Use for premium inventory, setup, and utilization review.
compatibility: Requires current LinkedIn product documentation and visible entitlement information from the connected account.
metadata:
  author: sunny
  version: "0.2.0"
---

# LinkedIn premium router

The base campaign must work without a paid service. Premium features enhance only the stages they genuinely support.

## Entitlement workflow

1. Identify every active individual subscription, Company Page subscription, product seat, trial, and plan tier visible to the user.
2. Record the account or Page, user role, status, expiry or renewal information, feature limits, credits, and regional restrictions.
3. Confirm the current feature set from official LinkedIn documentation; do not infer access from a generic product name.
4. Classify each feature as relevant now, potentially useful, unrelated, or unavailable.
5. Map relevant features to a pipeline stage, trigger, output, metric, and fallback.
6. Configure the settings and integrations required for relevant active features.
7. Log configuration changes and how to reverse them.

Read [entitlement routing](references/entitlement-routing.md) for product-specific examples.

## Fixed rules

- Premium actions count toward existing action totals.
- Premium access does not override qualification, cooldown, or content rules.
- If a premium feature is optional and unavailable, continue through the base flow.
- If the entitlement cannot be verified, do not use it.
