"""Explorador local de artefatos derivados; não lê nem publica extratos originais."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "reports" / "runs"


def read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    with path.open("r", encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


st.set_page_config(page_title="Disponibilidade da frota", layout="wide")
st.title("Disponibilidade operacional D+1")
st.caption("Exploração local. Online indica candidatura; a disponibilidade confirmada ainda não foi validada.")

diagnostics = read_jsonl(RUNS / "availability_diagnostic.jsonl")
if diagnostics:
    st.subheader("Diagnóstico agregado")
    st.table([{
        "dataset": row["dataset"],
        "status": row["status"],
        "linhas": row.get("rows"),
        "arquivos": row.get("files"),
        "chaves_duplicadas": row.get("duplicate_key_rows"),
    } for row in diagnostics])
else:
    st.info("Execute o comando de auditoria para gerar o diagnóstico local.")

timeline = read_jsonl(RUNS / "availability_timeline.jsonl")
if timeline:
    st.subheader("Linha do tempo por veículo")
    vehicle = st.selectbox("Veículo", sorted({str(row["vehicle_id"]) for row in timeline}))
    selected = [row for row in timeline if row["vehicle_id"] == vehicle]
    st.table([{
        "início": row["start"], "fim": row["end"], "estado": row["state"],
        "confiança": row["confidence"], "fontes": ", ".join(row["sources"]),
        "conflito": row["conflict"],
    } for row in selected])
else:
    st.info("Execute reconstruct com --output reports/runs/availability_timeline.jsonl para explorar os intervalos.")

forecasts = read_jsonl(RUNS / "forecast_candidates.jsonl")
if forecasts:
    st.subheader("Candidatura prevista para D+1")
    st.warning("A taxa de candidatura Online não é uma probabilidade validada de disponibilidade. Região prevista ausente.")
    vehicle = st.selectbox("Veículo previsto", sorted({str(row["vehicle_id"]) for row in forecasts}))
    st.table([{
        "horário": row["target"],
        "taxa de candidatura": row["candidate_probability"],
        "horas positivas": row["positive_observed_hours"],
        "horas negativas": row["negative_observed_hours"],
        "confiança": row.get("confidence_level", "NAO_REGISTRADA"),
        "motivo": row["reason"],
    } for row in forecasts if row["vehicle_id"] == vehicle])
else:
    st.info("Execute forecast-candidates com --output reports/runs/forecast_candidates.jsonl para explorar o baseline D+1.")

st.caption("Reposicionamentos, localização Cobli, previsão de região e recomendações finais aguardam validação dos relacionamentos e das regras operacionais.")
