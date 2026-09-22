"""SQLite reference BI store for experiment results.

This is an offline contract demonstrator, not a distributed Iceberg warehouse.
"""

from __future__ import annotations

import sqlite3
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS experiments (
  scenario_sha256 TEXT PRIMARY KEY,
  scenario_id TEXT NOT NULL,
  model_version TEXT NOT NULL,
  evidence_label TEXT NOT NULL,
  runs INTEGER NOT NULL,
  agent_steps INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS arm_metrics (
  scenario_sha256 TEXT NOT NULL REFERENCES experiments(scenario_sha256),
  arm_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  mean REAL NOT NULL,
  p05 REAL NOT NULL,
  p95 REAL NOT NULL,
  PRIMARY KEY (scenario_sha256, arm_id, metric)
);
CREATE TABLE IF NOT EXISTS paired_effects (
  scenario_sha256 TEXT NOT NULL REFERENCES experiments(scenario_sha256),
  arm_id TEXT NOT NULL,
  metric TEXT NOT NULL,
  mean REAL NOT NULL,
  p05 REAL NOT NULL,
  p95 REAL NOT NULL,
  PRIMARY KEY (scenario_sha256, arm_id, metric)
);
"""

METRICS = ("adoption_share", "net_contribution", "gross_contribution", "marketing_cost")


def ingest(connection: sqlite3.Connection, result: dict[str, Any]) -> None:
    """Idempotently store an unmodified synthetic result by its scenario digest."""
    if result.get("evidence_label") != "SYNTHETIC_SCENARIO":
        raise ValueError("reference store accepts only labeled synthetic results")
    digest = result.get("scenario_sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("scenario_sha256 must be a 64-character digest")
    connection.executescript(SCHEMA)
    with connection:
        existing = connection.execute("SELECT scenario_id, model_version FROM experiments WHERE scenario_sha256 = ?", (digest,)).fetchone()
        if existing and existing != (result["scenario_id"], result["model_version"]):
            raise ValueError("digest collision or incompatible experiment metadata")
        connection.execute(
            "INSERT OR IGNORE INTO experiments VALUES (?, ?, ?, ?, ?, ?)",
            (digest, result["scenario_id"], result["model_version"], result["evidence_label"], result["runs"], result["agent_steps"]),
        )
        for arm, metrics in result["arms"].items():
            for metric in METRICS:
                values = metrics[metric]
                connection.execute(
                    "INSERT OR REPLACE INTO arm_metrics VALUES (?, ?, ?, ?, ?, ?)",
                    (digest, arm, metric, values["mean"], values["p05"], values["p95"]),
                )
        for arm, metrics in result["paired_effects"].items():
            for metric, values in metrics.items():
                connection.execute(
                    "INSERT OR REPLACE INTO paired_effects VALUES (?, ?, ?, ?, ?, ?)",
                    (digest, arm, metric, values["mean"], values["p05"], values["p95"]),
                )


def report(connection: sqlite3.Connection) -> list[dict]:
    connection.executescript(SCHEMA)
    rows = connection.execute(
        """SELECT e.scenario_id, e.scenario_sha256, e.model_version, e.runs,
                  a.arm_id, a.mean AS net_contribution,
                  p.mean AS paired_net_effect
           FROM experiments e
           JOIN arm_metrics a ON a.scenario_sha256 = e.scenario_sha256
             AND a.metric = 'net_contribution'
           LEFT JOIN paired_effects p ON p.scenario_sha256 = e.scenario_sha256
             AND p.arm_id = a.arm_id AND p.metric = 'net_contribution'
           ORDER BY e.scenario_id, a.arm_id"""
    ).fetchall()
    keys = ("scenario_id", "scenario_sha256", "model_version", "runs", "arm_id", "net_contribution", "paired_net_effect")
    return [dict(zip(keys, row)) for row in rows]
