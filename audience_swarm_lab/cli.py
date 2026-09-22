"""Offline command-line interface."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from .contracts import validate
from .engine import simulate
from .matching import evaluate_logged_policy, rank_products
from .warehouse import ingest, report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="audience-lab")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("simulate", "rank", "evaluate"):
        command = sub.add_parser(name)
        command.add_argument("input", type=Path)
        command.add_argument("--output", type=Path)
        if name == "rank":
            command.add_argument("--segment", required=True)
    warehouse = sub.add_parser("warehouse", help="Store a simulation result and report arm-level BI metrics")
    warehouse.add_argument("result", type=Path)
    warehouse.add_argument("--db", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        raw = json.loads((args.result if args.command == "warehouse" else args.input).read_text(encoding="utf-8"))
        if args.command == "simulate":
            output = simulate(raw)
        elif args.command == "rank":
            scenario = validate(raw)
            segment = next((s for s in scenario["segments"] if s["id"] == args.segment), None)
            if segment is None:
                raise ValueError("unknown segment")
            output = {"segment": args.segment, "label": "UNCALIBRATED_MODEL_RANKING", "ranking": rank_products(segment, scenario["products"])}
        elif args.command == "evaluate":
            if not isinstance(raw, dict) or set(raw) != {"records", "target_actions"}:
                raise ValueError("evaluation input needs records and target_actions")
            output = evaluate_logged_policy(raw["records"], raw["target_actions"])
        else:
            with sqlite3.connect(args.db) as connection:
                ingest(connection, raw)
                output = {"store": str(args.db), "experiments": report(connection)}
        rendered = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
        if getattr(args, "output", None):
            args.output.write_text(rendered, encoding="utf-8")
        else:
            sys.stdout.write(rendered)
        return 0
    except (OSError, ValueError, TypeError, KeyError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
