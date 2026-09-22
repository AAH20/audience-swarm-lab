"""Strict public input contract for the reference experiment."""

from __future__ import annotations

import math
from typing import Any

MAX_AGENT_STEPS = 2_000_000


def _object(value: Any, label: str, required: set[str], optional: set[str] = set()) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    if required - value.keys() or value.keys() - required - optional:
        raise ValueError(f"{label} has missing or unknown keys")
    return value


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be a finite number between {low} and {high}")
    return float(value)


def _integer(value: Any, label: str, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer between {low} and {high}")
    return value


def _name(value: Any, label: str) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= 100:
        raise ValueError(f"{label} must be a nonempty string of at most 100 characters")
    return value


def validate(raw: Any) -> dict:
    top = {"schema_version", "scenario_id", "population", "steps", "runs", "seed", "neighbors", "segments", "products", "arms", "research_question", "documents", "economics"}
    s = _object(raw, "scenario", top - {"documents", "economics"}, {"documents", "economics"})
    if s["schema_version"] != "0.1.0":
        raise ValueError("unsupported schema_version")
    _name(s["scenario_id"], "scenario_id")
    _name(s["research_question"], "research_question")
    n = _integer(s["population"], "population", 10, 5000)
    steps = _integer(s["steps"], "steps", 1, 100)
    runs = _integer(s["runs"], "runs", 1, 200)
    _integer(s["seed"], "seed", 0, 2**32 - 1)
    neighbors = _integer(s["neighbors"], "neighbors", 2, min(30, n - 1))
    if neighbors % 2:
        raise ValueError("neighbors must be even")
    if not isinstance(s["segments"], list) or not 1 <= len(s["segments"]) <= 20:
        raise ValueError("segments must have 1-20 entries")
    segment_names: set[str] = set()
    total_share = 0.0
    for seg in s["segments"]:
        keys = {"id", "share", "affinity", "price_sensitivity", "peer_influence", "reservation"}
        _object(seg, "segment", keys)
        name = _name(seg["id"], "segment.id")
        if name in segment_names:
            raise ValueError("duplicate segment id")
        segment_names.add(name)
        total_share += _number(seg["share"], "share", 0, 1)
        _number(seg["price_sensitivity"], "price_sensitivity", 0, 5)
        _number(seg["peer_influence"], "peer_influence", 0, 5)
        _number(seg["reservation"], "reservation", -5, 5)
        if not isinstance(seg["affinity"], dict):
            raise ValueError("affinity must be an object")
        for category, score in seg["affinity"].items():
            _name(category, "category")
            _number(score, "affinity", -5, 5)
    if not math.isclose(total_share, 1.0, abs_tol=1e-8):
        raise ValueError("segment shares must sum to one")
    if not isinstance(s["products"], list) or not 1 <= len(s["products"]) <= 12:
        raise ValueError("products must have 1-12 entries")
    product_names: set[str] = set()
    for p in s["products"]:
        _object(p, "product", {"id", "category", "price", "unit_cost", "quality", "marketing", "marketing_cost_per_step"})
        name = _name(p["id"], "product.id")
        if name in product_names:
            raise ValueError("duplicate product id")
        product_names.add(name)
        _name(p["category"], "category")
        for field, high in (("price", 10000), ("unit_cost", 10000), ("quality", 1), ("marketing", 1), ("marketing_cost_per_step", 100000)):
            _number(p[field], field, 0, high)
        if p["unit_cost"] > p["price"]:
            raise ValueError("unit_cost exceeds price")
    if not isinstance(s["arms"], list) or len(s["arms"]) > 5:
        raise ValueError("arms must have at most five interventions")
    arm_names = {"baseline"}
    for arm in s["arms"]:
        _object(arm, "arm", {"id", "start_step", "product_id", "changes"})
        name = _name(arm["id"], "arm.id")
        if name in arm_names:
            raise ValueError("duplicate or reserved arm id")
        arm_names.add(name)
        _integer(arm["start_step"], "start_step", 1, steps)
        if arm["product_id"] not in product_names:
            raise ValueError("arm references unknown product")
        changes = _object(arm["changes"], "changes", set(), {"price", "quality", "marketing", "marketing_cost_per_step"})
        if not changes:
            raise ValueError("arm changes cannot be empty")
        for field, value in changes.items():
            _number(value, field, 0, 1 if field in {"quality", "marketing"} else 100000 if field == "marketing_cost_per_step" else 10000)
    if n * steps * runs * (1 + len(s["arms"])) > MAX_AGENT_STEPS:
        raise ValueError("experiment exceeds agent-step work budget")
    if "documents" in s:
        if not isinstance(s["documents"], list) or len(s["documents"]) > 100:
            raise ValueError("documents must have at most 100 entries")
        ids = set()
        for doc in s["documents"]:
            _object(doc, "document", {"id", "text", "source", "license"})
            doc_id = _name(doc["id"], "document.id")
            if doc_id in ids:
                raise ValueError("duplicate document id")
            ids.add(doc_id)
            if not isinstance(doc["text"], str) or len(doc["text"]) > 20000:
                raise ValueError("document text is invalid or too long")
            _name(doc["source"], "document.source")
            _name(doc["license"], "document.license")
    if "economics" in s:
        _object(s["economics"], "economics", {"cpu_cost_per_million_agent_steps", "graph_index_cost_per_scenario", "storage_and_observability_cost", "operating_allowance_fraction"})
        for key, value in s["economics"].items():
            _number(value, key, 0, 10000 if key != "operating_allowance_fraction" else 5)
    return s
