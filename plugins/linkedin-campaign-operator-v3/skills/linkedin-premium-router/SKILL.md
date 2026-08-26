---
name: linkedin-premium-router
description: Detect every active LinkedIn paid entitlement, calculate a prioritized utilization plan, configure included features, and route them through the adaptive campaign without changing fixed limits. Use for subscription inventory, optimization, setup, usage, and weekly utilization review.
metadata:
  author: sunny
  version: "5.0.6"
---

# LinkedIn subscription optimizer

The base campaign must work without a paid service. Premium features enhance only the stages they genuinely support.

Inherit the parent's active campaign-lifetime consent receipt and leased task. Never ask for a second routine approval to inspect or configure already-included reversible features. Checkpoint inventory, setup, capacity, routing, and measured results so restart recovery does not repeat completed configuration.

## Automated execution

In automated mode, inspect visible entitlements, calculate the best current use of every relevant included feature, configure it when needed, route it into the parent pipeline, and measure the result. Do this without asking the owner which feature to use. If a plan, limit, or feature cannot be verified, record it as unknown or unavailable and continue through the base campaign flow.

Here, optimize or upgrade means improve the setup and utilization of services that are already active and included. It never means buying a product, starting a paid trial, upgrading a plan, changing billing, consuming an unverified credit, or accepting a new contract.

## Automated optimization loop

1. Identify every active individual subscription, Company Page subscription, product seat, trial, and plan tier visible to the user.
2. Record the account or Page, user role, status, expiry or renewal information, feature limits, credits, and regional availability.
3. Confirm the current feature set from official LinkedIn documentation; do not infer access from a generic product name.
4. Normalize each verified feature into `subscription-inventory.json`. Preserve unknown values as `null`; never invent access, limits, or remaining credits.
5. Run `python scripts/score_subscription_features.py subscription-inventory.json --output subscription-utilization-plan.json` using the campaign's configured weights and thresholds.
6. For every `activate-now` item, perform any reversible setup required to use the already-entitled feature, then inject its usage into the mapped pipeline stage. Queue lower-priority eligible items without creating extra campaign actions or overriding adaptive scheduling.
7. Log setup changes, reversal steps, usage, capacity consumed, and measurable outcomes in `subscription-results.jsonl`.
8. Recalculate the plan when entitlement information changes, before a pipeline stage that depends on a paid feature, and during the weekly retrospective. Use measured results to adjust feature priority within the configured bounds.

The optimizer returns control to `linkedin-campaign-orchestrator` after every run. It must not pause the full pipeline for a routine choice or optional unavailable feature.

Read [subscription optimization](references/subscription-optimization.md) for the data contract, scoring model, stage hooks, and result loop. Read [entitlement routing](references/entitlement-routing.md) for product-specific examples.

## Pipeline integration

- Pre-flight: refresh inventory, compute the plan, and complete eligible setup.
- Research and content: use included insights or learning only when relevant and independently verify public factual claims.
- Investigation and reserve building: use eligible searches, saved entities, alerts, recommendations, and insights to improve candidate discovery and ranking.
- Adaptive bursts: execute selected premium-assisted actions inside the shared base budget and burst cap.
- Analytics: attribute usage and outcomes to the feature that supported them.
- Weekly retrospective: compare utilization, outcomes, remaining capacity, renewal timing, and fallback performance; then recompute priorities.

## Fixed rules

- Premium actions count toward existing action totals.
- Premium access does not override qualification, cooldown, or content rules.
- Only active, verified, already-included entitlements are eligible for automatic setup or use.
- No purchase, paid-plan upgrade, billing change, contract acceptance, or paid-trial start is authorized.
- If a premium feature is optional and unavailable, continue through the base flow.
- If entitlement or capacity cannot be verified, do not consume it and do not fabricate a utilization value.
