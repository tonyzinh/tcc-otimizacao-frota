"""Fase 1: recalcula a inferência da v1 com bootstrap dependente, Romano–Wolf/Holm, NB(e*), Fieller e MDE."""
from __future__ import annotations

import csv
from math import isfinite
from pathlib import Path

import numpy as np

from . import inferencia as inf
from .reamostragem import SCHEMES, indices, scheme_seed

E_STAR = (3, 5, 10, 20, 30, 50, 100)           # km de KM vazio por corrida extra aceitáveis (pré-registro §5)
PRIMARY_WINDOW, PRIMARY_REGIME = "04-11", "B"
ALPHA = 0.05


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields = list(rows[0])
    with open(path, "w", encoding="utf-8", newline="") as handle:
        w = csv.DictWriter(handle, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if isinstance(v, float) and not isfinite(v) else v) for k, v in r.items()})


def _intervals(pr: inf.Pairs, fn, boot_idx: dict[str, np.ndarray]) -> dict[str, inf.Interval]:
    point = fn(pr)
    return {s: inf.summarize(point, np.asarray(fn(pr, I))) for s, I in boot_idx.items()}


def family_pvalues(rows: list[dict], direction: str, key: str) -> dict:
    """p bruto, Holm e Romano–Wolf por variante; p de decisão = máximo entre variantes (esclarecimento E3)."""
    m = len(rows)
    per_scheme = {}
    for s in SCHEMES:
        t_obs = np.array([inf.t_stat(r[key][s], direction) for r in rows])
        tb = np.column_stack([inf.t_boot(r[key][s], direction) for r in rows])
        raw = np.array([inf.raw_p(t_obs[j], tb[:, j]) for j in range(m)])
        per_scheme[s] = (raw, inf.holm(raw), inf.romano_wolf(t_obs, tb))
    out = {name: np.max([per_scheme[s][i] for s in SCHEMES], axis=0) for i, name in enumerate(("raw", "holm", "rw"))}
    out["por_variante"] = per_scheme
    return out


def run(dias_csv: Path, tab11_csv: Path, out: Path, reps: int = 10000, echo=print) -> dict:
    pairs = inf.load_pairs(dias_csv)
    with open(tab11_csv, encoding="utf-8", newline="") as handle:
        tab11 = list(csv.DictReader(handle))
    keys = [(r["periodo"], r["janela"], r["regime"], r["cenario"]) for r in tab11]
    missing = [k for k in keys if k not in pairs]
    if missing:
        raise ValueError(f"linhas da tab11 sem dias pareados: {missing[:3]}")

    # Matrizes de reamostragem por período e variante, compartilhadas por todas as linhas do período.
    boot_idx: dict[str, dict[str, np.ndarray]] = {}
    for periodo in sorted({k[0] for k in keys}):
        dates = pairs[next(k for k in keys if k[0] == periodo)].dates
        boot_idx[periodo] = {s: indices(s, list(dates), reps, scheme_seed(periodo, s)) for s in SCHEMES}

    rows = []
    for key, v1 in zip(keys, tab11):
        pr = pairs[key]
        bi = boot_idx[key[0]]
        r = {"key": key, "v1": v1, "pr": pr,
             "km": _intervals(pr, inf.stat_km_vazio_pct, bi),
             "n_pct": _intervals(pr, inf.stat_served_pct, bi),
             "dn": _intervals(pr, inf.stat_d_served_day, bi),
             "de": _intervals(pr, inf.stat_d_empty_day, bi)}
        for e in E_STAR:
            r[f"nb{e}"] = _intervals(pr, lambda p, idx=None, e=e: inf.stat_nb(p, e, idx), bi)
        rows.append(r)
    echo(f"{len(rows)} linhas de tab11 recalculadas")

    # 1) Reprodução da v1: os pontos têm de coincidir com a tab11 publicada.
    repro = []
    for r in rows:
        v1 = r["v1"]
        repro.append({"periodo": r["key"][0], "janela": r["key"][1], "regime": r["key"][2], "cenario": r["key"][3],
                      "km_vazio_pct_v1": float(v1["km_vazio_por_corrida_var_pct"]),
                      "km_vazio_pct_recalc": r["km"]["iid"].point,
                      "atendidas_pct_v1": float(v1["corridas_atendidas_var_pct"]),
                      "atendidas_pct_recalc": r["n_pct"]["iid"].point})
    worst = max(max(abs(x["km_vazio_pct_v1"] - x["km_vazio_pct_recalc"]), abs(x["atendidas_pct_v1"] - x["atendidas_pct_recalc"]))
                for x in repro)
    write_csv(out / "fase1_reproducao_v1.csv", repro)
    echo(f"maior diferença de ponto contra a tab11: {worst:.4f} pp")

    # 2) Famílias. F1/F2: 162 linhas; F1p: subfamília primária (janela 04–11, regime B).
    prim_idx = [i for i, r in enumerate(rows) if r["key"][1] == PRIMARY_WINDOW and r["key"][2] == PRIMARY_REGIME]
    f1 = {d: family_pvalues(rows, d, "km") for d in ("reducao", "aumento")}
    f2 = family_pvalues(rows, "nao_inferior", "n_pct")
    f2s = family_pvalues(rows, "nao_inferior_sens", "n_pct")
    sub = [rows[i] for i in prim_idx]
    f1p = {d: family_pvalues(sub, d, "km") for d in ("reducao", "aumento")}
    f2p = family_pvalues(sub, "nao_inferior", "n_pct")

    primary_set = {i: pos for pos, i in enumerate(prim_idx)}
    lines, variants, comp = [], [], []
    for i, r in enumerate(rows):
        key = r["key"]
        k_name, k_iv = inf.widest(r["km"])
        n_name, n_iv = inf.widest(r["n_pct"])
        red, aum = f1["reducao"], f1["aumento"]
        p_red_rw, p_aum_rw, p_ni_rw = red["rw"][i], aum["rw"][i], f2["rw"][i]
        if i in primary_set:
            j = primary_set[i]
            pp = {"p_rw_reducao_F1p": f1p["reducao"]["rw"][j], "p_rw_aumento_F1p": f1p["aumento"]["rw"][j],
                  "p_holm_reducao_F1p": f1p["reducao"]["holm"][j], "p_rw_nao_inferior_F2p": f2p["rw"][j]}
            pr_, pa_, pn_ = pp["p_rw_reducao_F1p"], pp["p_rw_aumento_F1p"], pp["p_rw_nao_inferior_F2p"]
        else:
            pp = {"p_rw_reducao_F1p": "", "p_rw_aumento_F1p": "", "p_holm_reducao_F1p": "", "p_rw_nao_inferior_F2p": ""}
            pr_, pa_, pn_ = p_red_rw, p_aum_rw, p_ni_rw
        # Regra de decisão (§7): usa o p-RW da família em que a linha foi declarada; a não inferioridade usa o limite do IC.
        non_inf_ok = isfinite(n_iv.lo) and n_iv.lo >= inf.NON_INFERIORITY_PP
        if pr_ < ALPHA and k_iv.hi < 0 and non_inf_ok:
            decisao = "reducao"
        elif pa_ < ALPHA and k_iv.lo > 0:
            decisao = "aumento"
        else:
            decisao = "inconclusivo"
        lines.append({
            "periodo": key[0], "janela": key[1], "regime": key[2], "cenario": key[3], "dias": len(r["pr"].dates),
            "familia_declarada": "F1p" if i in primary_set else "F1",
            "km_vazio_pct": k_iv.point, "ic_decisao_inf": k_iv.lo, "ic_decisao_sup": k_iv.hi, "ic_decisao_variante": k_name,
            "p_bruto_reducao": red["raw"][i], "p_holm_reducao_F1": red["holm"][i], "p_rw_reducao_F1": p_red_rw,
            "p_bruto_aumento": aum["raw"][i], "p_holm_aumento_F1": aum["holm"][i], "p_rw_aumento_F1": p_aum_rw,
            **pp,
            "atendidas_pct": n_iv.point, "atendidas_ic_decisao_inf": n_iv.lo, "atendidas_ic_decisao_sup": n_iv.hi,
            "p_bruto_nao_inferior": f2["raw"][i], "p_rw_nao_inferior_sens2pp_F2": f2s["rw"][i], "ic_inf_ok_1pp": non_inf_ok, "ic_inf_ok_2pp": bool(isfinite(n_iv.lo) and n_iv.lo >= inf.NON_INFERIORITY_SENS_PP), "p_holm_nao_inferior_F2": f2["holm"][i], "p_rw_nao_inferior_F2": p_ni_rw,
            "decisao": decisao})
        for stat, fam in (("km_vazio_pct", "km"), ("atendidas_pct", "n_pct")):
            for s in SCHEMES:
                iv = r[fam][s]
                variants.append({"periodo": key[0], "janela": key[1], "regime": key[2], "cenario": key[3], "estatistica": stat,
                                 "variante": s, "ponto": iv.point, "ic_inf": iv.lo, "ic_sup": iv.hi, "ep": iv.se})
        v1 = r["v1"]
        iid = r["km"]["iid"]
        comp.append({
            "periodo": key[0], "janela": key[1], "regime": key[2], "cenario": key[3],
            "v1_km_vazio_pct": float(v1["km_vazio_por_corrida_var_pct"]),
            "v1_ic_percentil_inf": float(v1["km_vazio_por_corrida_var_pct_ic_inf"]),
            "v1_ic_percentil_sup": float(v1["km_vazio_por_corrida_var_pct_ic_sup"]),
            "v1_p_permutacao": float(v1["p_km_vazio_por_corrida"]),
            "v2_ic_iid_inf": iid.lo, "v2_ic_iid_sup": iid.hi,
            "v2_ic_decisao_inf": k_iv.lo, "v2_ic_decisao_sup": k_iv.hi, "v2_variante_decisao": k_name,
            "v2_p_bruto": red["raw"][i], "v2_p_holm_F1": red["holm"][i], "v2_p_rw_F1": p_red_rw,
            "decisao": decisao})
    write_csv(out / "fase1_inferencia_linhas.csv", lines)
    write_csv(out / "fase1_ic_variantes.csv", variants)
    write_csv(out / "fase1_comparacao_v1_v2.csv", comp)

    # 3) NB(e*), e pontual + Fieller, MDE e dispersão.
    nb_rows, e_rows, mde_rows, disp_rows, dow_rows = [], [], [], [], []
    for r in rows:
        key, pr = r["key"], r["pr"]
        base = {"periodo": key[0], "janela": key[1], "regime": key[2], "cenario": key[3]}
        for e in E_STAR:
            name, iv = inf.widest(r[f"nb{e}"])
            nb_rows.append({**base, "e_star_km_por_corrida": e, "nb_corridas_equiv_dia": iv.point,
                            "ic_decisao_inf": iv.lo, "ic_decisao_sup": iv.hi, "variante": name,
                            "ic_iid_inf": r[f"nb{e}"]["iid"].lo, "ic_iid_sup": r[f"nb{e}"]["iid"].hi,
                            "conclusao": "NB>0" if iv.lo > 0 else ("NB<0" if iv.hi < 0 else "inconclusivo")})
        a = pr.p["empty_km"] - pr.b["empty_km"]
        b = pr.p["served"] - pr.b["served"]
        _, dn_iv = inf.widest(r["dn"])
        excludes_zero = isfinite(dn_iv.lo) and (dn_iv.lo > 0 or dn_iv.hi < 0)
        dn_total = float(b.sum())
        fi = inf.fieller(a, b) if len(a) > 1 and np.var(b, ddof=1) > 0 else None
        e_rows.append({**base, "d_atendidas_dia": dn_iv.point, "d_atendidas_ic_decisao_inf": dn_iv.lo, "d_atendidas_ic_decisao_sup": dn_iv.hi,
                       "e_pontual": (float(a.sum() / dn_total) if excludes_zero and dn_total > 0 else ""),
                       "e_pontual_motivo": ("IC de ΔN exclui zero" if excludes_zero else "IC de ΔN contém zero: e não reportado"),
                       "e_fieller": ("ilimitado" if fi is None else f"[{fi[0]:.4g}; {fi[1]:.4g}]"),
                       "e_v1_ic_percentil_NAO_RECOMENDADO": f"[{r['v1']['km_vazio_incremental_por_corrida_extra_ic_inf']}; {r['v1']['km_vazio_incremental_por_corrida_extra_ic_sup']}]"})
        km_iid, n_iid = r["km"]["iid"], r["n_pct"]["iid"]
        mde_rows.append({**base, "dias": len(pr.dates),
                         "mde_km_vazio_pct_iid": inf.mde(km_iid.se),
                         "mde_km_vazio_pct_pior_variante": inf.mde(max(v.se for v in r["km"].values() if isfinite(v.se))),
                         "mde_atendidas_pct_iid": inf.mde(n_iid.se),
                         "mde_atendidas_pct_pior_variante": inf.mde(max(v.se for v in r["n_pct"].values() if isfinite(v.se))),
                         "efeito_observado_km_vazio_pct": km_iid.point, "efeito_observado_atendidas_pct": n_iid.point})
        disp_rows.append({**base, "dias": len(pr.dates),
                          "d_atendidas_media": float(b.mean()), "d_atendidas_dp": float(b.std(ddof=1)),
                          "d_atendidas_min": float(b.min()), "d_atendidas_max": float(b.max()),
                          "d_km_vazio_media": float(a.mean()), "d_km_vazio_dp": float(a.std(ddof=1)),
                          "d_km_vazio_min": float(a.min()), "d_km_vazio_max": float(a.max())})
        wd = np.array([d.weekday() for d in pr.dates])
        for w in range(7):
            sel = wd == w
            if sel.any():
                dow_rows.append({**base, "dia_semana": w, "dias": int(sel.sum()),
                                 "d_atendidas_media": float(b[sel].mean()), "d_km_vazio_media": float(a[sel].mean())})
    # Curva contínua de NB(e*): linear em 1/e*, então as réplicas saem de ΔN e ΔKM com os mesmos índices.
    curve = []
    for r in rows:
        key = r["key"]
        for e in np.geomspace(2, 200, 41):
            ivs = {sc: inf.summarize(r["dn"][sc].point - r["de"][sc].point / e,
                                     r["dn"][sc].boot - r["de"][sc].boot / e) for sc in SCHEMES}
            _, iv = inf.widest(ivs)
            curve.append({"periodo": key[0], "janela": key[1], "regime": key[2], "cenario": key[3], "e_star": round(float(e), 4),
                          "nb": iv.point, "ic_inf": iv.lo, "ic_sup": iv.hi})
    write_csv(out / "fase1_nb_curva.csv", curve)
    write_csv(out / "fase1_nb.csv", nb_rows)
    write_csv(out / "fase1_e_fieller.csv", e_rows)
    write_csv(out / "fase1_mde.csv", mde_rows)
    write_csv(out / "fase1_dispersao_diaria.csv", disp_rows)
    write_csv(out / "fase1_dispersao_dia_semana.csv", dow_rows)
    return {"linhas": len(rows), "maior_diferenca_v1_pp": worst,
            "decisoes": {d: sum(1 for x in lines if x["decisao"] == d) for d in ("reducao", "aumento", "inconclusivo")}}
