"""Analytical adapters for locally extracted Elasticsearch documents.

Only a verified creation event can become demand. Outputs stay under the
ignored local run directory; no individual record is printed by the CLI.
"""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone as utc_timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from tcc_frota.ingestion.history import parse_time
from tcc_frota.ingestion.elasticsearch import iter_jsonl
from tcc_frota.ingestion.files import authorize


SUMMARY_COUNTS = (
    "qtdOnline", "qtdOffline", "qtdACaminho", "qtdComPassageiro",
    "qtdIndisponivel", "qtdSelecionado", "qtdAproveitamento",
)


def _parquet_writer(path: Path, schema):
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError('instale o extra "parquet" para gerar tabelas analíticas') from exc
    path.parent.mkdir(parents=True, exist_ok=True)
    return pq.ParquetWriter(path, schema)


def _append(writer, rows: list[dict[str, object]], schema) -> None:
    import pyarrow as pa

    if rows:
        writer.write_table(pa.Table.from_pylist(rows, schema=schema))


def _creation(payload: dict[str, object], creation_status: str | None, creation_field: str | None) -> datetime | None:
    if creation_status:
        events = payload.get("logStatus")
        if not isinstance(events, list):
            return None
        stamps = []
        for event in events:
            if isinstance(event, dict) and event.get("tX_STATUS") == creation_status:
                stamp = parse_time(event.get("dT_REGISTRO"))
                if stamp is not None:
                    stamps.append(stamp)
        return min(stamps, default=None)
    if creation_field:
        return parse_time(payload.get(creation_field))
    return None


def profile_request_times(run_root: Path) -> dict[str, object]:
    """Profile request/status clocks without interpreting either as creation.

    Only aggregate counts and status labels are persisted inside the ignored run.
    """
    authorize("real", "local")
    coverage = json.loads((run_root / "coverage.json").read_text(encoding="utf-8"))["coverage"]
    months = sorted(row["month"] for row in coverage
                    if row["dataset"] == "solicitacoes" and row["status"] == "ready")
    audit: Counter[str] = Counter()
    document_status: Counter[str] = Counter()
    event_status: Counter[str] = Counter()
    by_month: Counter[str] = Counter()
    for month in months:
        path = run_root / "silver" / "solicitacoes" / month / "documents.jsonl"
        for _, wrapper in iter_jsonl(path):
            audit["documents"] += 1
            by_month[month] += 1
            payload = wrapper.get("document")
            if not isinstance(payload, dict):
                audit["invalid_document"] += 1
                continue
            status = payload.get("tX_STATUS")
            document_status[str(status) if status is not None else "<missing>"] += 1
            try:
                registered = parse_time(payload.get("dT_REGISTRO"))
            except (TypeError, ValueError):
                registered = None
                audit["invalid_document_time"] += 1
            events = payload.get("logStatus")
            if not isinstance(events, list) or not events:
                audit["without_status_history"] += 1
                continue
            stamps = []
            for event in events:
                audit["status_events"] += 1
                if not isinstance(event, dict):
                    audit["invalid_status_event"] += 1
                    continue
                state = event.get("tX_STATUS")
                event_status[str(state) if state is not None else "<missing>"] += 1
                try:
                    stamp = parse_time(event.get("dT_REGISTRO"))
                except (TypeError, ValueError):
                    stamp = None
                if stamp is None:
                    audit["invalid_or_missing_event_time"] += 1
                else:
                    stamps.append(stamp)
            if registered is not None and stamps:
                earliest, latest = min(stamps), max(stamps)
                if registered == earliest:
                    audit["document_time_equals_earliest_event"] += 1
                if registered == latest:
                    audit["document_time_equals_latest_event"] += 1
                if registered < earliest:
                    audit["document_time_before_all_events"] += 1
                if registered > latest:
                    audit["document_time_after_all_events"] += 1
    result = {"run_id": run_root.name, "audit": dict(sorted(audit.items())),
              "documents_by_month": dict(sorted(by_month.items())),
              "document_status_counts": dict(sorted(document_status.items())),
              "event_status_counts": dict(sorted(event_status.items())),
              "interpretation": "descriptive_only; no timestamp is accepted as request creation"}
    (run_root / "request_time_profile.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def build_registration_proxy(run_root: Path, *, timezone: str = "America/Sao_Paulo") -> dict[str, object]:
    """Exploratory time series from document registration, never `created_at`.

    This output is deliberately outside Gold demand and cannot pass the
    historical planner's evidence gate.
    """
    authorize("real", "local")
    import pyarrow as pa

    tz = ZoneInfo(timezone)
    coverage = json.loads((run_root / "coverage.json").read_text(encoding="utf-8"))["coverage"]
    months = sorted(row["month"] for row in coverage
                    if row["dataset"] == "solicitacoes" and row["status"] == "ready")
    db = sqlite3.connect(run_root / "registration_proxy.sqlite")
    audit: Counter[str] = Counter()
    try:
        db.execute("CREATE TABLE IF NOT EXISTS registrations (request_id TEXT PRIMARY KEY, registered_at TEXT)")
        db.execute("DELETE FROM registrations")
        for month in months:
            for _, wrapper in iter_jsonl(run_root / "silver" / "solicitacoes" / month / "documents.jsonl"):
                audit["documents"] += 1
                payload = wrapper.get("document")
                if not isinstance(payload, dict):
                    audit["invalid_payload"] += 1
                    continue
                identifier = payload.get("codigo")
                if identifier is None or str(identifier).strip() == "":
                    audit["missing_request_id"] += 1
                    continue
                try:
                    registered = parse_time(payload.get("dT_REGISTRO"))
                except (TypeError, ValueError):
                    registered = None
                if registered is None:
                    audit["invalid_or_missing_registration_time"] += 1
                    continue
                key = str(identifier).strip()
                stamp = registered.astimezone(utc_timezone.utc).isoformat()
                previous = db.execute("SELECT registered_at FROM registrations WHERE request_id=?", (key,)).fetchone()
                if previous:
                    audit["repeated_request_id_documents"] += 1
                    if stamp < previous[0]:
                        db.execute("UPDATE registrations SET registered_at=? WHERE request_id=?", (stamp, key))
                else:
                    db.execute("INSERT INTO registrations VALUES (?,?)", (key, stamp))
            db.commit()
        counts: Counter[tuple[object, int]] = Counter()
        for (stamp,) in db.execute("SELECT registered_at FROM registrations"):
            local = datetime.fromisoformat(stamp).astimezone(tz)
            counts[(local.date(), local.hour)] += 1
        schema = pa.schema([
            ("date", pa.date32()), ("hour", pa.int8()), ("request_count", pa.int64()),
            ("time_basis", pa.string()), ("spatial_status", pa.string()),
        ])
        target = run_root / "exploration" / "registration_proxy_hourly.parquet"
        writer = _parquet_writer(target, schema)
        try:
            _append(writer, [{"date": day, "hour": hour, "request_count": count,
                              "time_basis": "document_registration_unverified",
                              "spatial_status": "origin_unavailable"}
                             for (day, hour), count in sorted(counts.items())], schema)
        finally:
            writer.close()
        audit["unique_requests_with_registration"] = sum(counts.values())
        result = {"run_id": run_root.name, "audit": dict(sorted(audit.items())),
                  "time_basis": "document_registration_unverified",
                  "scientific_status": "exploratory_only_not_validated_demand",
                  "spatial_status": "origin_unavailable", "timezone": timezone,
                  "path": str(target)}
        (run_root / "exploration" / "registration_proxy_coverage.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
    finally:
        db.close()


def build_analytics(run_root: Path, *, creation_status: str | None = None,
                    creation_field: str | None = None, timezone: str = "America/Sao_Paulo") -> dict[str, object]:
    """Build typed Silver and aggregate Gold from a completed local Bronze/Silver run.

    Explicit creation mapping is an experimental input, not a claim that the
    source field is creation. No mapping means demand Gold stays blocked.
    """
    if creation_status and creation_field:
        raise ValueError("escolha somente uma fonte de criação")
    if creation_field == "dT_REGISTRO":
        raise ValueError("dT_REGISTRO não comprova criação de pedido")
    authorize("real", "local")
    tz = ZoneInfo(timezone)
    previous_report = run_root / "analytics_coverage.json"
    source_label = f"status:{creation_status}" if creation_status else f"field:{creation_field}" if creation_field else None
    if previous_report.is_file():
        previous = json.loads(previous_report.read_text(encoding="utf-8"))
        if (previous.get("creation_source") not in (None, source_label)
                or previous.get("timezone") != timezone):
            raise ValueError("run analítico já construído com outro contrato; use outra saída")
    coverage = json.loads((run_root / "coverage.json").read_text(encoding="utf-8"))["coverage"]
    accepted = {(row["dataset"], row["month"]) for row in coverage if row["status"] == "ready"}
    import pyarrow as pa

    requests_schema = pa.schema([
        ("request_id", pa.string()), ("created_at", pa.timestamp("us", tz="UTC")),
        ("source_month", pa.string()), ("creation_source", pa.string()),
    ])
    summary_schema = pa.schema([
        ("snapshot_at", pa.timestamp("us", tz="UTC")), ("region", pa.int64()),
        ("source_month", pa.string()), *((name, pa.int64()) for name in SUMMARY_COUNTS),
    ])
    gold_schema = pa.schema([
        ("date", pa.date32()), ("hour", pa.int8()), ("request_count", pa.int64()),
        ("spatial_status", pa.string()),
    ])
    pressure_schema = pa.schema([
        ("date", pa.date32()), ("hour", pa.int8()), ("snapshots", pa.int64()),
        ("online_sum", pa.int64()), ("online_mean", pa.float64()),
        ("online_is_free", pa.bool_()),
    ])
    audit = Counter()
    db = sqlite3.connect(run_root / "analytics.sqlite")
    try:
        db.execute("CREATE TABLE IF NOT EXISTS requests (request_id TEXT PRIMARY KEY, created_at TEXT, source_month TEXT)")
        db.execute("CREATE TABLE IF NOT EXISTS request_ids (request_id TEXT PRIMARY KEY)")
        db.execute("DELETE FROM requests")
        db.execute("DELETE FROM request_ids")
        for month in sorted(month for dataset, month in accepted if dataset == "solicitacoes"):
            path = run_root / "silver" / "solicitacoes" / month / "documents.jsonl"
            for _, wrapper in iter_jsonl(path):
                audit["request_documents"] += 1
                payload = wrapper.get("document")
                if not isinstance(payload, dict):
                    audit["invalid_request_payload"] += 1
                    continue
                identifier = payload.get("codigo")
                if identifier is None or str(identifier).strip() == "":
                    audit["missing_request_id"] += 1
                    continue
                key = str(identifier).strip()
                cursor = db.execute("INSERT OR IGNORE INTO request_ids VALUES (?)", (key,))
                if cursor.rowcount == 0:
                    audit["repeated_request_id_documents"] += 1
                if not (creation_status or creation_field):
                    continue
                try:
                    created = _creation(payload, creation_status, creation_field)
                except (TypeError, ValueError):
                    audit["invalid_creation_time"] += 1
                    continue
                if created is None:
                    audit["missing_creation_event"] += 1
                    continue
                created_utc = created.astimezone(utc_timezone.utc).isoformat()
                previous = db.execute("SELECT created_at FROM requests WHERE request_id=?", (key,)).fetchone()
                if previous:
                    audit["duplicate_request_documents"] += 1
                    if created_utc < previous[0]:
                        db.execute("UPDATE requests SET created_at=?, source_month=? WHERE request_id=?",
                                   (created_utc, month, key))
                else:
                    db.execute("INSERT INTO requests VALUES (?,?,?)", (key, created_utc, month))
            db.commit()
        audit["distinct_request_ids"] = db.execute("SELECT COUNT(*) FROM request_ids").fetchone()[0]

        if creation_status or creation_field:
            writer = _parquet_writer(run_root / "silver" / "requests_typed.parquet", requests_schema)
            counts: Counter[tuple[object, int]] = Counter()
            try:
                batch = []
                for key, stamp, month in db.execute("SELECT request_id, created_at, source_month FROM requests ORDER BY request_id"):
                    at = datetime.fromisoformat(stamp)
                    local = at.astimezone(tz)
                    counts[(local.date(), local.hour)] += 1
                    batch.append({"request_id": key, "created_at": at, "source_month": month,
                                  "creation_source": f"status:{creation_status}" if creation_status else f"field:{creation_field}"})
                    if len(batch) >= 10000:
                        _append(writer, batch, requests_schema)
                        batch.clear()
                _append(writer, batch, requests_schema)
            finally:
                writer.close()
            writer = _parquet_writer(run_root / "gold" / "demand_hourly.parquet", gold_schema)
            try:
                _append(writer, [{"date": day, "hour": hour, "request_count": count,
                                  "spatial_status": "origin_unavailable"}
                                 for (day, hour), count in sorted(counts.items())], gold_schema)
            finally:
                writer.close()
            audit["unique_requests_with_creation"] = sum(counts.values())

        writer = _parquet_writer(run_root / "silver" / "summaries_typed.parquet", summary_schema)
        pressure: dict[tuple[object, int], list[int]] = {}
        try:
            batch = []
            for month in sorted(month for dataset, month in accepted if dataset == "sumarios"):
                path = run_root / "silver" / "sumarios" / month / "documents.jsonl"
                for _, wrapper in iter_jsonl(path):
                    audit["summary_documents"] += 1
                    payload = wrapper.get("document")
                    if not isinstance(payload, dict):
                        audit["invalid_summary"] += 1
                        continue
                    try:
                        at = parse_time(payload.get("dataHora"))
                        region = int(payload["codigoRegiao"])
                        values = {name: int(payload[name]) for name in SUMMARY_COUNTS}
                        if at is None or any(value < 0 for value in values.values()):
                            raise ValueError("invalid summary")
                    except (KeyError, TypeError, ValueError):
                        audit["invalid_summary"] += 1
                        continue
                    batch.append({"snapshot_at": at, "region": region, "source_month": month, **values})
                    local = at.astimezone(tz)
                    slot = pressure.setdefault((local.date(), local.hour), [0, 0])
                    slot[0] += 1
                    slot[1] += values["qtdOnline"]
                    audit["valid_summaries"] += 1
                    if len(batch) >= 10000:
                        _append(writer, batch, summary_schema)
                        batch.clear()
            _append(writer, batch, summary_schema)
        finally:
            writer.close()
        writer = _parquet_writer(run_root / "gold" / "online_hourly.parquet", pressure_schema)
        try:
            _append(writer, [{"date": day, "hour": hour, "snapshots": pair[0],
                              "online_sum": pair[1], "online_mean": pair[1] / pair[0],
                              "online_is_free": False}
                             for (day, hour), pair in sorted(pressure.items())], pressure_schema)
        finally:
            writer.close()

        # Oferta individual is diagnostic only. Snapshot presence is not eligibility.
        for month in sorted(month for dataset, month in accepted if dataset == "ofertas"):
            path = run_root / "silver" / "ofertas" / month / "documents.jsonl"
            for _, wrapper in iter_jsonl(path):
                audit["offer_snapshots"] += 1
                payload = wrapper.get("document")
                if not isinstance(payload, dict):
                    audit["invalid_offer_snapshot"] += 1
                    continue
                try:
                    snapshot_at = parse_time(payload.get("dataHora"))
                except (ValueError, TypeError):
                    snapshot_at = None
                offers = payload.get("ofertaList")
                if snapshot_at is None or not isinstance(offers, list):
                    audit["invalid_offer_snapshot"] += 1
                    continue
                for offer in offers:
                    audit["offer_entries"] += 1
                    if not isinstance(offer, dict):
                        audit["invalid_offer_entry"] += 1
                        continue
                    stamp = offer.get("dataPosicaoGPS") or offer.get("dataAtualizacao")
                    try:
                        at = parse_time(stamp)
                    except (TypeError, ValueError):
                        at = None
                    if at is None:
                        audit["offer_position_time_missing_or_invalid"] += 1
                    elif at > snapshot_at:
                        audit["offer_position_after_snapshot"] += 1
                    elif (snapshot_at - at).total_seconds() > 7200:
                        audit["offer_position_over_120_min"] += 1
                    try:
                        lat, lon = float(offer["latitude"]), float(offer["longitude"])
                        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
                            raise ValueError("out of bounds")
                    except (KeyError, TypeError, ValueError):
                        audit["offer_coordinates_missing"] += 1
                    audit["offer_state_unmapped"] += 1
        result = {"run_id": run_root.name, "audit": dict(sorted(audit.items())),
                  "demand_status": "built_temporal_only" if creation_status or creation_field else "blocked_creation_semantics",
                  "spatial_status": "origin_unavailable", "eligible_fleet_status": "blocked_unverified",
                  "replay_status": "blocked_unverified_inputs", "timezone": timezone,
                  "creation_source": f"status:{creation_status}" if creation_status else f"field:{creation_field}" if creation_field else None}
        (run_root / "analytics_coverage.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result
    finally:
        db.close()
