"""Escrita de lotes em Parquet (e amostra CSV) com manifesto verificável."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

RAIZ_PADRAO = Path(__file__).resolve().parents[4] / "data" / "raw" / "v1_viagens"  # raiz do repositório (src/tcc_frota/data/extraction)
VERSAO_ESQUEMA = "2"  # 2: known_at (nulo=desconhecido) e extraido_em substituem available_at/ingested_at; ES renomeia campos de tempo


def sha256_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for bloco in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def hash_json(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str, ensure_ascii=False).encode()).hexdigest()[:16]


def versao_codigo() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, timeout=10, check=False)
        sujo = subprocess.run(["git", "status", "--porcelain", "--", "src"], capture_output=True, text=True, timeout=10, check=False)
        return (out.stdout.strip() or "desconhecida") + ("+alteracoes" if sujo.stdout.strip() else "")
    except (OSError, subprocess.SubprocessError):
        return "desconhecida"


def agora_utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def caminho_lote(raiz: Path, fonte: str, entidade: str, dia: str) -> Path:
    return raiz / fonte / entidade / f"dt={dia}"


def lote_pronto(pasta: Path, assinatura: str) -> bool:
    """Idempotência: o lote vale se o manifesto existe, tem a mesma assinatura e o Parquet confere com o checksum."""
    man = pasta / "manifest.json"
    if not man.is_file():
        return False
    try:
        dados = json.loads(man.read_text(encoding="utf-8"))
        arq = pasta / dados["arquivo"]
        return dados.get("assinatura") == assinatura and arq.is_file() and sha256_arquivo(arq) == dados["sha256"]
    except (OSError, KeyError, ValueError):
        return False


def gravar_lote(
    pasta: Path,
    linhas: list[dict],
    rejeitadas: list[dict],
    *,
    meta: dict,
    colunas: dict[str, str],
    amostra_csv: int = 200,
) -> dict:
    """Grava Parquet principal, amostra CSV (UTF-8) e rejeitados à parte; devolve o manifesto do lote."""
    import pandas as pd
    import pyarrow as pa
    import pyarrow.parquet as pq

    pasta.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(linhas, columns=list(colunas))
    for col, tipo in colunas.items():
        if tipo == "timestamp":
            df[col] = pd.to_datetime(df[col], errors="coerce")
        elif tipo == "timestamp_utc":
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=True)
        elif tipo in {"int64", "float64"}:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64" if tipo == "int64" else "float64")
        elif tipo == "bool":
            df[col] = df[col].astype("boolean")
        else:
            df[col] = df[col].astype("string")
    arq = pasta / "part-000.parquet"
    pq.write_table(pa.Table.from_pandas(df, preserve_index=False), arq, compression="zstd")
    if amostra_csv and len(df):
        df.head(amostra_csv).to_csv(pasta / "amostra.csv", index=False, encoding="utf-8")
    rej = pasta / "rejeitados.parquet"
    if rejeitadas:
        pq.write_table(pa.Table.from_pandas(pd.DataFrame(rejeitadas).astype("string"), preserve_index=False), rej, compression="zstd")
    elif rej.exists():
        rej.unlink()
    man = {
        **meta,
        "arquivo": arq.name,
        "sha256": sha256_arquivo(arq),
        "linhas": int(len(df)),
        "rejeitadas": len(rejeitadas),
        "colunas": colunas,
        "esquema_versao": VERSAO_ESQUEMA,
        "codigo": versao_codigo(),
        "gerado_em_utc": agora_utc(),
    }
    (pasta / "manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    return man
