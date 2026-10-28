"""Ingestão local conservadora de exportações mensais do Elasticsearch.

Os registros e identificadores permanecem em reports/runs. O relatório público
contém apenas contagens e nomes de campos, nunca valores de documentos.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter
from collections.abc import Iterator
from pathlib import Path

from tcc_frota.ingestion.files import authorize

DATASETS = ("solicitacoes", "ofertas", "sumarios")
MONTHS = tuple(f"{year}-{month:02d}" for year, start, end in ((2025, 10, 12), (2026, 1, 9)) for month in range(start, end + 1))
COMPLETE = {"complete", "completed", "concluido", "concluida", "concluído", "concluída", "success", "succeeded", "finished"}
STATUS_KEYS = ("status", "state", "estado", "situacao", "situação")
COUNT_KEYS = ("document_count", "documents", "total_documents", "total_documentos", "total", "count")


def validate_manifest(path: Path, dataset: str, month: str) -> tuple[bool, str, int | None]:
    """Falha fechada quando não existe status explícito de conclusão."""
    if not path.is_file():
        return False, "manifest_missing", None
    try:
        manifest = json.loads(path.read_text(encoding="utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError):
        return False, "manifest_invalid_json", None
    if not isinstance(manifest, dict):
        return False, "manifest_not_object", None
    for key, expected in (("dataset", dataset), ("month", month), ("mes", month)):
        if key in manifest and manifest[key] != expected:
            return False, f"manifest_{key}_mismatch", None
    status = next((manifest[key] for key in STATUS_KEYS if key in manifest), None)
    if not isinstance(status, str) or status.strip().lower() not in COMPLETE:
        return False, "manifest_not_complete", None
    declared = next((manifest[key] for key in COUNT_KEYS if key in manifest), None)
    if declared is not None and (type(declared) is not int or declared < 0):
        return False, "manifest_invalid_count", None
    if "region" in manifest and manifest["region"] != 1:
        return False, "manifest_region_mismatch", None
    return True, "complete", declared


def discover(raw_root: Path) -> list[dict[str, object]]:
    inventory = []
    for dataset in DATASETS:
        for month in MONTHS:
            directory = raw_root / dataset / month
            data = directory / "dados.jsonl"
            valid, reason, declared = validate_manifest(directory / "manifest.json", dataset, month)
            if not directory.is_dir():
                reason = "month_missing"
            elif valid and not data.is_file():
                reason = "data_missing"
            inventory.append(
                {
                    "dataset": dataset,
                    "month": month,
                    "status": "ready" if valid and data.is_file() else reason,
                    "declared_documents": declared,
                    "data_path": data,
                }
            )
    return inventory


def iter_jsonl(path: Path) -> Iterator[tuple[int, dict[str, object]]]:
    with path.open("r", encoding="utf-8-sig") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"JSONL inválido na linha {line_number}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"documento não é objeto na linha {line_number}")
            yield line_number, item


def _payload(item: dict[str, object]) -> dict[str, object]:
    source = item.get("_source")
    if source is None:
        return item
    if not isinstance(source, dict):
        raise ValueError("_source não é objeto")
    return source


def _marker(item: dict[str, object], payload: dict[str, object]) -> str:
    # O ID do hit identifica a versão lógica; sem ele, somente conteúdo idêntico
    # pode ser colapsado com segurança, sem supor chave de negócio.
    identifier = item.get("_id")
    if identifier is not None and str(identifier).strip():
        return "id:" + str(identifier)
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _signature(inventory: list[dict[str, object]]) -> str:
    details = []
    for entry in inventory:
        if entry["status"] != "ready":
            continue
        path = entry["data_path"]
        assert isinstance(path, Path)
        stat = path.stat()
        manifest = path.parent / "manifest.json"
        details.append(
            (entry["dataset"], entry["month"], stat.st_size, stat.st_mtime_ns, hashlib.sha256(manifest.read_bytes()).hexdigest())
        )
    return hashlib.sha256(json.dumps(details).encode()).hexdigest()[:16]


def process_local(raw_root: Path, output_root: Path) -> dict[str, object]:
    """Cria um run imutável; meses novos geram novo run sem tocar no anterior."""
    authorize("real", "local")
    raw_root = raw_root.resolve()
    output_root = output_root.resolve()
    if not raw_root.is_dir():
        raise FileNotFoundError(raw_root)
    if output_root == raw_root or raw_root in output_root.parents:
        raise ValueError("saída não pode estar dentro de data/raw")
    repository = Path(__file__).resolve().parents[3]
    if repository == output_root or repository in output_root.parents:
        protected = (repository / "reports" / "runs").resolve()
        relative = output_root.relative_to(repository)
        test_directory = relative.parts[0].startswith(".pytest-tmp")
        if output_root != protected and protected not in output_root.parents and not test_directory:
            raise ValueError("artefatos reais dentro do repositório devem ficar em reports/runs")
    inventory = discover(raw_root)
    run = output_root / _signature(inventory)
    report_path = run / "coverage.json"
    if report_path.is_file():
        return json.loads(report_path.read_text(encoding="utf-8"))
    if run.exists():
        raise FileExistsError("run parcial existente; escolha outra saída após inspeção")
    run.mkdir(parents=True)
    index = sqlite3.connect(run / "dedup.sqlite")
    index.execute("CREATE TABLE seen (dataset TEXT, marker TEXT, PRIMARY KEY(dataset, marker))")
    coverage = []
    try:
        for entry in inventory:
            dataset, month, status = str(entry["dataset"]), str(entry["month"]), str(entry["status"])
            summary: dict[str, object] = {
                "dataset": dataset,
                "month": month,
                "status": status,
                "declared_documents": entry["declared_documents"],
                "read_documents": 0,
                "unique_documents": 0,
                "duplicate_documents": 0,
                "fields": {},
                "invalid": {},
            }
            coverage.append(summary)
            if status != "ready":
                continue
            path = entry["data_path"]
            assert isinstance(path, Path)
            target = run / "bronze" / dataset / month
            silver = run / "silver" / dataset / month
            target.mkdir(parents=True)
            silver.mkdir(parents=True)
            fields: Counter[str] = Counter()
            types: dict[str, Counter[str]] = {}
            invalid: Counter[str] = Counter()
            # Bronze references the immutable raw JSONL; copying multi-GB originals
            # would create another sensitive copy without adding information.
            (target / "source.json").write_text(
                json.dumps(
                    {
                        "source": str(path),
                        "bytes": path.stat().st_size,
                        "manifest_sha256": hashlib.sha256((path.parent / "manifest.json").read_bytes()).hexdigest(),
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
            with (silver / "documents.jsonl").open("w", encoding="utf-8") as silver_stream:
                for _, item in iter_jsonl(path):
                    summary["read_documents"] = int(summary["read_documents"]) + 1
                    try:
                        payload = _payload(item)
                    except ValueError:
                        invalid["invalid_source"] += 1
                        continue
                    fields.update(payload.keys())
                    for key, value in payload.items():
                        kind = (
                            "null"
                            if value is None
                            else "array"
                            if isinstance(value, list)
                            else "object"
                            if isinstance(value, dict)
                            else type(value).__name__
                        )
                        types.setdefault(key, Counter())[kind] += 1
                    marker = _marker(item, payload)
                    try:
                        index.execute("INSERT INTO seen VALUES (?, ?)", (dataset, marker))
                    except sqlite3.IntegrityError:
                        summary["duplicate_documents"] = int(summary["duplicate_documents"]) + 1
                        continue
                    silver_stream.write(json.dumps({"document": payload, "source_month": month}, ensure_ascii=False) + "\n")
                    summary["unique_documents"] = int(summary["unique_documents"]) + 1
            index.commit()
            summary["fields"] = dict(sorted(fields.items()))
            summary["field_types"] = {key: dict(sorted(counts.items())) for key, counts in sorted(types.items())}
            summary["missing_fields"] = {key: int(summary["read_documents"]) - count for key, count in sorted(fields.items())}
            summary["invalid"] = dict(invalid)
            declared = entry["declared_documents"]
            if declared is not None and declared != summary["read_documents"]:
                summary["status"] = "count_mismatch"
    finally:
        index.close()
    report = {
        "run_id": run.name,
        "coverage": coverage,
        "note": "Campos são nomes observados, sem semântica validada; Gold e simulação real exigem mapeamento confirmado.",
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
