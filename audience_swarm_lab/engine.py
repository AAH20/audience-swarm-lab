"""Paired, reproducible multi-product audience experiments."""

from __future__ import annotations

import hashlib
import json
import math
import random
from copy import deepcopy

from .context import retrieve
from .contracts import validate

MODEL_VERSION = "0.1.0"


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    low = int(position)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[min(low + 1, len(ordered) - 1)] * fraction


def _summary(values: list[float]) -> dict:
    return {"mean": sum(values) / len(values), "p05": _quantile(values, 0.05), "p95": _quantile(values, 0.95)}


def _choose(utilities: list[float], draw: float) -> int | None:
    # Outside option of 2.5 prevents automatic purchase just because a
    # candidate exists. All utilities are clipped for numeric stability.
    weights = [math.exp(2.5)] + [math.exp(max(-20, min(20, u))) for u in utilities]
    threshold = draw * sum(weights)
    total = 0.0
    for index, weight in enumerate(weights):
        total += weight
        if threshold < total:
            return None if index == 0 else index - 1
    return len(utilities) - 1


def _one_arm(segments: list[dict], graph: list[list[int]], draws: list[list[float]], products: list[dict], arm: dict | None) -> dict:
    adopted: list[str | None] = [None] * len(segments)
    trajectory = []
    contribution = 0.0
    marketing_cost = 0.0
    for step, step_draws in enumerate(draws, start=1):
        offerings = deepcopy(products)
        if arm and step >= arm["start_step"]:
            next(p for p in offerings if p["id"] == arm["product_id"]).update(arm["changes"])
        # Simultaneous transitions: peers influence the next state only.
        next_adopted = adopted.copy()
        step_contribution = 0.0
        new = 0
        for index, segment in enumerate(segments):
            if adopted[index] is not None:
                continue
            utilities = []
            for product in offerings:
                peer_share = sum(adopted[peer] == product["id"] for peer in graph[index]) / len(graph[index])
                utility = (
                    segment["affinity"].get(product["category"], 0)
                    + 2 * (product["quality"] - 0.5)
                    - segment["price_sensitivity"] * product["price"] / 100
                    + product["marketing"]
                    + segment["peer_influence"] * peer_share
                    - segment["reservation"]
                )
                utilities.append(utility)
            choice = _choose(utilities, step_draws[index])
            if choice is not None:
                product = offerings[choice]
                next_adopted[index] = product["id"]
                step_contribution += product["price"] - product["unit_cost"]
                new += 1
        adopted = next_adopted
        step_marketing = sum(product["marketing_cost_per_step"] for product in offerings)
        contribution += step_contribution
        marketing_cost += step_marketing
        trajectory.append({"step": step, "new_adopters": new, "adoption_share": sum(p is not None for p in adopted) / len(adopted), "cumulative_net_contribution": contribution - marketing_cost})
    counts = {p["id"]: adopted.count(p["id"]) for p in products}
    return {"adoption_share": trajectory[-1]["adoption_share"], "net_contribution": contribution - marketing_cost, "gross_contribution": contribution, "marketing_cost": marketing_cost, "product_adopters": counts, "trajectory": trajectory}


def simulate(raw: dict) -> dict:
    scenario = validate(raw)
    digest = hashlib.sha256(json.dumps(scenario, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    names = ["baseline"] + [arm["id"] for arm in scenario["arms"]]
    outcomes = {name: [] for name in names}
    n, steps, runs = scenario["population"], scenario["steps"], scenario["runs"]
    for trial in range(runs):
        rng = random.Random(scenario["seed"] + trial)
        agents = rng.choices(scenario["segments"], weights=[s["share"] for s in scenario["segments"]], k=n)
        graph = [sorted({(i + offset) % n for offset in range(-scenario["neighbors"] // 2, scenario["neighbors"] // 2 + 1) if offset}) for i in range(n)]
        draws = [[rng.random() for _ in range(n)] for _ in range(steps)]
        for name, arm in zip(names, [None] + scenario["arms"]):
            outcomes[name].append(_one_arm(agents, graph, draws, scenario["products"], arm))
    summaries = {}
    for name, trials in outcomes.items():
        summaries[name] = {
            "adoption_share": _summary([t["adoption_share"] for t in trials]),
            "net_contribution": _summary([t["net_contribution"] for t in trials]),
            "gross_contribution": _summary([t["gross_contribution"] for t in trials]),
            "marketing_cost": _summary([t["marketing_cost"] for t in trials]),
            "product_adopters": {p["id"]: _summary([t["product_adopters"][p["id"]] for t in trials]) for p in scenario["products"]},
            "trajectory": [{"step": step + 1, "adoption_share": _summary([t["trajectory"][step]["adoption_share"] for t in trials])} for step in range(steps)],
        }
    effects = {name: {metric: _summary([outcomes[name][trial][metric] - outcomes["baseline"][trial][metric] for trial in range(runs)]) for metric in ("adoption_share", "net_contribution", "gross_contribution")} for name in names[1:]}
    agent_steps = n * steps * runs * len(names)
    economics = scenario.get("economics")
    estimate = None
    if economics:
        cpu = agent_steps / 1_000_000 * economics["cpu_cost_per_million_agent_steps"]
        direct = cpu + economics["graph_index_cost_per_scenario"] + economics["storage_and_observability_cost"]
        estimate = {"currency": "USD", "basis": "illustrative input rates; excludes provider calls and human review", "agent_steps": agent_steps, "cpu": cpu, "graph_index": economics["graph_index_cost_per_scenario"], "storage_and_observability": economics["storage_and_observability_cost"], "direct": direct, "with_operating_allowance": direct * (1 + economics["operating_allowance_fraction"])}
    return {
        "model_version": MODEL_VERSION,
        "scenario_id": scenario["scenario_id"],
        "scenario_sha256": digest,
        "seed": scenario["seed"],
        "runs": runs,
        "agent_steps": agent_steps,
        "interpretation": "Synthetic scenarios only; run quantiles are not real-world confidence intervals or causal estimates.",
        "evidence_label": "SYNTHETIC_SCENARIO",
        "context_hits": retrieve(scenario["research_question"], scenario.get("documents", [])),
        "arms": summaries,
        "paired_effects": effects,
        "cost_estimate": estimate,
    }
