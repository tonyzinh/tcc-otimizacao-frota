"""CLI local; nenhuma subrotina envia dados a serviços externos."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime
from pathlib import Path

from tcc_frota.experiment import run_synthetic, write_report
from tcc_frota.ingestion.files import read_rows
from tcc_frota.ingestion.pipeline import build_local_medallion
from tcc_frota.ingestion.elasticsearch import discover, process_local
from tcc_frota.ingestion.es_analytics import build_analytics, build_registration_proxy, profile_request_times
from tcc_frota.ingestion.files import authorize
from tcc_frota.demand.forecast import forecast_temporal_counts
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
    inventory = sub.add_parser("es-inventory", help="inventário local de manifestos Elasticsearch")
    inventory.add_argument("--raw-root", type=Path, default=Path("data/raw"))
    for name in ("es-audit", "es-build"):
        command = sub.add_parser(name, help="processamento local de JSONL Elasticsearch")
        command.add_argument("--raw-root", type=Path, default=Path("data/raw"))
        command.add_argument("--out", type=Path, default=Path("reports/runs/elasticsearch"))
        if name == "es-build":
            creation = command.add_mutually_exclusive_group()
            creation.add_argument("--creation-status", help="status de criação previamente validado em logStatus")
            creation.add_argument("--creation-field", help="campo de criação previamente validado; dT_REGISTRO é proibido")
            command.add_argument("--timezone", default="America/Sao_Paulo")
    forecast = sub.add_parser("es-forecast", help="previsão temporal D+1 do Gold real")
    forecast.add_argument("--run", type=Path, required=True)
    forecast.add_argument("--cutoff", type=datetime.fromisoformat, required=True)
    forecast.add_argument("--target-date", type=date.fromisoformat, required=True)
    forecast.add_argument("--slot-hours", type=int, default=1)
    forecast.add_argument("--exploratory-registration-proxy", action="store_true",
                          help="usa série exploratória de dT_REGISTRO; não é demanda validada")
    profile = sub.add_parser("es-profile-requests", help="perfil agregado de relógios e status das solicitações")
    profile.add_argument("--run", type=Path, required=True)
    explore = sub.add_parser("es-explore-demand", help="série temporal exploratória de dT_REGISTRO")
    explore.add_argument("--run", type=Path, required=True)
    explore.add_argument("--timezone", default="America/Sao_Paulo")
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
    elif args.command == "es-inventory":
        authorize("real", "local")
        items = discover(args.raw_root)
        print(json.dumps([{key: value for key, value in item.items() if key != "data_path"} for item in items], ensure_ascii=False))
    elif args.command in {"es-audit", "es-build"}:
        report = process_local(args.raw_root, args.out)
        run = args.out / report["run_id"]
        if args.command == "es-build":
            analytical = build_analytics(run, creation_status=args.creation_status,
                                         creation_field=args.creation_field, timezone=args.timezone)
            print(json.dumps(analytical, ensure_ascii=False, sort_keys=True))
        else:
            print(json.dumps({"run_id": report["run_id"], "coverage": report["coverage"]}, ensure_ascii=False))
    elif args.command == "es-forecast":
        authorize("real", "local")
        import pyarrow.parquet as pq

        path = (args.run / "exploration" / "registration_proxy_hourly.parquet"
                if args.exploratory_registration_proxy else args.run / "gold" / "demand_hourly.parquet")
        if not path.is_file():
            raise ValueError("série temporal ausente; execute es-explore-demand ou valide criação e execute es-build")
        coverage = json.loads((args.run / "coverage.json").read_text(encoding="utf-8"))["coverage"]
        months = [row["month"] for row in coverage if row["dataset"] == "solicitacoes" and row["status"] == "ready"]
        table = pq.read_table(path, columns=["date", "hour", "request_count"])
        values = zip(table["date"].to_pylist(), table["hour"].to_pylist(), table["request_count"].to_pylist())
        result = forecast_temporal_counts(values, months, args.target_date, args.cutoff, slot_hours=args.slot_hours)
        result["time_basis"] = ("document_registration_unverified" if args.exploratory_registration_proxy
                                else "verified_request_creation")
        result["scientific_status"] = ("exploratory_only_not_validated_demand"
                                       if args.exploratory_registration_proxy else "validated_creation_source_required")
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    elif args.command == "es-profile-requests":
        report = profile_request_times(args.run)
        print(json.dumps({"run_id": report["run_id"], "audit": report["audit"],
                          "report": str(args.run / "request_time_profile.json")}, ensure_ascii=False, sort_keys=True))
    elif args.command == "es-explore-demand":
        report = build_registration_proxy(args.run, timezone=args.timezone)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        rows = read_rows(args.path, dataset_kind=args.dataset_kind)
        summary = audit_rows(rows, tuple(args.required), key=args.key)
        print(json.dumps(summary.as_dict(), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
