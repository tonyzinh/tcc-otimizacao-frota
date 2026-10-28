"""Impressão digital do repositório (antes/depois de uma reorganização): Git, hashes dos artefatos científicos,
importação de todos os módulos, compilação, métricas determinísticas de um experimento sintético e resumo do pytest.

Uso: python scripts/validar_baseline.py --out reports/repository_migration/baseline_antes.json
Não lê dados reais nem imprime registros individuais.
"""

import argparse
import compileall
import hashlib
import importlib
import json
import pkgutil
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
CIENTIFICOS = ("reports/tcc_final", "reports/tcc_v2", "resultados", "tabelas", "config", "databricks")
OPCIONAIS = {
    "pyarrow",
    "h3",
    "streamlit",
    "pyspark",
    "numpy",
    "matplotlib",
    "sklearn",
    "arch",
    "statsmodels",
    "scipy",
    "pandas",
    "yaml",
    "tzdata",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout.strip()


def hashes_v1() -> dict:
    texto = (ROOT / "docs/V2_PREREGISTRO.md").read_text(encoding="utf-8")
    linhas = re.findall(r"^\| (\S+\.(?:csv|json)) \| ([0-9a-f]{64}) \|", texto, re.M)
    ok = [n for n, h in linhas if sha(ROOT / "reports/tcc_final" / n) == h]
    return {"arquivos": len(linhas), "iguais": len(ok), "divergentes": [n for n, _ in linhas if n not in ok]}


def artefatos() -> dict:
    out = {}
    for base in CIENTIFICOS:
        arquivos = [Path(p) for p in git("ls-files", base).splitlines() if p]
        out[base] = {
            "arquivos": len(arquivos),
            "digest": hashlib.sha256("".join(sorted(sha(ROOT / p) for p in arquivos)).encode()).hexdigest(),
        }
    return out


def importacoes() -> dict:
    import tcc_frota

    ok, falhas, ignorados = 0, {}, {}
    for m in pkgutil.walk_packages(tcc_frota.__path__, "tcc_frota."):
        try:
            importlib.import_module(m.name)
            ok += 1
        except ImportError as e:
            faltando = (getattr(e, "name", "") or "").split(".")[0]
            (ignorados if faltando in OPCIONAIS else falhas)[m.name] = str(e)[:120]
    return {"importados": ok, "dependencia_opcional_ausente": ignorados, "falhas": falhas}


def metricas_sinteticas() -> dict:
    from tcc_frota.algoritmos.base import PlannerSpec
    from tcc_frota.v3 import controle as c

    specs = [PlannerSpec("proporcional", "proporcional", {"max_km": 3.0})]
    out = {}
    for cen in c.SCENARIOS:
        for r in c.run_day(0, cen, specs, mode="fixa", forecast="verdadeira"):
            out[f"{cen}|{r['cenario']}"] = {
                k: round(float(r[k]), 9) for k in ("n_requests", "served", "pickup_km", "reposition_km", "empty_km")
            }
    return out


def decisao_real() -> dict:
    from tcc_frota.v3 import decisao as dc

    plano, base = dc.dias_de_csv(
        ROOT / "reports/tcc_v2/fase4_dias.csv", periodo="set2026", cenario="proporcional", grupo="origem|B0|rho1|c1", par="origem|B0|rho1"
    )
    d = dc.decidir(30, plano, base, reps=2000, rotulo="set2026")
    return {"nb": round(d.nb, 9), "ic_inf": round(d.ic_inf, 6), "ic_sup": round(d.ic_sup, 6), "decisao": d.decisao}


def pytest_resumo() -> str:
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    linhas = [ln for ln in (r.stdout or "").splitlines() if re.search(r"\d+ (passed|failed|error)", ln)]
    return linhas[-1].strip() if linhas else f"sem resumo (código {r.returncode})"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--sem-pytest", action="store_true")
    a = ap.parse_args()
    res = {
        "git": {
            "commit": git("rev-parse", "HEAD"),
            "ramo": git("branch", "--show-current"),
            "alteracoes_nao_commitadas": git("status", "--short").splitlines(),
        },
        "hashes_v1": hashes_v1(),
        "artefatos_versionados": artefatos(),
        "importacoes": importacoes(),
        "compilacao_ok": bool(compileall.compile_dir(ROOT / "src", quiet=2, force=True)),
        "metricas_sinteticas_dia0": metricas_sinteticas(),
        "decisao_f4_set_proporcional_e30": decisao_real(),
        "pytest": None if a.sem_pytest else pytest_resumo(),
    }
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: res[k] for k in ("hashes_v1", "importacoes", "compilacao_ok", "pytest")}, indent=1, ensure_ascii=False)[:1500])


if __name__ == "__main__":
    main()
