#!/usr/bin/env python3
"""Rank eligible LinkedIn actions by predicted qualified-growth value."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


WEIGHTS = {
    "qualified_growth": 0.35,
    "audience_spillover": 0.20,
    "conversation_probability": 0.15,
    "target_relevance": 0.15,
    "freshness_timing": 0.10,
    "historical_performance": 0.05,
}
HARD_GATES = ("action_available",)
VALID_LANES = {"proactive", "soft-reciprocity", "direct-inbound"}
RECOVERY_TIERS = {
    "normal": {"threshold": 65.0, "followers": 3000, "cooldown_hours": 72},
    "expansion": {"threshold": 60.0, "followers": 2000, "cooldown_hours": 48},
    "intensive": {"threshold": 55.0, "followers": 1000, "cooldown_hours": 24},
}


def bounded(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a number from 0 to 1")
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise ValueError(f"{field} must be a number from 0 to 1")
    return number


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidates", type=Path)
    parser.add_argument("--threshold", type=float, default=65.0)
    parser.add_argument("--mode", choices=tuple(RECOVERY_TIERS), default="normal")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 0 <= args.threshold <= 100:
        parser.error("threshold must be from 0 to 100")
    if not 1 <= args.limit <= 10:
        parser.error("limit must be from 1 to 10")

    try:
        data = json.loads(args.candidates.read_text(encoding="utf-8"))
        candidates = data.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError("candidates must be an array")
        eligible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        budget = data.get("budget", {})
        if not isinstance(budget, dict):
            raise ValueError("budget must be an object")
        base_used = int(budget.get("rolling_24h_actions", budget.get("base_actions_used", 0)))
        base_ceiling = int(budget.get("rolling_action_cap", budget.get("base_daily_ceiling", 200)))
        if not 0 <= base_used <= base_ceiling or base_ceiling != 200:
            raise ValueError("budget must use the 200-action rolling cap with valid usage")
        direct_overage_allowed = budget.get("direct_reply_overage_allowed", True) is True
        tier = RECOVERY_TIERS[args.mode]
        threshold = max(55.0, tier["threshold"], args.threshold if "--threshold" in sys.argv else tier["threshold"])
        new_target_min_followers = max(1000, tier["followers"])
        concentration_penalty = bounded(data.get("concentration_penalty", 0), "concentration_penalty")
        concentration_penalty_weight = bounded(
            data.get("concentration_penalty_weight", 0.20), "concentration_penalty_weight"
        )
        minimum_marginal_value = bounded(
            data.get("minimum_expected_marginal_value", 0.65),
            "minimum_expected_marginal_value",
        )
        for position, candidate in enumerate(candidates):
            if not isinstance(candidate, dict):
                raise ValueError(f"candidates[{position}] must be an object")
            candidate_id = candidate.get("candidate_id")
            if not isinstance(candidate_id, str) or not candidate_id:
                raise ValueError(f"candidates[{position}].candidate_id must be set")
            lane = candidate.get("lane", "proactive")
            if lane not in VALID_LANES:
                raise ValueError(f"{candidate_id}.lane is invalid")
            failed_gates = [gate for gate in HARD_GATES if candidate.get(gate) is not True]
            if lane != "direct-inbound":
                if candidate.get("capacity_available", True) is not True:
                    failed_gates.append("capacity_available")
                if candidate.get("cooldown_passed") is not True:
                    failed_gates.append("cooldown_passed")
                if candidate.get("target_status") == "new":
                    follower_count = candidate.get("follower_count")
                    if (
                        isinstance(follower_count, bool)
                        or not isinstance(follower_count, (int, float))
                        or follower_count < new_target_min_followers
                    ):
                        failed_gates.append("new_target_min_followers")
                elif candidate.get("qualified") is not True:
                    failed_gates.append("qualified")
                if base_used >= base_ceiling:
                    failed_gates.append("base_daily_ceiling")
            elif base_used >= base_ceiling and not direct_overage_allowed:
                failed_gates.append("direct_reply_overage_allowed")
            if lane == "soft-reciprocity" and not candidate.get("triggering_signal"):
                failed_gates.append("triggering_signal")
            action_type = str(candidate.get("action_type") or "").lower()
            if lane != "direct-inbound" and action_type in {"dm", "message", "direct-message"}:
                if candidate.get("connection_status") not in {"existing", "connected"}:
                    failed_gates.append("existing_connection_required_for_dm")
                prior_evidence = candidate.get("prior_interaction_evidence")
                if prior_evidence is not True and not isinstance(prior_evidence, dict):
                    failed_gates.append("prior_interaction_required_for_dm")
            if failed_gates:
                rejected.append(
                    {
                        "candidate_id": candidate_id,
                        "lane": lane,
                        "reason": "hard-gate",
                        "failed_gates": list(dict.fromkeys(failed_gates)),
                    }
                )
                continue
            components = {
                name: bounded(candidate.get(name, 0), f"{candidate_id}.{name}")
                for name in WEIGHTS
            }
            marginal_value = bounded(
                candidate.get("expected_marginal_value", 1),
                f"{candidate_id}.expected_marginal_value",
            )
            if lane != "direct-inbound" and marginal_value < minimum_marginal_value:
                rejected.append(
                    {
                        "candidate_id": candidate_id,
                        "lane": lane,
                        "reason": "marginal-value-decline",
                        "expected_marginal_value": marginal_value,
                    }
                )
                continue
            raw_score = sum(components[name] * WEIGHTS[name] for name in WEIGHTS)
            applied_penalty = 0 if lane == "direct-inbound" else concentration_penalty * concentration_penalty_weight
            score = round(max(0, raw_score - applied_penalty) * 100, 2)
            ranked = {
                **candidate,
                "lane": lane,
                "score_components": components,
                "expected_marginal_value": marginal_value,
                "concentration_penalty_applied": round(applied_penalty * 100, 2),
                "action_score": score,
            }
            if lane == "direct-inbound" or score >= threshold:
                eligible.append(ranked)
            else:
                rejected.append({"candidate_id": candidate_id, "reason": "below-threshold", "action_score": score})
        lane_priority = {"direct-inbound": 0, "soft-reciprocity": 1, "proactive": 2}
        eligible.sort(
            key=lambda item: (
                lane_priority[item["lane"]],
                -item["action_score"],
                item["candidate_id"],
            )
        )
        selected: list[dict[str, Any]] = []
        eligible_not_selected: list[dict[str, Any]] = []
        selected_soft_targets: set[str] = set()
        projected_base = base_used
        projected_overage = int(budget.get("direct_reply_overage", 0) or 0)
        for item in eligible:
            if len(selected) >= args.limit:
                eligible_not_selected.append(item)
                continue
            item = dict(item)
            if item["lane"] == "soft-reciprocity":
                soft_target = str(
                    item.get("target_id")
                    or item.get("signal_actor_id")
                    or item.get("candidate_id")
                )
                if soft_target in selected_soft_targets:
                    rejected.append(
                        {
                            "candidate_id": item["candidate_id"],
                            "lane": item["lane"],
                            "reason": "soft-reciprocity-one-opportunity",
                        }
                    )
                    continue
                selected_soft_targets.add(soft_target)
            if item["lane"] == "direct-inbound":
                item["budget_class"] = "direct-inbound-outside-cap"
                projected_overage += 1
            else:
                item["budget_class"] = "base"
                projected_base += 1
            selected.append(item)
        output = {
            "schema_version": "2.0",
            "campaign_id": data.get("campaign_id"),
            "threshold": threshold,
            "active_recovery_mode": args.mode,
            "active_gates": {
                "minimum_score": threshold,
                "new_target_min_followers": new_target_min_followers,
                "cooldown_hours": tier["cooldown_hours"],
                "max_proactive_actions_per_person_per_7d": 2,
            },
            "limit": args.limit,
            "concentration_penalty": concentration_penalty,
            "concentration_penalty_weight": concentration_penalty_weight,
            "selected": selected,
            "eligible_not_selected": eligible_not_selected,
            "rejected": rejected,
            "projected_budget": {
                "rolling_24h_actions": min(projected_base, base_ceiling),
                "rolling_action_target": 160,
                "rolling_action_cap": base_ceiling,
                "direct_inbound_replies": projected_overage,
            },
            "owner_input_required": False,
            "next_step": "execute-selected" if selected else "continue-discovery",
        }
        rendered = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.write_text(rendered, encoding="utf-8")
        else:
            print(rendered, end="")
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(json.dumps({"valid": False, "error": str(exc)}), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
