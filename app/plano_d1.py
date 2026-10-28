"""Visualizador local do experimento D+1 real.

Lê apenas os resultados agregados e os detalhes por dia gerados por
`tcc-frota gold-replay --details` em reports/runs/gold_replay/ (ignorado pelo Git).
Não lê a Gold nem envia dados a serviços; o mapa de fundo opcional baixa só imagens de ruas.

    streamlit run app/plano_d1.py --server.address 127.0.0.1
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import altair as alt
import pydeck as pdk
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "reports" / "runs" / "gold_replay"
NOMES = {
    "guloso": "Guloso (DT001)",
    "proporcional": "Proporcional",
    "atribuicao_otima": "Atribuição ótima",
    "busca_local": "Busca local (SA)",
    "guloso_simulado": "Guloso simulado",
}
LOCAL = ZoneInfo("America/Sao_Paulo")
PADRAO = {"plan_hour": 7, "horizon_hours": 3, "max_reposition_km": 12.0, "min_presence_rate": 0.5, "execution_tolerance_minutes": 30.0}


@st.cache_data
def carregar_execucoes() -> list[dict[str, object]]:
    execucoes: dict[str, dict[str, object]] = {}
    for path in sorted(RUNS.glob("*/result.json"), key=lambda p: p.stat().st_mtime):
        r = json.loads(path.read_text(encoding="utf-8"))
        c = r["config"]
        algoritmo = c.get("algorithm", "guloso")
        variacao = ", ".join(f"{k}={c[k]}" for k in PADRAO if c.get(k) != PADRAO[k])
        rotulo = NOMES.get(algoritmo, algoritmo) + (" · oráculo" if c.get("oracle_fleet") else "")
        rotulo += f" · {variacao}" if variacao else ""
        # Reexecuções da mesma configuração: fica a mais recente.
        execucoes[rotulo] = {
            "rotulo": rotulo,
            "algoritmo": algoritmo,
            "oraculo": bool(c.get("oracle_fleet")),
            "variacao": variacao,
            "pasta": path.parent,
            "resultado": r,
        }
    ordem = list(NOMES)
    return sorted(execucoes.values(), key=lambda e: (e["oraculo"], bool(e["variacao"]), ordem.index(e["algoritmo"]), e["rotulo"]))


def resumo(r: dict[str, object]) -> dict[str, object]:
    dias = r["days"]
    soma = lambda cen, campo: sum(d[cen][campo] for d in dias)
    base = soma("baseline", "estimated_km_dead_total")
    prop = soma("proposed", "estimated_km_dead_total")
    pedidos = soma("baseline", "requests")
    execucao = Counter()
    for d in dias:
        execucao.update(d["plan"]["execution"])
    return {
        "KM vazio sem reposicionar": round(base, 1),
        "KM vazio preventivo": round(prop, 1),
        "Reposicionamento (km)": round(soma("proposed", "estimated_reposition_km"), 1),
        "Redução (%)": round(100 * (base - prop) / base, 2) if base else None,
        "Cobertura sem reposicionar": round(soma("baseline", "served") / pedidos, 4),
        "Cobertura preventivo": round(soma("proposed", "served") / pedidos, 4),
        "Recomendações": sum(d["plan"]["recommendations"] for d in dias),
        "Executadas": execucao.get("aplicada", 0),
        "Plano (s/dia)": round(sum(d["plan"].get("plan_seconds", 0) for d in dias) / len(dias), 2),
    }


def mapa_do_dia(com_detalhe: list[dict[str, object]]) -> None:
    col1, col2, col3 = st.columns([2, 1, 1])
    escolha = col1.selectbox("Algoritmo", [e["rotulo"] for e in com_detalhe])
    execucao = next(e for e in com_detalhe if e["rotulo"] == escolha)
    dias = sorted(p.stem for p in (execucao["pasta"] / "days").glob("*.json"))
    dia = col2.selectbox("Dia", dias, index=len(dias) - 1)
    fundo = col3.toggle("Mapa de ruas", value=True, help="Baixa imagens de mapa (Carto); nenhum dado é enviado.")
    detalhe = json.loads((execucao["pasta"] / "days" / f"{dia}.json").read_text(encoding="utf-8"))
    dados_dia = next(d for d in execucao["resultado"]["days"] if d["target_date"] == dia)

    m = st.columns(6)
    m[0].metric("Pedidos 07–10 h", dados_dia["world"]["requests"])
    m[1].metric("Frota prevista no corte", dados_dia["plan"]["predicted_fleet"])
    m[2].metric(
        "Recomendações / executadas", f"{dados_dia['plan']['recommendations']} / {dados_dia['plan']['execution'].get('aplicada', 0)}"
    )
    m[3].metric("KM vazio sem reposicionar", f"{dados_dia['baseline']['estimated_km_dead_total']:.1f}")
    m[4].metric(
        "KM vazio preventivo",
        f"{dados_dia['proposed']['estimated_km_dead_total']:.1f}",
        delta=f"{dados_dia['proposed']['estimated_km_dead_total'] - dados_dia['baseline']['estimated_km_dead_total']:+.1f} km",
        delta_color="inverse",
    )
    m[5].metric("Atendidos (sem repos. → prev.)", f"{dados_dia['baseline']['served']} → {dados_dia['proposed']['served']}")

    camadas_escolhidas = st.multiselect(
        "Camadas",
        ["Demanda prevista", "Frota prevista", "Frota real às 07:00", "Planejadas", "Executadas", "Pedidos"],
        default=["Demanda prevista", "Executadas", "Pedidos"],
    )
    camadas = []
    if "Demanda prevista" in camadas_escolhidas:
        camadas.append(
            pdk.Layer(
                "ScatterplotLayer",
                detalhe["zonas"],
                get_position="[lon, lat]",
                get_radius="200 + 250 * demanda_prevista",
                get_fill_color=[208, 140, 47, 70],
                stroked=True,
                get_line_color=[208, 140, 47, 160],
                line_width_min_pixels=1,
                pickable=True,
            )
        )
    if "Frota prevista" in camadas_escolhidas:
        camadas.append(
            pdk.Layer(
                "ScatterplotLayer",
                detalhe["frota_prevista"],
                get_position="[lon, lat]",
                get_radius=140,
                get_fill_color=[59, 110, 168, 180],
                pickable=True,
            )
        )
    if "Frota real às 07:00" in camadas_escolhidas:
        camadas.append(
            pdk.Layer(
                "ScatterplotLayer",
                detalhe["frota_real_inicio"],
                get_position="[lon, lat]",
                get_radius=110,
                get_fill_color=[90, 90, 90, 170],
                pickable=True,
            )
        )
    if "Planejadas" in camadas_escolhidas:
        camadas.append(
            pdk.Layer(
                "LineLayer",
                detalhe["planejadas"],
                get_source_position="[de.lon, de.lat]",
                get_target_position="[para.lon, para.lat]",
                get_color=[120, 120, 120, 120],
                get_width=2,
                pickable=True,
            )
        )
    if "Executadas" in camadas_escolhidas:
        camadas.append(
            pdk.Layer(
                "ArcLayer",
                detalhe["executadas"],
                get_source_position="[de.lon, de.lat]",
                get_target_position="[para.lon, para.lat]",
                get_source_color=[59, 110, 168],
                get_target_color=[34, 139, 84],
                get_width=4,
                pickable=True,
            )
        )
    if "Pedidos" in camadas_escolhidas:
        pedidos = [{**p, "cor": [34, 139, 84, 200] if p["atendido_preventivo"] else [196, 59, 59, 220]} for p in detalhe["pedidos"]]
        camadas.append(
            pdk.Layer("ScatterplotLayer", pedidos, get_position="[lon, lat]", get_radius=90, get_fill_color="cor", pickable=True)
        )
    pontos = detalhe["pedidos"] or detalhe["zonas"]
    centro = (sum(p["lat"] for p in pontos) / len(pontos), sum(p["lon"] for p in pontos) / len(pontos))
    st.pydeck_chart(
        pdk.Deck(
            layers=camadas,
            initial_view_state=pdk.ViewState(latitude=centro[0], longitude=centro[1], zoom=11, pitch=35),
            map_style=pdk.map_styles.CARTO_LIGHT if fundo else None,
            tooltip={"text": "{zona}\n{demanda_prevista}{km}{instante}"},
        ),
        width="stretch",
    )
    st.caption(
        "Laranja: demanda prevista por zona no corte (tamanho = corridas esperadas 07–10 h). "
        "Azul: frota prevista. Cinza: frota real às 07:00. Linhas cinza: plano do corte. "
        "Arcos azul→verde: reposicionamentos executados. Pontos verdes/vermelhos: pedidos atendidos/não "
        "atendidos no cenário preventivo."
    )

    por_faixa = Counter()
    for p in detalhe["pedidos"]:
        minuto = datetime.fromisoformat(p["instante"]).astimezone(LOCAL)
        faixa = minuto.replace(minute=minuto.minute // 15 * 15, second=0, microsecond=0).strftime("%H:%M")
        por_faixa[(faixa, "Atendido" if p["atendido_preventivo"] else "Não atendido")] += 1
    st.altair_chart(
        alt.Chart(alt.Data(values=[{"Faixa": f, "Situação": s, "Pedidos": n} for (f, s), n in sorted(por_faixa.items())]))
        .mark_bar()
        .encode(
            x=alt.X("Faixa:O", title="Faixa de 15 min (horário de Brasília)"),
            y="Pedidos:Q",
            color=alt.Color("Situação:N", scale=alt.Scale(range=["#228b54", "#c43b3b"])),
        ),
        width="stretch",
    )


def leitura() -> None:
    st.markdown("""
**Fluxo de um dia.** Às 20h de D, o modelo só conhece o passado: prevê a demanda por zona para 07–10 h
de D+1, prevê quais motoristas estarão presentes e onde costumam estar, e o algoritmo escolhido gera o plano.
No dia seguinte, o plano só é executado para motoristas previstos que estejam livres até 07:30; os demais
contam como não adesão. Os dois cenários (sem reposicionar e preventivo) usam exatamente os mesmos pedidos,
frota, corridas em andamento e método de distância.

**Por que o preventivo raramente ganha em linha reta.** Mover um carro até uma zona e depois atender ali
custa, em linha reta, o mesmo que atender direto (desigualdade triangular). O ganho só aparece quando o
reposicionamento corrige uma escolha míope do despacho "veículo livre mais próximo", ou quando reduz
espera e evita pedidos não atendidos. Por isso o algoritmo que avalia movimentos por simulação histórica
quase nunca recomenda mover.

**Oráculo.** Usa a frota e as posições reais das 07:00: viola o corte D+1 e serve só para separar o erro
de previsão do limite do algoritmo.
""")


st.set_page_config(page_title="Plano D+1", layout="wide")
st.title("Alocação preventiva D+1: visualização do experimento")
st.caption(
    "Distâncias Haversine estimadas sobre pedidos e frota reais (setembro/2026). "
    "Contrafactual de simulação: não é economia observada nem política da empresa."
)

execucoes = carregar_execucoes()
if not execucoes:
    st.info("Nenhum resultado encontrado. Execute `tcc-frota gold-replay --details` (ver docs/experimento_real.md).")
    st.stop()

aba_comp, aba_mapa, aba_leitura = st.tabs(["Comparação dos algoritmos", "Mapa de um dia", "Como ler"])

with aba_comp:
    st.subheader("Mesmo mês, mesmo corte, mesmo simulador")
    linhas = [{"Cenário": e["rotulo"], **resumo(e["resultado"])} for e in execucoes]
    st.dataframe(linhas, hide_index=True, width="stretch")
    padrao = [e for e in execucoes if not e["variacao"]]  # mesma janela 07–10 h: mesma referência
    barras = [
        {"Cenário": e["rotulo"], "Parcela": parcela, "km": valor}
        for e in padrao
        for parcela, valor in (
            ("Pickup", sum(d["proposed"]["estimated_pickup_km"] for d in e["resultado"]["days"])),
            ("Reposicionamento", sum(d["proposed"]["estimated_reposition_km"] for d in e["resultado"]["days"])),
        )
    ]
    referencia = sum(d["baseline"]["estimated_km_dead_total"] for d in (padrao or execucoes)[0]["resultado"]["days"])
    grafico = (
        alt.Chart(alt.Data(values=barras))
        .mark_bar()
        .encode(
            y=alt.Y("Cenário:N", sort=None, title=None),
            x=alt.X("sum(km):Q", title="KM vazio estimado no mês (preventivo)"),
            color=alt.Color("Parcela:N", scale=alt.Scale(range=["#3b6ea8", "#d08c2f"])),
            tooltip=["Cenário:N", "Parcela:N", alt.Tooltip("sum(km):Q", format=",.1f")],
        )
    )
    regra = alt.Chart(alt.Data(values=[{"km": referencia}])).mark_rule(color="#444", strokeDash=[4, 3]).encode(x="km:Q")
    st.altair_chart(grafico + regra, width="stretch")
    st.caption(f"Linha tracejada: KM vazio sem reposicionar ({referencia:,.1f} km). À direita dela, o preventivo piorou.")

    escolha = st.selectbox("Evolução diária de", [e["rotulo"] for e in execucoes])
    exec_sel = next(e for e in execucoes if e["rotulo"] == escolha)
    diario = [
        {"Dia": d["target_date"], "Cenário": nome, "km": d[cen]["estimated_km_dead_total"]}
        for d in exec_sel["resultado"]["days"]
        for cen, nome in (("baseline", "Sem reposicionar"), ("proposed", "Preventivo"))
    ]
    st.altair_chart(
        alt.Chart(alt.Data(values=diario))
        .mark_line(point=True)
        .encode(
            x=alt.X("Dia:T", title=None),
            y=alt.Y("km:Q", title="KM vazio estimado 07–10 h"),
            color=alt.Color("Cenário:N", scale=alt.Scale(range=["#d08c2f", "#3b6ea8"])),
            tooltip=["Dia:T", "Cenário:N", alt.Tooltip("km:Q", format=",.1f")],
        ),
        width="stretch",
    )

with aba_mapa:
    com_detalhe = [e for e in execucoes if (e["pasta"] / "days").is_dir()]
    if not com_detalhe:
        st.info("Execute gold-replay com `--details` para gerar os mapas diários.")
    else:
        mapa_do_dia(com_detalhe)

with aba_leitura:
    leitura()
