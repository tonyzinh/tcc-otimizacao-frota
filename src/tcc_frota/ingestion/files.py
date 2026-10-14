"""Leitores locais com portão explícito para extratos reais."""
from __future__ import annotations

import csv
import os
from pathlib import Path
from typing import Iterator


def authorize(dataset_kind: str, destination: str = "local") -> None:
    if dataset_kind not in {"synthetic", "real"}:
        raise ValueError("dataset_kind deve ser synthetic ou real")
    if destination not in {"local", "external"}:
        raise ValueError("destination inválido")
    if dataset_kind == "real" and os.getenv("TCC_REAL_DATA_AUTHORIZED") != "YES":
        raise PermissionError("dados reais exigem TCC_REAL_DATA_AUTHORIZED=YES e autorização formal")
    if dataset_kind == "real" and destination == "external" and os.getenv("TCC_EXTERNAL_DATA_AUTHORIZED") != "YES":
        raise PermissionError("ambiente externo exige autorização separada")


def read_rows(path: str | Path, *, dataset_kind: str = "synthetic", destination: str = "local") -> Iterator[dict[str, object]]:
    source = Path(path)
    known_real_names = {"app_solicitacao_hist.csv", "app_estimativa_preco.csv"}
    repository_data = Path(__file__).resolve().parents[3] / "data"
    if dataset_kind == "synthetic" and (
        source.name.lower() in known_real_names or source.resolve().parent == repository_data.resolve()
    ):
        raise PermissionError("extrato local real não pode ser declarado sintético")
    authorize(dataset_kind, destination)
    if not source.is_file():
        raise FileNotFoundError(source)
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV vazio ou sem cabeçalho")
            for row in reader:
                yield dict(row)
    elif source.suffix.lower() in {".xlsx", ".xlsm"}:
        try:
            from openpyxl import load_workbook
        except ImportError as exc:
            raise RuntimeError("instale o extra excel para ler XLSX") from exc
        workbook = load_workbook(source, read_only=True, data_only=True)
        try:
            for sheet in workbook.worksheets:
                values = sheet.values
                header = next(values, None)
                if not header:
                    continue
                names = [str(item).strip() if item is not None else "" for item in header]
                if not any(names):
                    continue
                for line in values:
                    if not any(value is not None for value in line):
                        continue
                    yield {"_sheet": sheet.title, **dict(zip(names, line))}
        finally:
            workbook.close()
    else:
        raise ValueError("formato suportado: CSV ou XLSX")
