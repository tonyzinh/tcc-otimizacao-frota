"""Comandos locais de auditoria e reconstrução; saídas individuais são opt-in."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from datetime import date, datetime, time, timedelta
from pathlib import Path

from tcc_frota.availability.contracts import CONTRACTS, locate_source
from tcc_frota.availability.diagnostics import diagnose_source, timestamp
from tcc_frota.availability.evaluation import evaluate_candidate_proxy
from tcc_frota.availability.forecast import HistoricalCandidateBaseline
from tcc_frota.availability.io import iter_rows
from tcc_frota.availability.location import last_vehicle_positions
from tcc_frota.availability.relationships import relationship_coverage
from tcc_frota.availability.rides import ride_intervals
from tcc_frota.availability.statuses import status_intervals
from tcc_frota.availability.timeline import reconstruct_timeline, summarize_timeline

RIDE_COLUMNS = (
    "CD_SOLICITACAO",
    "CD_VEICULO",
    "CD_MOTORISTA",
    "DT_INICIO_REALIZADA",
    "DT_FIM_REALIZADA",
    "TX_STATUS",
)
STATUS_COLUMNS = (
    "CD_LOG_STATUS_MOTORISTA",
    "CD_MOTORISTA",
    "CD_VEICULO",
    "TX_STATUS",
    "inicio_evento",
    "fim_evento",
    "qualidade_intervalo",
    "qualidade_relacionamento",
    "placa",
)
COBLI_POSITION_COLUMNS = (
    "placa",
    "TYPE",
    "END_ADDRESS_DATETIME",
    "END_ADDRESS_LATITUDE",
    "END_ADDRESS_LONGITUDE",
)


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _instant(value: str, timezone: str) -> datetime:
    parsed = timestamp(value, timezone)
    if parsed is None:
        raise ValueError("instante vazio")
    return parsed


def _rows(paths: list[Path], columns: tuple[str, ...]):
    for path in paths:
        yield from iter_rows(path, columns)


def _sensitive_output(path: Path) -> Path:
    root = Path.cwd().resolve()
    allowed = (root / "reports" / "runs").resolve()
    if root not in allowed.parents:
        raise ValueError("reports/runs/ deve permanecer dentro do repositório")
    resolved = path.resolve()
    if resolved == allowed or allowed not in resolved.parents:
        raise ValueError("saída individual deve ficar dentro de reports/runs/ (ignorado pelo Git)")
    return resolved


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Auditoria local e disponibilidade histórica conservadora")
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument("--timezone", default="America/Sao_Paulo")
    sub = parser.add_subparsers(dest="command", required=True)
    audit = sub.add_parser("audit", help="diagnóstico agregado de todos os datasets encontrados")
    audit.add_argument("--from-date", type=_date)
    audit.add_argument("--through-date", type=_date)
    audit.add_argument("--dataset", choices=tuple(item.name for item in CONTRACTS))
    audit.add_argument("--output", type=Path, help="relatório agregado JSONL dentro de reports/runs/")
    sub.add_parser("relationships", help="cobertura agregada de chaves entre fontes")
    replay = sub.add_parser("reconstruct", help="linha do tempo histórica baseada em corridas e logs de status")
    replay.add_argument("--start", required=True)
    replay.add_argument("--end", required=True)
    replay.add_argument("--as-of", required=True, help="limite máximo de eventos conhecidos na auditoria")
    replay.add_argument("--output", type=Path, help="JSONL individual, apenas em reports/runs/")
    predict = sub.add_parser("forecast-candidates", help="baseline D+1 de candidatura Online, não de disponibilidade confirmada")
    predict.add_argument("--cutoff", required=True)
    predict.add_argument("--target-date", required=True, type=_date)
    predict.add_argument("--lookback-days", type=int, default=56)
    predict.add_argument("--min-observed-hours", type=float, default=3.0)
    predict.add_argument("--max-position-age-minutes", type=float, default=120.0)
    predict.add_argument("--output", type=Path, help="previsões individuais, apenas em reports/runs/")
    predict.add_argument("--evaluation-as-of", help="audita o alvo depois do dia; usado somente no backtest")
    args = parser.parse_args(argv)
    if args.command == "audit":
        if args.from_date and args.through_date and args.through_date < args.from_date:
            parser.error("período inválido")
        results: list[dict[str, object]] = []
        for contract in CONTRACTS:
            if args.dataset and args.dataset != contract.name:
                continue
            result = diagnose_source(
                args.data_root, contract, timezone=args.timezone, period_start=args.from_date, period_end=args.through_date
            )
            results.append(result)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        if args.output:
            destination = _sensitive_output(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as stream:
                for result in results:
                    stream.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
        return 0
    if args.command == "relationships":
        for result in relationship_coverage(args.data_root):
            print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    if args.command == "forecast-candidates":
        cutoff = _instant(args.cutoff, args.timezone)
        if args.target_date != cutoff.date() + timedelta(days=1):
            parser.error("target-date deve ser o dia local após cutoff")
        if not 1 <= args.lookback_days <= 366 or args.min_observed_hours <= 0:
            parser.error("parâmetros de histórico inválidos")
        start = cutoff - timedelta(days=args.lookback_days)
        end = as_of = cutoff
    else:
        start = _instant(args.start, args.timezone)
        end = _instant(args.end, args.timezone)
        as_of = _instant(args.as_of, args.timezone)
        if end <= start or end > as_of:
            parser.error("horizonte precisa terminar até as-of")
    rides = locate_source(args.data_root, "corridas_v1")
    if not rides:
        parser.error("corridas_v1 CSV/Parquet ausente")
    evidence, ride_audit = ride_intervals(_rows(rides, RIDE_COLUMNS), timezone=args.timezone, as_of=as_of)
    status_paths = locate_source(args.data_root, "eventos_status_motoristas")
    status_audit: dict[str, int] = {}
    status_evidence = []
    if status_paths:
        status_evidence, status_audit = status_intervals(_rows(status_paths, STATUS_COLUMNS), timezone=args.timezone, as_of=as_of)
        evidence.extend(status_evidence)
    vehicles = {item.vehicle_id for item in evidence if item.start < end and item.end > start}
    segments = reconstruct_timeline(evidence, vehicles, start, end)
    if args.command == "forecast-candidates":
        model = HistoricalCandidateBaseline(cutoff, segments)
        midnight = datetime.combine(args.target_date, time.min, tzinfo=cutoff.tzinfo)
        predictions = [
            model.predict(vehicle, midnight + timedelta(hours=hour), min_observed_hours=args.min_observed_hours)
            for vehicle in sorted(vehicles)
            for hour in range(24)
        ]
        location_audit: dict[str, int] = {}
        cobli_paths = locate_source(args.data_root, "cobli_eventos")
        if cobli_paths and status_evidence:
            positions, location_audit = last_vehicle_positions(
                _rows(cobli_paths, COBLI_POSITION_COLUMNS),
                status_evidence,
                timezone=args.timezone,
                cutoff=cutoff,
                max_age_minutes=args.max_position_age_minutes,
            )
            predictions = [
                replace(
                    item,
                    region=positions[item.vehicle_id].region,
                    location_age_minutes=positions[item.vehicle_id].age_minutes_at_cutoff,
                    location_method=positions[item.vehicle_id].method,
                )
                if item.vehicle_id in positions
                else item
                for item in predictions
            ]
        available = sum(item.candidate_probability is not None for item in predictions)
        evaluation = None
        if args.evaluation_as_of:
            evaluation_as_of = _instant(args.evaluation_as_of, args.timezone)
            next_midnight = midnight + timedelta(days=1)
            if evaluation_as_of < next_midnight:
                parser.error("evaluation-as-of precisa ocorrer após o dia alvo")
            observed_rides, _ = ride_intervals(_rows(rides, RIDE_COLUMNS), timezone=args.timezone, as_of=evaluation_as_of)
            observed_status = []
            if status_paths:
                observed_status, _ = status_intervals(_rows(status_paths, STATUS_COLUMNS), timezone=args.timezone, as_of=evaluation_as_of)
            observed = reconstruct_timeline(observed_rides + observed_status, vehicles, midnight, next_midnight)
            evaluation = evaluate_candidate_proxy(predictions, observed)
        if args.output:
            destination = _sensitive_output(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open("w", encoding="utf-8") as stream:
                for item in predictions:
                    row = asdict(item)
                    row["target"] = item.target.isoformat()
                    stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(
            json.dumps(
                {
                    "target_date": args.target_date.isoformat(),
                    "cutoff": cutoff.isoformat(),
                    "lookback_days": args.lookback_days,
                    "vehicles_with_historical_evidence": len(vehicles),
                    "vehicle_hour_slots": len(predictions),
                    "candidate_probability_estimated_slots": available,
                    "availability_probability_estimated_slots": 0,
                    "vehicle_hour_slots_with_region_proxy": sum(item.region is not None for item in predictions),
                    "candidate_slots_with_region_proxy": sum(
                        item.region is not None and item.candidate_probability is not None for item in predictions
                    ),
                    "location_audit": location_audit,
                    "ride_audit": ride_audit,
                    "status_audit": status_audit,
                    "backtest": evaluation,
                    "interpretation": "taxa histórica de candidatura Online sem ocupação identificada; não é chance validada de disponibilidade",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return 0
    result = {
        "dataset": "corridas_v1",
        "ride_audit": ride_audit,
        "status_audit": status_audit,
        "timeline": summarize_timeline(segments),
        "interpretation": "corridas e status reconstruídos; Online é apenas candidato, Offline e lacunas são DESCONHECIDO; não é previsão D+1",
        "timezone_assumed": args.timezone,
        "vehicle_universe": "somente IDs com evidência temporal no horizonte; cadastro geral não define frota elegível histórica",
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    if args.output:
        destination = _sensitive_output(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as stream:
            for segment in segments:
                row = asdict(segment)
                row["state"] = segment.state.value
                row["start"] = segment.start.isoformat()
                row["end"] = segment.end.isoformat()
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        result["individual_output_written"] = True
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
