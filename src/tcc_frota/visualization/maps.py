"""Mapa H3 do recorte estudado na Grande Vitória (dados públicos: limites IBGE + vias OpenStreetMap).

O mapa é ILUSTRATIVO: mostra os municípios, as células H3 (resolução 7, zonas de planejamento do cenário sintético) que contêm os pontos de
parada do recorte e a âncora do recorte (Centro de Vitória). Não contém demanda, posições de veículos, passageiros nem dados da empresa, e
não é uma rota: nenhuma linha liga veículo e passageiro. O recorte (até 20 km POR VIA da âncora) é uma hipótese experimental, não um limite
administrativo nem a área de operação de empresa alguma, e é menor que a região metropolitana inteira.

Fontes: IBGE, API de Malhas v3 (limites municipais, WGS84/EPSG:4326, baixados em 08/11/2026, dados públicos; citar IBGE); OpenStreetMap via
Overpass (ODbL 1.0, © colaboradores do OpenStreetMap), ver ``data/geografia/manifesto_geografia.json``. Indexação: H3 (Uber), resolução 7.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import h3
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon as MplPolygon

from tcc_frota.scenarios import geography as geo

SOURCE_TEXT = "Fontes: limites municipais IBGE (API de Malhas v3, 2026); vias © colaboradores do OpenStreetMap (ODbL); grade H3 res. 7."
ATTRIBUTION = "Mapa ilustrativo do recorte experimental; sem dados da empresa, demanda ou posições individuais."


def study_cut_cells(zone_resolution: int = 7, radius_km: float = 20.0) -> tuple[Counter, geo.Pontos]:
    """Contagem de pontos de parada por célula H3 de zona no recorte operacional e os pontos do recorte."""
    points = geo.recortar_operacional(geo.construir_pontos(geo.construir_rede(), res_zona=zone_resolution, min_nos=20), radius_km)
    return Counter(points.zona.tolist()), points


def cell_polygon(cell: str) -> np.ndarray:
    """Vértices (lon, lat) do hexágono H3."""
    return np.array([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])


def plot_study_cut(out: Path | None = None, name: str = "mapa_recorte_h3", footer: bool = True) -> plt.Figure:
    """Figura estática: municípios, células H3 do recorte (cor = nº de pontos de parada) e âncora do recorte.

    ``footer=False`` omite o rodapé de fonte/atribuição (a legenda do artigo o declara).
    """
    counts, points = study_cut_cells()
    rings = geo.carregar_aneis()
    fig, ax = plt.subplots(figsize=(6.3, 5.4))
    for ring_list in rings.values():
        for r in ring_list:
            ax.add_patch(MplPolygon(r, closed=True, facecolor="#eef1f4", edgecolor="#9aa5b1", linewidth=0.6, zorder=1))
    vmax = max(counts.values())
    cmap = plt.get_cmap("Blues")
    for cell, n in counts.items():
        ax.add_patch(
            MplPolygon(
                cell_polygon(cell),
                closed=True,
                facecolor=cmap(0.25 + 0.7 * n / vmax),
                edgecolor="#1f4e79",
                linewidth=0.5,
                alpha=0.85,
                zorder=2,
            )
        )
    ax.scatter(
        [geo.ANCORA_CENTRO_VITORIA[1]],
        [geo.ANCORA_CENTRO_VITORIA[0]],
        marker="*",
        s=140,
        color="#b03a2e",
        edgecolor="white",
        zorder=4,
        label="âncora do recorte (Centro de Vitória)",
    )
    for municipality, ring_list in rings.items():
        big = max(ring_list, key=len)
        ax.text(big[:, 0].mean(), big[:, 1].mean(), municipality, fontsize=8, color="#3d4852", ha="center", zorder=3)
    lons = np.concatenate([cell_polygon(c)[:, 0] for c in counts])
    lats = np.concatenate([cell_polygon(c)[:, 1] for c in counts])
    pad = 0.04
    ax.set_xlim(lons.min() - pad, lons.max() + pad)
    ax.set_ylim(lats.min() - pad, lats.max() + pad)
    ax.set_aspect(1 / np.cos(np.deg2rad(-20.3)))
    ax.set_xlabel("longitude (°)", fontsize=8)
    ax.set_ylabel("latitude (°)", fontsize=8)
    ax.set_title(f"Recorte estudado: {len(counts)} células H3 (res. 7) com {len(points)} pontos de parada", fontsize=9, loc="left")
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, vmax))
    fig.colorbar(sm, ax=ax, shrink=0.7, label="pontos de parada por célula (res. 8)")
    ax.legend(loc="lower left", fontsize=7, frameon=True)
    ax.xaxis.set_major_locator(plt.MaxNLocator(5))
    ax.tick_params(labelsize=7)
    if footer:
        fig.text(0.01, 0.005, SOURCE_TEXT + "\n" + ATTRIBUTION, fontsize=6.2, color="#444", va="bottom")
    fig.tight_layout(rect=(0, 0.05 if footer else 0, 1, 1))
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        fig.savefig(out / f"{name}.pdf", bbox_inches="tight")
        fig.savefig(out / f"{name}.png", dpi=200, bbox_inches="tight")
    return fig


def interactive_map(out_html: Path | None = None):
    """Mapa interativo (folium) das células H3 do recorte, com tooltip do nº de pontos; exige ``folium`` e abre tiles OSM pela internet.

    Retorna o objeto folium.Map; se `out_html` for dado, grava o HTML. Não contém dados privados.
    """
    import folium  # dependência opcional (extra "notebooks")

    counts, _points = study_cut_cells()
    m = folium.Map(location=list(geo.ANCORA_CENTRO_VITORIA), zoom_start=11, tiles="OpenStreetMap", control_scale=True)
    for cell, n in counts.items():
        folium.Polygon(
            locations=[(lat, lng) for lat, lng in h3.cell_to_boundary(cell)],
            color="#1f4e79",
            weight=1,
            fill=True,
            fill_opacity=0.35,
            tooltip=f"H3 res. 7 · {n} pontos de parada",
        ).add_to(m)
    folium.Marker(list(geo.ANCORA_CENTRO_VITORIA), tooltip="âncora do recorte (Centro de Vitória)").add_to(m)
    if out_html is not None:
        out_html.parent.mkdir(parents=True, exist_ok=True)
        m.save(str(out_html))
    return m
