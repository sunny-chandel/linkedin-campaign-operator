# Subscription optimization

This system maximizes practical use of LinkedIn services already active for the recognized owner. It does not select or purchase new subscriptions.

## Persistent artifacts

### `subscription-inventory.json`

Use one feature object per separately usable entitlement:

```json
{
  "schema_version": "1.0",
  "campaign_id": "linkedin-growth",
  "generated_at": "ISO-8601 timestamp",
  "subscription": {"product": "verified product", "tier": "verified tier"},
  "features": [
    {
      "feature_id": "stable-local-id",
      "name": "verified feature name",
      "entitled": true,
      "configured": false,
      "quota_total": 50,
      "quota_used": 10,
      "unused_capacity": null,
      "renews_at": "ISO-8601 timestamp or null",
      "pipeline_stages": ["identification-pass"],
      "campaign_relevance": 0.9,
      "evidence_strength": 0.8,
      "expiry_urgency": 0.4,
      "implementation_readiness": 1.0,
      "expected_outcome": "specific measurable outcome",
      "action_class": "candidate-discovery",
      "counts_toward_window": false,
      "fallback": "base discovery flow"
    }
  ]
}
```

All scoring inputs are numbers from 0 to 1. If a numeric quota is verified, unused capacity is calculated as `(quota_total - quota_used) / quota_total`. Otherwise use an explicitly observed `unused_capacity`. If neither is known, the scorer uses zero rather than inventing capacity.

### `subscription-utilization-plan.json`

The scorer writes a ranked feature list, eligibility status, score components, pipeline stages, outcome, action class, counting rule, and fallback. The default score is:

`30% campaign relevance + 25% unused capacity + 20% evidence strength + 15% expiry urgency + 10% implementation readiness`

Default routing:

- score 70-100: `activate-now`;
- score 45-69.99: `schedule`;
- score below 45: `monitor`;
- not entitled: `unavailable`.

Campaign configuration may change these weights and thresholds only when the values remain valid and saved campaign limits remain unchanged.

### `subscription-results.jsonl`

Append one record per setup, use, or measurement event. Include timestamp, feature ID, pipeline stage, event type, capacity consumed, linked campaign action when applicable, observed metric, result, evidence reference, and uncertainty. Never claim value without an observable result.

## Execution rules

1. Inspect the connected account and official current product information.
2. Separate product-level access from feature-level access. A product name alone is not proof that a feature is available.
3. Normalize verified features and run the deterministic scorer.
4. Complete reversible setup for `activate-now` features when it stays within already-included entitlements and introduces no purchase, plan change, billing change, paid-trial start, contract acceptance, or dependency on another account.
5. Route planned use into the existing stage. Do not create extra publishing or engagement windows.
6. Record capacity before and after use whenever the interface exposes it.
7. Attribute measurable results, then recalculate weekly. Increase priority for repeatable positive outcomes; reduce priority when the feature adds no measurable value or consumes scarce capacity inefficiently.
8. Preserve the base-flow fallback for every feature.

## Stage hooks

- Pre-flight creates or refreshes the inventory and plan.
- Identification passes consume search, alert, recommendation, viewer, lead, account, or Page insights when those exact capabilities are verified.
- Content stages can use included learning or market insight as background, but public factual claims still require independent verification.
- Campaign activity assisted by a paid feature still follows its original classification and limits.
- End-of-day analytics append outcomes and remaining capacity.
- Weekly learning may change feature priority and score inputs, but not configured limits, timing, qualification, cooldowns, or content rules.
