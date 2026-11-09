"""Matriz experimental CONGELADA (definida antes de olhar resultados do guloso). Rótulos: concentrações = hipóteses sintéticas no mapa."""

from __future__ import annotations

from tcc_frota.scenarios.generator import Cenario

PPV_BAIXA, PPV_MEDIA, PPV_ALTA = (
    4.0,
    8.0,
    14.0,
)  # pedidos por veículo por dia: frota abundante / intermediária / escassa (piloto só com a referência)

SEMENTES_PILOTO = tuple(range(1, 6))
SEMENTES_DESENVOLVIMENTO = tuple(range(101, 121))  # 20
SEMENTES_AVALIACAO = tuple(range(9001, 9041))  # 40, reservadas: só rodam com a matriz congelada


def matriz() -> list[Cenario]:
    c = []
    n = 0

    def add(id_, desc, **kw):
        nonlocal n
        n += 1
        c.append(Cenario(id_, desc, codigo=n, **kw))

    add("S1", "demanda aproximadamente uniforme entre regiões", espacial="uniforme")
    add("S2", "demanda concentrada e previsível (3 concentrações com janelas de horário)", espacial="hubs")
    add(
        "S3",
        "frota inicialmente desequilibrada (85% perto de um ponto distante das concentrações)",
        espacial="hubs",
        posicao_inicial="concentrada",
    )
    add("S4", "mudança inesperada: no dia avaliado duas concentrações trocam de lugar", espacial="hubs", desvio="hubs_trocados")
    add("S5", "demanda móvel: a região quente muda ao longo do dia (decisão única)", espacial="movel")
    for base, kw in (("S2", dict(espacial="hubs")), ("S3", dict(espacial="hubs", posicao_inicial="concentrada"))):
        add(f"{base}_frota_abundante", f"{base} com frota abundante ({PPV_BAIXA:g} pedidos/veículo)", pedidos_por_veiculo=PPV_BAIXA, **kw)
        add(f"{base}_frota_escassa", f"{base} com frota escassa ({PPV_ALTA:g} pedidos/veículo)", pedidos_por_veiculo=PPV_ALTA, **kw)
        for km in (6.0, 10.0):
            add(f"{base}_salto{km:g}km", f"{base} com salto máximo do guloso de {km:g} km (artigo: 3 km)", max_km_guloso=km, **kw)
        for rz in (6, 8):
            add(f"{base}_res{rz}", f"{base} com zonas H3 de resolução {rz} (sensibilidade à agregação)", res_zona=rz, **kw)
    for base, kw in (
        ("S2", dict(espacial="hubs")),
        ("S3", dict(espacial="hubs", posicao_inicial="concentrada")),
        ("S4", dict(espacial="hubs", desvio="hubs_trocados")),
        ("S5", dict(espacial="movel")),
    ):
        add(
            f"{base}_previsao_perfeita",
            f"DIAGNÓSTICO idealizado: {base} com a intensidade verdadeira do dia como previsão",
            previsao="perfeita",
            **kw,
        )
    add("S2_erro_previsao", "S2 com erro multiplicativo lognormal (σ = 0,5) sobre a previsão", espacial="hubs", sigma_previsao=0.5)
    return c


PRINCIPAIS = ("S1", "S2", "S3", "S4", "S5")
PPV_POR_ID = {c.id: c for c in matriz()}
SCENARIOS_BY_ID = PPV_POR_ID  # nome em inglês; PPV_POR_ID é o nome gravado nos scripts congelados
DEVELOPMENT_SEEDS = tuple(range(101, 121))
FINAL_EVALUATION_SEEDS = tuple(
    range(20001, 20041)
)  # reservadas em 08/11/2026; vistas antes da decisão de adoção (docs/CONGELAMENTO_ATRIBUICAO_60S.md)


# ---------------------------------------------------------------------------------------------------------------------------------
# Catálogo exportável (configs/scenarios/catalog.json). A semântica dos cenários NÃO muda: só rótulos de finalidade e mapeamento de nomes.
# ---------------------------------------------------------------------------------------------------------------------------------
SCENARIO_PURPOSE_NOTE = (
    "Os 22 cenários compartilham a mesma estrutura (rede, frota de 100 veículos, geração de pedidos) e variam fatores controlados; "
    "não são 22 confirmações independentes. As sementes 20001–20040 foram examinadas antes da decisão de adotar o método."
)
_PRINCIPAL_DESCRIPTION = {
    "S1": "baseline de demanda uniforme",
    "S2": "demanda concentrada e previsível",
    "S3": "frota inicialmente desequilibrada",
    "S4": "mudança inesperada de concentrações",
    "S5": "demanda móvel ao longo do dia",
}


def _group(scenario_id: str) -> str:
    if scenario_id in PRINCIPAIS:
        return "principal"
    if scenario_id.endswith("_previsao_perfeita"):
        return "diagnostico_oraculo"
    if "frota_" in scenario_id:
        return "sensibilidade_frota"
    if "_salto" in scenario_id:
        return "sensibilidade_parametro_do_guloso_antigo"
    if "_res" in scenario_id:
        return "sensibilidade_resolucao_h3"
    return "sensibilidade_previsao"


def export_catalog() -> list[dict]:
    """Uma entrada por cenário: id estável, descrição, parâmetros, sementes, tipo de dado, finalidade e locais de configuração/resultado.

    Os parâmetros ``max_km_guloso``, ``previsao`` e ``sigma_previsao`` pertencem ao planejador D+1 abandonado e NÃO afetam o despacho em
    lotes (políticas A, B, C); por isso variantes que só os alteram reproduzem estruturalmente o mesmo mundo de despacho.
    """
    out = []
    for c in matriz():
        out.append(
            {
                "id": c.id,
                "nome_legivel": _PRINCIPAL_DESCRIPTION.get(c.id, c.id.replace("_", " ")),
                "descricao": c.descricao,
                "grupo": _group(c.id),
                "parametros": {
                    "espacial": c.espacial,
                    "posicao_inicial": c.posicao_inicial,
                    "desvio": c.desvio,
                    "n_veiculos": c.n_veiculos,
                    "pedidos_por_veiculo": c.pedidos_por_veiculo,
                    "res_zona": c.res_zona,
                    "afeta_despacho_em_lotes": c.pedidos_por_veiculo != 8.0
                    or c.posicao_inicial != "uniforme"
                    or c.espacial != "uniforme"
                    or c.desvio != "nenhum"
                    or c.res_zona != 7,
                    "parametros_do_planejador_abandonado": {
                        "max_km_guloso": c.max_km_guloso,
                        "previsao": c.previsao,
                        "sigma_previsao": c.sigma_previsao,
                    },
                },
                "codigo_da_semente": c.codigo,
                "sementes": {
                    "desenvolvimento": [SEMENTES_DESENVOLVIMENTO[0], SEMENTES_DESENVOLVIMENTO[-1]],
                    "avaliacao_final_vista_antes_da_decisao": [FINAL_EVALUATION_SEEDS[0], FINAL_EVALUATION_SEEDS[-1]],
                },
                "tipo_de_dado": "sintetico (rede viaria OSM + demanda gerada)",
                "finalidade": "confirmatorio_principal" if c.id in PRINCIPAIS else "exploratorio_complementar",
                "configuracao": "configs/scenarios/catalog.json",
                "resultados_congelados": "reports/sintetico_v2/metodos_avaliacao_D/",
                "nome_antigo": c.id,  # o id gravado nos resultados congelados é o mesmo; a política A aparece como 'R0' nos Parquet
            }
        )
    return out
