"""CLI local; nenhuma subrotina envia dados a serviços externos."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tcc_frota.experiment import run_synthetic, write_report
from tcc_frota.ingestion.files import read_rows
from tcc_frota.ingestion.pipeline import build_local_medallion
from tcc_frota.quality.audit import audit_rows
from tcc_frota.synthetic.generator import export_synthetic, make_synthetic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tcc-frota")
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate-synthetic")
    generate.add_argument("--seed", type=int, default=20261014)
    generate.add_argument("--out", type=Path, default=Path("data/synthetic"))
    run = sub.add_parser("run-synthetic")
    run.add_argument("--seed", type=int, default=20261014)
    run.add_argument("--fleet-size", type=int, default=5)
    run.add_argument("--minimum-coverage", type=float, default=0.75)
    run.add_argument("--leste-train-count", type=int, default=3)
    run.add_argument("--leste-eval-count", type=int, default=3)
    run.add_argument("--initial-distribution", choices=("center", "spread"), default="center")
    run.add_argument("--max-reposition-km", type=float, default=12)
    run.add_argument("--adherence", type=float, default=1.0)
    run.add_argument("--out", type=Path, default=Path("reports/runs"))
    pipeline = sub.add_parser("build-synthetic-data")
    pipeline.add_argument("--seed", type=int, default=20261014)
    pipeline.add_argument("--out", type=Path, default=Path("reports/runs/medallion"))
    audit = sub.add_parser("audit-local")
    audit.add_argument("path", type=Path)
    audit.add_argument("--dataset-kind", choices=("synthetic", "real"), required=True)
    audit.add_argument("--required", nargs="+", required=True)
    audit.add_argument("--key")
    args = parser.parse_args(argv)
    if args.command == "generate-synthetic":
        files = export_synthetic(make_synthetic(seed=args.seed), args.out)
        print(json.dumps({"dataset_kind": "synthetic", "files": [str(file) for file in files]}))
    elif args.command == "run-synthetic":
        result = run_synthetic(
            args.seed, args.fleet_size, args.minimum_coverage,
            leste_train_count=args.leste_train_count,
            leste_eval_count=args.leste_eval_count,
            initial_distribution=args.initial_distribution,
            max_reposition_km=args.max_reposition_km,
            adherence=args.adherence,
        )
        files = write_report(result, args.out)
        print(json.dumps({"run_id": result["run_id"], "files": [str(file) for file in files], "estimated_km_reduction_percent": result["estimated_km_reduction_percent"]}))
    elif args.command == "build-synthetic-data":
        manifest = build_local_medallion(make_synthetic(seed=args.seed), args.out)
        print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    else:
        rows = read_rows(args.path, dataset_kind=args.dataset_kind)
        summary = audit_rows(rows, tuple(args.required), key=args.key)
        print(json.dumps(summary.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
