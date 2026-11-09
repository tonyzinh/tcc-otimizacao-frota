"""Baixa a geografia PÚBLICA da Grande Vitória (ES) e grava manifesto (fonte, URL, data, licença, SHA-256). Não usa dados privados.

Fontes:
  - Limites municipais: IBGE, API de Malhas v3 (https://servicodados.ibge.gov.br/api/v3/malhas), dados públicos do IBGE (atribuição: IBGE).
  - Rede viária: OpenStreetMap via Overpass API (https://overpass-api.de), © colaboradores do OpenStreetMap, licença ODbL 1.0
    (https://www.openstreetmap.org/copyright). Atribuição obrigatória; a base derivada deve manter a licença ODbL.
Idempotente: arquivo existente é mantido (a reprodução usa o snapshot). Uso: python scripts/download_geography.py [--forcar]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import requests

PASTA = Path("data/geographic")
UA = {"User-Agent": "tcc-frota-pesquisa/1.0 (pesquisa academica; contato via repositorio)"}
MUNICIPIOS = {"3205309": "Vitória", "3205200": "Vila Velha", "3205002": "Serra", "3201308": "Cariacica"}
BBOX = (-20.50, -40.55, -20.00, -40.15)  # sul, oeste, norte, leste (caixa de consulta; o recorte real é o polígono municipal)
CLASSES = (
    "motorway|trunk|primary|secondary|tertiary|unclassified|residential|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link"
)


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--forcar", action="store_true")
    a = ap.parse_args()
    PASTA.mkdir(parents=True, exist_ok=True)
    man: dict = {"baixado_em": time.strftime("%Y-%m-%d"), "arquivos": {}}
    for cod, nome in MUNICIPIOS.items():
        p = PASTA / f"ibge_{cod}.geojson"
        url = f"https://servicodados.ibge.gov.br/api/v3/malhas/municipios/{cod}?formato=application/vnd.geo+json&qualidade=maxima"
        if a.forcar or not p.exists():
            r = requests.get(url, headers=UA, timeout=120)
            r.raise_for_status()
            p.write_bytes(r.content)
        man["arquivos"][p.name] = {
            "fonte": "IBGE, API de Malhas v3",
            "municipio": nome,
            "url": url,
            "crs": "WGS84 (EPSG:4326), lon/lat em graus",
            "licenca": "dados públicos IBGE; citar a fonte",
            "sha256": sha(p),
        }
    p = PASTA / "osm_highways_raw.json"
    consulta = f'[out:json][timeout:300];way["highway"~"^({CLASSES})$"]({BBOX[0]},{BBOX[1]},{BBOX[2]},{BBOX[3]});out geom qt;'
    if a.forcar or not p.exists():
        for servidor in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
            try:
                r = requests.post(servidor, data={"data": consulta}, headers=UA, timeout=600)
                r.raise_for_status()
                p.write_bytes(r.content)
                man["servidor_overpass"] = servidor
                break
            except requests.RequestException as e:
                print("falha", servidor, e)
        else:
            raise SystemExit("não foi possível baixar a rede viária")
    man["arquivos"][p.name] = {
        "fonte": "OpenStreetMap via Overpass API",
        "consulta": consulta,
        "crs": "WGS84 (EPSG:4326)",
        "licenca": "ODbL 1.0, © colaboradores do OpenStreetMap",
        "sha256": sha(p),
        "bytes": p.stat().st_size,
    }
    (PASTA / "manifesto_geografia.json").write_text(json.dumps(man, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v.get("bytes", None) for k, v in man["arquivos"].items()}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
