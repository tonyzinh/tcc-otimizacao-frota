"""Explorador local de artefatos derivados; não lê nem publica extratos originais."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "reports" / "runs"
sys.path.insert(0, str(ROOT / "src"))

from tcc_frota.availability.forecast import CandidateForecast
from tcc_frota.availability.recommend import ServiceNeed, rank_experimental_candidates


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
    st.table(
        [
            {
                "dataset": row["dataset"],
                "status": row["status"],
                "linhas": row.get("rows"),
                "arquivos": row.get("files"),
                "chaves_duplicadas": row.get("duplicate_key_rows"),
            }
            for row in diagnostics
        ]
    )
else:
    st.info("Execute o comando de auditoria para gerar o diagnóstico local.")

timeline = read_jsonl(RUNS / "availability_timeline.jsonl")
if timeline:
    st.subheader("Linha do tempo por veículo")
    vehicle = st.selectbox("Veículo", sorted({str(row["vehicle_id"]) for row in timeline}))
    selected = [row for row in timeline if row["vehicle_id"] == vehicle]
    st.table(
        [
            {
                "início": row["start"],
                "fim": row["end"],
                "estado": row["state"],
                "confiança": row["confidence"],
                "fontes": ", ".join(row["sources"]),
                "conflito": row["conflict"],
            }
            for row in selected
        ]
    )
else:
    st.info("Execute reconstruct com --output reports/runs/availability_timeline.jsonl para explorar os intervalos.")

forecasts = read_jsonl(RUNS / "forecast_candidates.jsonl")
if forecasts:
    st.subheader("Candidatura prevista para D+1")
    st.warning("A taxa de candidatura Online não é uma probabilidade validada de disponibilidade. Região prevista ausente.")
    vehicle = st.selectbox("Veículo previsto", sorted({str(row["vehicle_id"]) for row in forecasts}))
    st.table(
        [
            {
                "horário": row["target"],
                "taxa de candidatura": row["candidate_probability"],
                "horas positivas": row["positive_observed_hours"],
                "horas negativas": row["negative_observed_hours"],
                "confiança": row.get("confidence_level", "NAO_REGISTRADA"),
                "região proxy": row.get("region"),
                "idade posição no corte (min)": row.get("location_age_minutes"),
                "método localização": row.get("location_method"),
                "motivo": row["reason"],
            }
            for row in forecasts
            if row["vehicle_id"] == vehicle
        ]
    )
    st.subheader("Candidatos experimentais para uma solicitação")
    st.caption("Ranking de proxies históricos; não comprova disponibilidade ou posição amanhã e não autoriza despacho.")
    regions = sorted({str(row["region"]) for row in forecasts if row.get("region")})
    if regions:
        region = st.selectbox("Região de origem (grade experimental)", regions)
        times = sorted({str(row["target"]) for row in forecasts})
        target = st.selectbox("Horário da solicitação", times)
        values = [
            CandidateForecast(**{**row, "target": datetime.fromisoformat(str(row["target"]))})
            for row in forecasts
            if row["target"] == target
        ]
        ranked = rank_experimental_candidates(ServiceNeed(datetime.fromisoformat(target), region), values)
        st.write(f"{len(ranked)} candidatos com proxy suficiente nesta faixa e região.")
        st.table(
            [
                {
                    "veículo": item.vehicle_id,
                    "taxa histórica de candidatura": item.candidate_probability,
                    "idade posição no corte (min)": item.location_age_minutes,
                    "explicação": item.reason,
                }
                for item in ranked[:20]
            ]
        )
    else:
        st.info("Nenhuma região pôde ser vinculada temporalmente à frota neste corte.")
else:
    st.info("Execute forecast-candidates com --output reports/runs/forecast_candidates.jsonl para explorar o baseline D+1.")

st.caption(
    "Reposicionamentos, localização Cobli, previsão de região e recomendações finais aguardam validação dos relacionamentos e das regras operacionais."
)
