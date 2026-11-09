"""Simulação por dia com entradas históricas da V1 Viagens (políticas A, B e C).

Mundo comum (cenário J, condição inicial `primeira_posicao_observada`, compromissos externos com deslocamento explícito, mesmos pedidos,
frota, jornadas, parâmetros herdados da calibração de março) vem de `data.world.montar`. Tudo é SIMULAÇÃO com km estimado
(linha reta × fator rua/reta), não odômetro. Só processamento local; as saídas são Parquet agregáveis por dia.

Identificadores gravados nos resultados congelados (colunas ``config``) são mantidos para que a análise leia os Parquet antigos:
  A = ``B0_imediato_atual``, B = ``B_lote60s_guloso_fifo``, C = ``B_lote60s_hungaro``.
"""

from __future__ import annotations

import hashlib
import json
import os
import pickle
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd

from tcc_frota.assignment import dispatch as dp
from tcc_frota.data.world import montar, origens_por_motorista
from tcc_frota.domain.entities import SimParams, SimResult
from tcc_frota.simulation.engine import simulate

RAIZ = Path("data/raw/v1_viagens")
CACHE = Path("data/processed/world_cache")
PARAMS = SimParams(radius_km=4.5, speed_kmh=16.079, road_factor=1.3012, patience_s=180.0)  # herdados da calibração de março
DAY_WINDOW_S = (0.0, 86400.0)  # avaliação: dia inteiro
BATCH_S = 60.0  # janela de lote das políticas B e C
LIMITES_ESPERA_S = (300.0, 600.0, 900.0)  # limites EXPERIMENTAIS de espera (não são SLA da empresa)

POLICY_IDS = {"A": "B0_imediato_atual", "B": "B_lote60s_guloso_fifo", "C": "B_lote60s_hungaro"}
# (id gravado, janela do lote em s ou None, função de atribuição ou None para despacho imediato)
POLICY_SPECS = (
    (POLICY_IDS["A"], None, None),
    (POLICY_IDS["B"], BATCH_S, dp.POLICIES["nearest_fifo"]),
    (POLICY_IDS["C"], BATCH_S, dp.POLICIES["hungarian"]),
)


def world_source_hash() -> str:
    """Hash do código que constrói o mundo (chave do cache determinístico)."""
    h = hashlib.sha256()
    base = Path(__file__).resolve().parents[1] / "data"
    for name in ("world.py", "availability.py", "initial_position.py"):
        h.update((base / name).read_bytes())
    return h.hexdigest()[:12]


def _cached(name: str, factory):
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"{name}_{world_source_hash()}.pkl"
    if path.exists():
        return pickle.loads(path.read_bytes())
    value = factory()
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_bytes(pickle.dumps(value))
    try:
        tmp.replace(path)
    except PermissionError:  # outro processo gravou o mesmo conteúdo determinístico ao mesmo tempo
        tmp.unlink(missing_ok=True)
    return value


def build_world(day: str):
    """(pedidos, motoristas, relatório, origens, commit_origins) do dia real, cenário J.

    Args:
        day: data ISO (AAAA-MM-DD) com as entidades extraídas em `RAIZ`.
    """

    def factory():
        reqs, drivers, report, origins = montar(RAIZ, day, cenario="J")
        slim = {k: report.get(k) for k in ("motoristas_simulados", "compromissos_atribuidos", "compromissos_nao_atribuidos_por_placa")}
        return reqs, drivers, slim, origins, origens_por_motorista(drivers, origins)

    return _cached(f"mundo_{day}", factory)


def _percentile(x, q: float) -> float:
    return float(np.percentile(x, q)) if len(x) else float("nan")


def day_metrics(res: SimResult) -> dict:
    """Métricas de um dia simulado. A espera (média, mediana, P90, lista) é calculada SÓ entre os pedidos atendidos."""
    w = np.array(res.wait_s, float)
    n = max(res.n_requests, 1)
    out = {
        "pedidos": res.n_requests,
        "atendidos": res.served,
        "nao_atendidos": res.n_requests - res.served,
        "km_vazio_total": res.empty_km,
        "km_busca": res.pickup_km,
        "km_reposicionamento": res.reposition_km,
        "km_outros_deslocamentos_vazios_modelados": 0.0,
        "km_aproximacao_compromissos_fora_do_vazio": res.commit_approach_km,
        "km_vazio_por_atendimento": res.empty_km / res.served if res.served else float("nan"),
        "espera_media_s": float(w.mean()) if len(w) else float("nan"),
        "espera_mediana_s": _percentile(w, 50),
        "espera_p90_s": _percentile(w, 90),
        "esperas_s": [float(x) for x in w],  # esperas dos atendidos do dia (para P90 agregado/pooled)
        "movimentos_planejados": res.moves_planned,
        "movimentos_executados": res.moves_executed,
        "movimentos_rejeitados": res.moves_planned - res.moves_executed,
    }
    for limit in LIMITES_ESPERA_S:
        out[f"atendidos_ate_{int(limit)}s_sobre_pedidos"] = float((w <= limit).sum() / n)
    outcomes: dict[str, int] = {}
    for v in res.move_outcomes.values():
        outcomes[v] = outcomes.get(v, 0) + 1
    for k in ("executed", "absent", "limit", "busy", "early", "already_there", "not_free_in_window"):
        out[f"mov_{k}"] = outcomes.get(k, 0)
    out["comp_avaliados"] = len(res.commit_events)
    out["comp_violacao_por_politica"] = sum(1 for e in res.commit_events if e["classe"] == "insuficiente_por_politica")
    out["comp_entrada_inconsistente"] = sum(1 for e in res.commit_events if e["classe"] == "insuficiente_por_entrada")
    out["comp_incertos"] = sum(1 for e in res.commit_events if e["classe"].startswith("incerta"))
    return out


def run_day(day: str, policy_ids: list[str] | None = None) -> list[dict]:
    """Roda as políticas A, B e C (ou só as de `policy_ids`) em um dia, com as mesmas entradas.

    Args:
        day: data ISO.
        policy_ids: subconjunto de ``POLICY_IDS.values()``; ``None`` roda as três.

    Raises:
        ValueError: identificador de política desconhecido.
    """
    reqs, drivers, _slim, _orig, commit_origins = build_world(day)
    specs = list(POLICY_SPECS)
    if policy_ids:
        unknown = set(policy_ids) - {s[0] for s in specs}
        if unknown:
            raise ValueError(f"políticas desconhecidas: {sorted(unknown)}")
        specs = [s for s in specs if s[0] in policy_ids]
    rows = []
    for name, batch_s, assigner in specs:
        t0 = time.perf_counter()
        res = simulate(reqs, drivers, PARAMS, DAY_WINDOW_S, {}, commit_origins=commit_origins, batch_s=batch_s, assigner=assigner)
        rows.append(
            {
                "grupo": "B",
                "dia": day,
                "config": name,
                "semente": 0,
                "janela_lote_s": batch_s or 0.0,
                "tempo_plano_s": time.perf_counter() - t0,
                "assinatura_entrada": res.signature,
                **day_metrics(res),
            }
        )
    return rows


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, encoding="utf-8", errors="replace", check=False).stdout or ""
    except OSError:
        return ""


def build_manifest(phase: str, days: list[str], extra: dict) -> dict:
    """Manifesto de rastreabilidade de uma execução (código, dados, parâmetros e hipóteses)."""
    diff = _git("diff", "HEAD")
    manifests = {}
    for d in days:
        for ent in ("ods/solicitacao", "ods/jornada_motorista", "ods/compromissos_externos", "ods/veiculo_condutor", "es/posicao_ofertas"):
            m = RAIZ / ent / f"dt={d}" / "manifest.json"
            if m.exists():
                manifests[f"{ent}/{d}"] = hashlib.sha256(m.read_bytes()).hexdigest()[:16]
    return {
        "execucao": f"B-{phase}-{time.strftime('%Y%m%dT%H%M%S')}",
        "fase": phase,
        "grupo": "B",
        "commit": _git("rev-parse", "HEAD").strip(),
        "hash_alteracoes_nao_commitadas": hashlib.sha256(diff.encode()).hexdigest(),
        "hash_codigo_do_mundo": world_source_hash(),
        "dias": days,
        "parametros_simulador": PARAMS.__dict__,
        "janela_lote_s": BATCH_S,
        "limites_espera_experimentais_s": list(LIMITES_ESPERA_S),
        "hipoteses": {
            "disponibilidade": "cenario J (jornada realizada; nao valida previsao de disponibilidade)",
            "condicao_inicial": "primeira_posicao_observada",
            "compromissos": "deslocamento explicito ate a origem; conhecidos pelo despacho desde o inicio",
            "km": "estimado (linha reta x fator rua/reta), nao odometro",
        },
        "hashes_manifestos_dos_lotes": manifests,
        **extra,
    }


def save_day(folder: Path, day: str, rows: list[dict]) -> None:
    """Grava as linhas de um dia em ``folder/dia=<day>.parquet``."""
    folder.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(folder / f"dia={day}.parquet", index=False)


def write_manifest(folder: Path, manifest: dict) -> None:
    """Grava ``manifesto.json`` em `folder`."""
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifesto.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
