"""Verificações estruturais da rede viária sintética (OSM). Não validam tempos reais nem confirmam ponte a ponte."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tcc_frota.scenarios import geography as geo

GEO = Path(__file__).resolve().parents[2] / "data" / "geographic"
pytestmark = pytest.mark.skipif(
    not (GEO / "osm_highways_raw.json").exists(), reason="dados geográficos públicos não baixados (scripts/download_geography.py)"
)


@pytest.fixture(scope="module")
def points():
    return geo.recortar_operacional(geo.construir_pontos(geo.construir_rede(), res_zona=7, min_nos=20), 20.0)


def test_road_distances_are_finite_when_all_cut_points_are_compared(points):
    assert np.isfinite(points.dist_km).all()


def test_road_distance_is_not_shorter_than_straight_line_when_points_are_distinct(points):
    straight = geo.haversine_km(points.lat[:, None], points.lon[:, None], points.lat[None, :], points.lon[None, :])
    assert (points.dist_km >= straight * 0.999 - 1e-6).all()


def test_island_to_mainland_ratio_is_comparable_to_within_municipality_when_bridges_are_mapped(points):
    municipality = np.array([str(m) for m in points.municipio])
    straight = geo.haversine_km(points.lat[:, None], points.lon[:, None], points.lat[None, :], points.lon[None, :])

    def median_ratio(a: str, b: str) -> float:
        ia, ib = np.where(municipality == a)[0], np.where(municipality == b)[0]
        sub, h = points.dist_km[np.ix_(ia, ib)], straight[np.ix_(ia, ib)]
        return float(np.median(sub[h > 0.5] / h[h > 0.5]))

    cross = median_ratio("Vitória", "Vila Velha")
    within = median_ratio("Vila Velha", "Vila Velha")
    assert cross < 2.0 * within  # uma travessia ausente deixaria a razão muito maior


def test_osm_snapshot_metadata_is_recorded_when_geography_manifest_is_read():
    raw = json.loads((GEO / "osm_highways_raw.json").read_text(encoding="utf-8"))
    assert "timestamp_osm_base" in raw["osm3s"] and raw["generator"].startswith("Overpass API")
