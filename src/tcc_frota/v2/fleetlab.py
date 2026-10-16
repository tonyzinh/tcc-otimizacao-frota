"""Exporta a rodada v2 para os contratos do FleetLab (`frontend/src/types/domain.ts`) e serve localmente.

Uso local apenas. Os arquivos contêm pedidos e posições de motoristas **reais pseudonimizados**
(origem/destino com 3 casas, posições com 4 casas) e ficam em `reports/runs/fleetlab/`, ignorado
pelo Git. Motoristas e pedidos recebem rótulos sequenciais (`M-001`, `P-0001`): nem o pseudônimo
nem o código interno saem do Python. O servidor escuta só em 127.0.0.1.

Os parâmetros (simulador calibrado, modelo de previsão e seleção dos algoritmos) são lidos do
`result.json` de um `final-run`; nada é recalibrado nem reescolhido aqui.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

from tcc_frota.v2 import experiment as ex
from tcc_frota.v2 import forecast as fc
from tcc_frota.v2 import rules
from tcc_frota.v2.fleet import end_of_day
from tcc_frota.v2.gold import build_gold
from tcc_frota.v2.raw import prepare_raw
from tcc_frota.v2.silver import build_silver
from tcc_frota.v2.sim import SimParams, reta_km, simulate

REGIMES = {
    "B": ("escala conhecida", "Plano no fim de D com a escala de D+1 conhecida e a última posição de D; "
          "o motorista dorme na zona-alvo e começa D+1 nela."),
    "A": ("D+1 estrito", "Plano às 20h de D com escala prevista (presença >= 50% em dias comparáveis); "
          "o motorista vai à zona-alvo na primeira disponibilidade da janela."),
    "C": ("oráculo", "Diagnóstico: posições e horários reais de D+1 (viola o corte)."),
}
OUTCOME = {"executed": "executed", "absent": "driver_absent", "busy": "driver_on_trip",
           "not_free_in_window": "driver_on_trip", "early": "driver_on_trip",
           "limit": "availability_conflict", "already_there": "availability_conflict"}
PERIOD_NAME = {"mar2026": "Março/2026", "set2026": "Setembro/2026"}


def _iso(day: date, seconds: float) -> str:
    return (datetime.combine(day, time(0), rules.TZ) + timedelta(seconds=seconds)).isoformat(timespec="seconds")


def _ll(p) -> list[float]:
    return [round(p[1], 5), round(p[0], 5)]   # contrato: [longitude, latitude]


def algorithm_specs(selection: dict) -> dict[str, tuple[str, dict]]:
    g = selection["guloso_marginal"]
    return {
        "guloso": ("guloso_marginal", {"alpha": ex.NAMED_ALPHA["intermediaria"], "rho_km": g["rho_km"], "max_km": g["max_km"]}),
        "proporcional": ("proporcional", {"max_km": selection["proporcional"]["max_km"]}),
        "regra_limiar": ("regra_limiar", dict(selection["regra_limiar"])),
    }


def algorithms_payload(selection: dict) -> list[dict]:
    specs = algorithm_specs(selection)
    g, t, p = specs["guloso"][1], specs["regra_limiar"][1], specs["proporcional"][1]
    return [
        {"id": "baseline", "name": "Sem reposicionamento", "shortName": "Baseline", "reference": "RN021",
         "description": "Despacho do motorista livre mais próximo dentro do raio calibrado, com fila e paciência.",
         "repositions": False},
        {"id": "guloso", "name": "Guloso de valor marginal (α=0,2)", "shortName": "Guloso α=0,2", "reference": "DT014",
         "description": f"A cada passo, o movimento de maior ganho esperado de corridas menos α × km; ρ={g['rho_km']} km, "
                        f"limite de {g['max_km']} km.", "repositions": True},
        {"id": "proporcional", "name": "Proporcional", "shortName": "Proporcional", "reference": "DT012",
         "description": f"Vagas por zona proporcionais à demanda prevista, preenchidas pelo par mais próximo; limite de {p['max_km']} km.",
         "repositions": True},
        {"id": "regra_limiar", "name": "Regra de limiar", "shortName": "Limiar", "reference": "DT014",
         "description": f"Cada motorista vai à zona de maior ganho por km se ganho/km >= {t['theta']}; limite de {t['max_km']} km.",
         "repositions": True},
    ]


def _metrics(alg: str, res, plan=None) -> dict:
    execution = {"executed": 0, "driver_absent": 0, "driver_on_trip": 0, "availability_conflict": 0}
    for outcome in res.move_outcomes.values():
        execution[OUTCOME[outcome]] += 1
    served = res.served
    return {
        "algorithmId": alg, "requests": res.n_requests, "served": served, "unserved": res.n_requests - served,
        "coverage": served / res.n_requests if res.n_requests else None,
        "pickupKm": res.pickup_km, "repositionKm": res.reposition_km, "returnKm": None,
        "emptyKmTotal": res.empty_km, "emptyKmPerServed": res.empty_km / served if served else None,
        "meanWaitMinutes": sum(res.wait_s) / len(res.wait_s) / 60 if res.wait_s else None,
        "plannedMoves": res.moves_planned, "executedMoves": res.moves_executed,
        "plannedRepositionKm": plan.planned_km if plan else 0.0, "execution": execution,
        "distanceMethod": "haversine_fator_rua", "dataKind": "real", "observedKm": None,
    }


class Exporter:
    def __init__(self, raw: Path, result_json: Path, out: Path, echo=print):
        self.echo = echo
        self.out = out
        self.result = json.loads(result_json.read_text(encoding="utf-8"))
        cfg = self.result["configuracao"]
        batches = prepare_raw(raw, echo=echo)
        silver = build_silver(batches, rules.load_salt())
        self.study = ex.Study(silver, build_gold(silver))
        for name, m in cfg["parametros_medidos"].items():
            self.study.trip_model[name] = (m["fator_rua_reta_viagem"], m["velocidade_viagem_kmh"])
        self.sims = {k: SimParams(**v) for k, v in cfg["simulador"].items()}
        self.selection = cfg["selecao"]
        self.model = cfg["modelo_previsao"]
        self.specs = algorithm_specs(self.selection)
        self.labels: dict[str, str] = {}
        self.provenance = {
            "kind": "real",
            "source": f"Extratos Elasticsearch (região 1) · final-run {self.result['run_id']} · simulação retrospectiva",
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "disclaimer": ("Dados reais pseudonimizados, só para uso local. Simulação retrospectiva com baseline "
                           "calibrado; KM = Haversine × fator rua/reta (estimativa, não odômetro). Não é economia "
                           "observada nem política da empresa. Trajetos desenhados são ilustrativos."),
        }

    def label(self, did: str) -> str:
        if did not in self.labels:
            self.labels[did] = f"M-{len(self.labels) + 1:03d}"
        return self.labels[did]

    def write(self, rel: str, payload) -> None:
        path = self.out / "api" / f"{rel}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    def experiment(self, period: str, regime: str) -> dict:
        sim = self.sims[period]
        g = self.specs["guloso"][1]
        name, rule = REGIMES[regime]
        return {
            "id": f"{period}-{regime}", "name": f"{PERIOD_NAME[period]} · {name} ({regime})",
            "description": f"Dias de teste da rodada v2, janela 04–11h. {rule}",
            "timezone": "America/Sao_Paulo", "region": "Grande Vitória (região 1)", "h3Resolution": 7,
            "distanceMethod": "haversine_fator_rua",
            "days": [d.isoformat() for d in ex.PERIODS[period].test],
            "parameters": {
                "cutoffHour": 20 if regime == "A" else 24, "planHour": 4, "horizonHours": 7, "lookbackDays": 56,
                "maxRepositionKm": g["max_km"], "minPresenceRate": 0.5, "executionToleranceMinutes": 0,
                "maxPickupMinutes": round(60 * sim.radius_km * sim.road_factor / sim.speed_kmh, 1),
                "speedKmh": round(sim.speed_kmh, 2), "radiusKm": sim.radius_km, "patienceSeconds": sim.patience_s,
                "roadFactor": round(sim.road_factor, 3), "executionRule": rule, "regime": regime,
            },
            "algorithms": ["baseline", "guloso", "proporcional", "regra_limiar"],
            "provenance": self.provenance,
        }

    def day(self, period: str, regime: str, target: date) -> dict:
        window = ex.WINDOWS[ex.MAIN_WINDOW]
        w = (window[0] * 3600.0, window[1] * 3600.0)
        sim = self.sims[period]
        exp_id = f"{period}-{regime}"
        reqs, drivers = self.study.world(period, target, window)
        inputs, diag = self.study.plan_inputs(target, window, regime, drivers, sim.road_factor, self.model, fc.ForecastConfig())
        origins = {d.did: p for d in drivers if (p := self.study.fleet.last_position(d.did, end_of_day(target)))}
        mode = ex.EXECUTION[regime]
        req_label = {r.rid: f"P-{i + 1:04d}" for i, r in enumerate(reqs)}
        zone_of = {r.rid: r.zone for r in reqs}
        # Snapshot (igual em todos os cenários)
        forecast = defaultdict(float)
        for (_, z), v in inputs.demand.items():
            forecast[z] += v
        observed = defaultdict(int)
        for r in reqs:
            observed[r.zone] += 1
        import h3

        zones = []
        for z in sorted(set(forecast) | set(observed)):
            if not z or (forecast[z] <= 0 and observed[z] == 0):
                continue
            lat, lon = h3.cell_to_latlng(z)
            zones.append({"h3": z, "centroid": [round(lon, 5), round(lat, 5)], "locality": f"Zona H3 {z[5:9]}",
                          "municipality": "Grande Vitória", "forecastRides": round(forecast[z], 3),
                          "observedRides": observed[z]})
        cutoff = _iso(target - timedelta(days=1), 20 * 3600) if regime == "A" else _iso(target, 0)
        fleet_start = []
        for d in drivers:
            live = [s for s in d.sessions if s[1] > w[0]]
            if not live:
                continue
            first = min(live)
            start = max(first[0], w[0])
            fleet_start.append({"vehicleId": self.label(d.did), "position": _ll(first[2:4]),
                                "zone": rules.h3_cell(first[2], first[3], 7), "basis": "observed_start",
                                "availableFrom": _iso(target, start), "availableUntil": _iso(target, max(s[1] for s in live)),
                                "state": "idle" if start <= w[0] else "unavailable"})
        predicted = [{"vehicleId": self.label(p.did), "position": _ll((p.lat, p.lon)), "zone": rules.h3_cell(p.lat, p.lon, 7),
                      "basis": "predicted", "availableFrom": _iso(target, p.start_h * 3600),
                      "availableUntil": _iso(target, p.end_h * 3600), "state": "idle"} for p in inputs.drivers]
        snapshot = {
            "experimentId": exp_id, "date": target.isoformat(), "cutoff": cutoff,
            "window": {"start": _iso(target, w[0]), "end": _iso(target, w[1])},
            "zones": zones,
            "vehicles": [{"id": self.label(d.did), "label": self.label(d.did)} for d in drivers],
            "predictedFleet": predicted, "fleetAtStart": fleet_start,
            "requests": [{"id": req_label[r.rid], "createdAt": _iso(target, r.t), "origin": _ll((r.lat, r.lon)),
                          "destination": _ll((r.dlat, r.dlon)), "originZone": r.zone} for r in reqs],
            "forecastTotal": round(sum(forecast.values()), 3), "observedTotal": len(reqs),
            "provenance": self.provenance,
        }
        # Cenários
        runs, metrics, signature = {}, {}, ""
        planned_pos = {p.did: (p.lat, p.lon) for p in inputs.drivers}
        target_zone = {v: k for k, v in inputs.zones.items()}
        for alg in ("baseline", "guloso", "proporcional", "regra_limiar"):
            trace: list = []
            plan = None
            if alg == "baseline":
                res = simulate(reqs, drivers, sim, w, trace=trace)
            else:
                algorithm, params = self.specs[alg]
                plan = ex.make_plan(algorithm, inputs, params)
                res = simulate(reqs, drivers, sim, w, plan.moves, max_move_km=params["max_km"], move_mode=mode,
                               move_origins=origins, trace=trace)
            signature = signature or res.signature
            if res.signature != signature:
                raise AssertionError("cenários com entradas diferentes (RN028)")
            movements, move_id = [], {}
            start_end: dict[str, list[float]] = defaultdict(list)
            for t, kind, did, _, _, _ in trace:
                if kind in ("reposition_start", "reposition_end"):
                    start_end[did].append(t)
            for did, to in sorted((plan.moves if plan else {}).items()):
                mid = f"{alg}-{target.isoformat()}-{self.label(did)}"
                move_id[did] = mid
                origin = planned_pos.get(did, to)
                exec_from = res.move_origins_used.get(did)
                times = start_end.get(did, [])
                movements.append({
                    "id": mid, "algorithmId": alg, "vehicleId": self.label(did),
                    "plannedFrom": _ll(origin), "executedFrom": _ll(exec_from) if exec_from else None, "to": _ll(to),
                    "fromZone": rules.h3_cell(origin[0], origin[1], 7), "toZone": target_zone.get(to, ""),
                    "plannedKm": reta_km(*origin, *to) * sim.road_factor,
                    "executedKm": reta_km(*exec_from, *to) * sim.road_factor if exec_from else None,
                    "plannedAt": cutoff, "scheduledStart": _iso(target, w[0]),
                    "outcome": OUTCOME.get(res.move_outcomes.get(did, "not_free_in_window"), "driver_on_trip"),
                    "executedStart": _iso(target, times[0]) if times else None,
                    "executedEnd": _iso(target, times[-1]) if times else None,
                    "plannedPath": [_ll(origin), _ll(to)], "executedPath": [_ll(exec_from), _ll(to)] if exec_from else None,
                    "pathKind": "illustrative",
                })
            events = []
            for i, (t, kind, did, rid, at, km) in enumerate(sorted(trace, key=lambda e: (e[0], e[1] != "request_created"))):
                events.append({"id": f"{alg}-{i}", "t": _iso(target, t), "type": kind, "algorithmId": alg,
                               "vehicleId": self.label(did) if did else None,
                               "requestId": req_label.get(rid) if rid is not None else None,
                               "movementId": move_id.get(did) if kind.startswith("reposition") else None,
                               "position": _ll(at), "km": km})
            metrics[alg] = _metrics(alg, res, plan)
            runs[alg] = {"experimentId": exp_id, "date": target.isoformat(), "algorithmId": alg, "metrics": metrics[alg],
                         "movements": movements, "events": events, "inputSignature": res.signature}
        self.write(f"experiments/{exp_id}/days/{target.isoformat()}", snapshot)
        for alg, run in runs.items():
            self.write(f"experiments/{exp_id}/days/{target.isoformat()}/scenarios/{alg}", run)
        return {"date": target.isoformat(), "forecastTotal": snapshot["forecastTotal"],
                "observedTotal": snapshot["observedTotal"], "inputSignature": signature, "metrics": metrics}

    def sensitivity(self, exp_id: str, tab13: Path | None) -> dict:
        variants, results = [], []
        if exp_id == f"{ex.SELECTION_PERIOD}-{ex.MAIN_REGIME}" and tab13 and tab13.is_file():
            import csv

            for row in csv.DictReader(tab13.open(encoding="utf-8")):
                vid = row["variacao"]
                variants.append({"id": vid, "label": vid.replace("_", " "), "parameter": None, "value": None,
                                 "isDefault": vid == "referencia"})
                be, pe = float(row["soma_base_empty_km"]), float(row["soma_prop_empty_km"])
                results.append({"variantId": vid, "algorithmId": "guloso", "baselineEmptyKm": be, "proposedEmptyKm": pe,
                                "repositionKm": float(row["soma_prop_reposition_km"]),
                                "reductionPercent": 100 * (be - pe) / be if be > 0 else None,
                                "baselineCoverage": float(row["soma_base_served"]) / float(row["soma_base_n_requests"]),
                                "proposedCoverage": float(row["soma_prop_served"]) / float(row["soma_prop_n_requests"]),
                                "executedMoves": int(float(row["soma_prop_moves_executed"])),
                                "plannedMoves": int(float(row["soma_prop_moves_planned"]))})
        return {"experimentId": exp_id, "variants": variants, "results": results, "provenance": self.provenance}

    def run(self, regimes=("B", "A", "C"), tab13: Path | None = None) -> dict:
        experiments = []
        for period in ex.PERIODS:
            for regime in regimes:
                exp = self.experiment(period, regime)
                self.echo(f"exportando {exp['id']}...")
                days = [self.day(period, regime, d) for d in ex.PERIODS[period].test]
                self.write(f"experiments/{exp['id']}/results", {"experimentId": exp["id"], "days": days,
                                                                 "provenance": self.provenance})
                self.write(f"experiments/{exp['id']}/sensitivity", self.sensitivity(exp["id"], tab13))
                experiments.append(exp)
        self.write("experiments", experiments)
        self.write("algorithms", algorithms_payload(self.selection))
        manifest = {"run_id": self.result["run_id"], "experimentos": [e["id"] for e in experiments],
                    "motoristas_rotulados": len(self.labels), "gerado_em": self.provenance["generatedAt"],
                    "aviso": "dados reais pseudonimizados; uso local; não versionar nem compartilhar"}
        (self.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest


def serve(root: Path, host: str = "127.0.0.1", port: int = 8000,
          origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173",
                                      "http://127.0.0.1:4173", "http://localhost:4173")) -> None:
    """Serve `root/api/<rota>.json` em `/api/<rota>` (somente GET, só na máquina local)."""
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    if host not in ("127.0.0.1", "localhost", "::1"):
        raise PermissionError("o servidor do FleetLab com dados reais só pode escutar na máquina local")
    api = (root / "api").resolve()

    class Handler(BaseHTTPRequestHandler):
        def _cors(self) -> None:
            origin = self.headers.get("Origin")
            if origin in origins:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self._cors()
            self.send_header("Access-Control-Allow-Methods", "GET")
            self.send_header("Access-Control-Allow-Headers", "Accept")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            from urllib.parse import unquote, urlsplit

            path = unquote(urlsplit(self.path).path)
            target = (api / (path.removeprefix("/api/").strip("/") + ".json")).resolve() if path.startswith("/api/") else None
            if target is None or api not in target.parents or not target.is_file():
                self.send_response(404)
                self._cors()
                self.end_headers()
                return
            body = target.read_bytes()
            self.send_response(200)
            self._cors()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format, *args) -> None:  # sem rotas nem dados nos logs
            return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"FleetLab (dados reais, uso local): http://{host}:{port}/api — Ctrl+C para encerrar", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
