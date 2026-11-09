"""Geografia pública da Grande Vitória (recorte: Vitória, Vila Velha, Serra e Cariacica) e rede viária para o estudo SINTÉTICO.

Fontes públicas (ver `scripts/download_geography.py` e `data/geographic/manifesto_geografia.json`): limites municipais IBGE (API de Malhas v3,
WGS84) e rede viária do OpenStreetMap (© colaboradores do OpenStreetMap, ODbL 1.0). Nada aqui lê dados privados.

O recorte é "parte da Grande Vitória", não toda a região metropolitana. Origens e destinos sintéticos são **nós da rede viária** dentro dos
municípios, na maior componente fortemente conexa (ou seja, em terra, acessíveis e alcançáveis entre si por vias); o deslocamento segue a rede
(menor caminho por distância), de modo que a baía e outros obstáculos só são cruzados por pontes e vias existentes no OSM. Limitações: classes
`residential` e acima apenas; sem restrições de conversão, semáforos, mão única parcial além do atributo `oneway`, nem congestionamento; a
velocidade é constante (hipótese experimental). Os polígonos do IBGE usam poucas casas decimais (generalizados): nós próximos à divisa podem
ser classificados no município vizinho.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import h3
import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import connected_components, dijkstra

PASTA = Path("data/geographic")
MUNICIPIOS = {"3205309": "Vitória", "3205200": "Vila Velha", "3205002": "Serra", "3201308": "Cariacica"}
RAIO_TERRA_KM = 6371.0088


def haversine_km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    h = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 2 * RAIO_TERRA_KM * np.arcsin(np.minimum(1.0, np.sqrt(h)))


def carregar_aneis(pasta: Path = PASTA) -> dict[str, list[np.ndarray]]:
    """Anéis (lon, lat) de cada município; anéis externos e furos juntos servem à regra par-ímpar de pertinência."""
    out: dict[str, list[np.ndarray]] = {}
    for cod, nome in MUNICIPIOS.items():
        gj = json.loads((pasta / f"ibge_{cod}.geojson").read_text(encoding="utf-8"))
        aneis = []
        for f in gj["features"]:
            g = f["geometry"]
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in polys:
                aneis.extend(np.asarray(r, float) for r in poly)
        out[nome] = aneis
    return out


def dentro(aneis: list[np.ndarray], lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """Pertinência (regra par-ímpar) vetorizada de pontos aos anéis de um município."""
    dentro_ = np.zeros(len(lat), bool)
    for r in aneis:
        x1, y1 = r[:-1, 0], r[:-1, 1]
        x2, y2 = r[1:, 0], r[1:, 1]
        for a, b, c, d in zip(x1, y1, x2, y2, strict=True):
            if b == d:
                continue
            cruza = ((b > lat) != (d > lat)) & (lon < (c - a) * (lat - b) / (d - b) + a)
            dentro_ ^= cruza
    return dentro_


@dataclass
class Rede:
    lat: np.ndarray  # por nó
    lon: np.ndarray
    municipio: np.ndarray  # nome do município de cada nó
    grafo: csr_matrix  # arestas dirigidas, peso = metros
    manifesto: dict


def construir_rede(pasta: Path = PASTA, usar_cache: bool = True) -> Rede:
    bruto = pasta / "osm_highways_raw.json"
    man = json.loads((pasta / "manifesto_geografia.json").read_text(encoding="utf-8"))
    chave = hashlib.sha256(bruto.read_bytes()).hexdigest()[:16]
    cache = pasta / f"rede_{chave}.npz"
    if usar_cache and cache.exists():
        z = np.load(cache, allow_pickle=False)
        from scipy.sparse import csr_matrix as csr

        g = csr((z["w"], z["ind"], z["ptr"]), shape=(len(z["lat"]),) * 2)
        info = json.loads(str(z["info"]))
        return Rede(z["lat"], z["lon"], z["mun"], g, {**man, "construcao": info})
    dados = json.loads(bruto.read_text(encoding="utf-8"))
    ids: dict[int, int] = {}
    lats: list[float] = []
    lons: list[float] = []
    arestas: list[tuple[int, int]] = []
    for w in dados["elements"]:
        if w.get("type") != "way" or "geometry" not in w:
            continue
        tags = w.get("tags", {})
        nos = w["nodes"]
        geo = w["geometry"]
        if len(nos) != len(geo) or len(nos) < 2:
            continue
        idx = []
        for n, p in zip(nos, geo, strict=True):
            if n not in ids:
                ids[n] = len(lats)
                lats.append(p["lat"])
                lons.append(p["lon"])
            idx.append(ids[n])
        ow = tags.get("oneway", "no")
        rev = ow == "-1"
        um_sentido = (
            ow in ("yes", "true", "1", "-1")
            or tags.get("junction") == "roundabout"
            or (tags.get("highway") in ("motorway", "motorway_link") and ow != "no")
        )
        for a, b in zip(idx[:-1], idx[1:], strict=True):
            if a == b:
                continue
            if um_sentido:
                arestas.append((b, a) if rev else (a, b))
            else:
                arestas.append((a, b))
                arestas.append((b, a))
    lat, lon = np.array(lats), np.array(lons)
    ea = np.array(arestas, dtype=np.int64)
    # recorte: nós dentro de algum dos quatro municípios
    aneis = carregar_aneis(pasta)
    mun = np.full(len(lat), "", dtype="U12")
    for nome, rs in aneis.items():
        m = dentro(rs, lat, lon) & (mun == "")
        mun[m] = nome
    ok = mun != ""
    keep = ok[ea[:, 0]] & ok[ea[:, 1]]
    ea = ea[keep]
    w = haversine_km(lat[ea[:, 0]], lon[ea[:, 0]], lat[ea[:, 1]], lon[ea[:, 1]]) * 1000.0
    n = len(lat)
    g = csr_matrix((w, (ea[:, 0], ea[:, 1])), shape=(n, n))
    g.sum_duplicates()
    # maior componente fortemente conexa: toda origem alcança todo destino
    _, lab = connected_components(g, directed=True, connection="strong")
    cont = np.bincount(lab[np.unique(ea)])
    maior = int(np.argmax(cont))
    sel = np.where(lab == maior)[0]
    remap = -np.ones(n, np.int64)
    remap[sel] = np.arange(len(sel))
    mask = (remap[ea[:, 0]] >= 0) & (remap[ea[:, 1]] >= 0)
    ea2 = remap[ea[mask]]
    g2 = csr_matrix((w[mask], (ea2[:, 0], ea2[:, 1])), shape=(len(sel), len(sel)))
    g2.sum_duplicates()
    info = {
        "nos_osm_lidos": int(n),
        "nos_dentro_dos_municipios": int(ok.sum()),
        "nos_na_maior_componente_forte": int(len(sel)),
        "arestas": int(g2.nnz),
        "km_de_via": float(g2.sum() / 1000.0),
        "por_municipio": {k: int((mun[sel] == k).sum()) for k in aneis},
    }
    r = Rede(lat[sel], lon[sel], mun[sel], g2, {**man, "construcao": info})
    np.savez_compressed(cache, w=g2.data, ind=g2.indices, ptr=g2.indptr, lat=r.lat, lon=r.lon, mun=r.municipio, info=json.dumps(info))
    return r


@dataclass
class Pontos:
    """Pontos de parada acessíveis: um nó representativo por célula H3 (res. `res_ponto`) com vias suficientes."""

    lat: np.ndarray
    lon: np.ndarray
    no: np.ndarray  # índice do nó na rede
    celula: np.ndarray  # id H3 do ponto (res_ponto)
    zona: np.ndarray  # id H3 da zona de planejamento (res_zona)
    municipio: np.ndarray
    dist_km: np.ndarray  # matriz N x N, menor caminho pela rede (km)
    manifesto: dict

    def __len__(self) -> int:
        return len(self.lat)


def construir_pontos(
    rede: Rede, res_ponto: int = 8, res_zona: int = 7, min_nos: int = 6, max_dist_centro_m: float = 350.0, usar_cache: bool = True
) -> Pontos:
    chave = hashlib.sha256(
        json.dumps(
            [rede.manifesto["arquivos"]["osm_highways_raw.json"]["sha256"], res_ponto, res_zona, min_nos, max_dist_centro_m]
        ).encode()
    ).hexdigest()[:16]
    cache = PASTA / f"pontos_{chave}.npz"
    if usar_cache and cache.exists():
        z = np.load(cache, allow_pickle=False)
        return Pontos(
            z["lat"], z["lon"], z["no"], z["cel"], z["zona"], z["mun"], z["dist"], {"cache": str(cache), **json.loads(str(z["info"]))}
        )
    celulas = np.array([h3.latlng_to_cell(a, b, res_ponto) for a, b in zip(rede.lat, rede.lon, strict=True)])
    reps: list[int] = []
    descartadas = {"poucos_nos": 0, "centro_longe_de_via": 0}
    ordem = np.argsort(celulas, kind="stable")
    inicio = 0
    while inicio < len(ordem):
        fim = inicio
        c = celulas[ordem[inicio]]
        while fim < len(ordem) and celulas[ordem[fim]] == c:
            fim += 1
        nos = ordem[inicio:fim]
        inicio = fim
        if len(nos) < min_nos:
            descartadas["poucos_nos"] += 1
            continue
        clat, clon = h3.cell_to_latlng(str(c))
        d = haversine_km(clat, clon, rede.lat[nos], rede.lon[nos]) * 1000.0
        k = int(np.argmin(d))
        if d[k] > max_dist_centro_m:
            descartadas["centro_longe_de_via"] += 1
            continue
        reps.append(int(nos[k]))
    reps_a = np.array(sorted(reps))
    d = np.empty((len(reps_a), len(reps_a)))
    for i in range(0, len(reps_a), 100):
        bloco = dijkstra(rede.grafo, directed=True, indices=reps_a[i : i + 100])
        d[i : i + 100] = bloco[:, reps_a] / 1000.0
    if not np.isfinite(d).all():
        raise RuntimeError("pontos inalcançáveis entre si na rede (não deveria ocorrer na maior componente forte)")
    cel = celulas[reps_a]
    zona = np.array([h3.cell_to_parent(str(c), res_zona) for c in cel])
    info = {
        "res_ponto": res_ponto,
        "res_zona": res_zona,
        "min_nos": min_nos,
        "max_dist_centro_m": max_dist_centro_m,
        "pontos": int(len(reps_a)),
        "zonas": int(len(set(zona))),
        "descartadas": descartadas,
    }
    p = Pontos(rede.lat[reps_a], rede.lon[reps_a], reps_a, cel, zona, rede.municipio[reps_a], d, info)
    np.savez_compressed(cache, lat=p.lat, lon=p.lon, no=p.no, cel=cel, zona=zona, mun=p.municipio, dist=d, info=json.dumps(info))
    return p


ANCORA_CENTRO_VITORIA = (-20.3155, -40.3128)  # referência geográfica pública (Centro de Vitória); só define o recorte operacional


def recortar_operacional(p: Pontos, raio_km: float, ancora: tuple[float, float] = ANCORA_CENTRO_VITORIA) -> Pontos:
    """Área operacional = pontos a até `raio_km` POR VIA do ponto mais próximo da âncora (ida e volta pela rede, o maior dos dois sentidos).

    É um recorte manejável de hipótese experimental (não é limite administrativo nem área de operação de empresa alguma). As distâncias
    entre os pontos mantidos continuam sendo as da rede completa (o caminho pode sair do recorte).
    """
    a = int(np.argmin(haversine_km(ancora[0], ancora[1], p.lat, p.lon)))
    manter = np.where(np.maximum(p.dist_km[a], p.dist_km[:, a]) <= raio_km)[0]
    info = {
        **p.manifesto,
        "recorte_operacional": {
            "ancora": list(ancora),
            "raio_km_por_via": raio_km,
            "pontos_mantidos": int(len(manter)),
            "pontos_antes": int(len(p)),
        },
    }
    zonas = p.zona[manter]
    info["zonas"] = int(len(set(zonas)))
    return Pontos(
        p.lat[manter], p.lon[manter], p.no[manter], p.celula[manter], zonas, p.municipio[manter], p.dist_km[np.ix_(manter, manter)], info
    )
