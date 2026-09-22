"""Transparent candidate baseline and logged-policy evaluation."""

from __future__ import annotations

import math


def rank_products(segment: dict, products: list[dict], available: set[str] | None = None) -> list[dict]:
    """Rank eligible products by heuristic purchase probability times unit margin.

    These are model scores, not calibrated real-world probabilities or uplift.
    """
    results = []
    for product in products:
        if available is not None and product["id"] not in available:
            continue
        utility = segment["affinity"].get(product["category"], 0) + 2 * (product["quality"] - 0.5) - segment["price_sensitivity"] * product["price"] / 100 + product["marketing"] - segment["reservation"]
        probability = 1 / (1 + math.exp(-max(-20, min(20, utility - 2.5))))
        margin = product["price"] - product["unit_cost"]
        results.append({"product_id": product["id"], "model_probability": probability, "unit_margin": margin, "model_value": probability * margin})
    return sorted(results, key=lambda result: (-result["model_value"], result["product_id"]))


def evaluate_logged_policy(records: list[dict], target_actions: dict[str, str]) -> dict:
    """Self-normalized IPS for a deterministic target policy.

    Requires known positive logging propensities and adequate overlap. This
    estimate is not proof of causal lift when the logging policy was confounded.
    """
    if not records:
        raise ValueError("records cannot be empty")
    weights, weighted_rewards = [], []
    for event in records:
        if not isinstance(event, dict) or set(event) != {"context_id", "action", "propensity", "reward"}:
            raise ValueError("each record needs context_id, action, propensity, and reward")
        if not isinstance(event["context_id"], str) or event["context_id"] not in target_actions:
            raise ValueError("target action missing for context")
        if not isinstance(event["action"], str):
            raise ValueError("action must be a string")
        p, reward = event["propensity"], event["reward"]
        if isinstance(p, bool) or not isinstance(p, (int, float)) or not math.isfinite(p) or not 0 < p <= 1:
            raise ValueError("propensity must be known and in (0, 1]")
        if isinstance(reward, bool) or not isinstance(reward, (int, float)) or not math.isfinite(reward):
            raise ValueError("reward must be a finite number")
        weight = 1 / p if event["action"] == target_actions[event["context_id"]] else 0
        weights.append(weight)
        weighted_rewards.append(weight * reward)
    denominator = sum(weights)
    if not denominator:
        raise ValueError("no overlap between logged and target actions")
    return {
        "method": "self_normalized_inverse_propensity",
        "estimate": sum(weighted_rewards) / denominator,
        "matched_records": sum(bool(weight) for weight in weights),
        "records": len(records),
        "effective_sample_size": denominator**2 / sum(weight**2 for weight in weights),
        "limitation": "Requires known logging propensities, overlap, and no unmeasured confounding; compare with a randomized online test.",
    }
