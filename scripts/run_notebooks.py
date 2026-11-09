"""Executa os notebooks de ``notebook/`` em kernel limpo (nbclient), de cima para baixo, e registra o resultado.

Uso: python scripts/run_notebooks.py [--inplace]
Sem --inplace, os notebooks não são alterados. Com --inplace, gravam-se as saídas de TEXTO (imagens e HTML pesado são removidos).
Resultado em ``reports/manifests/notebooks_execucao.json`` (sucesso/falha por notebook; falhas por dado privado ausente ficam explícitas).
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

ROOT = Path(__file__).resolve().parents[1]


def _strip_heavy_outputs(nb) -> None:
    for cell in nb.cells:
        if cell.cell_type != "code":
            continue
        kept = []
        for out in cell.get("outputs", []):
            data = out.get("data")
            if data:
                data = {k: v for k, v in data.items() if k == "text/plain"}
                if not data:
                    continue
                out["data"] = data
            kept.append(out)
        cell["outputs"] = kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--inplace", action="store_true")
    args = ap.parse_args()
    results = []
    for path in sorted((ROOT / "notebook").glob("*.ipynb")):
        nb = nbformat.read(path, as_version=4)
        t0 = time.time()
        status, detail = "ok", ""
        try:
            NotebookClient(nb, timeout=900, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
        except CellExecutionError as exc:
            status, detail = "falhou", str(exc).splitlines()[-1][:300]
        results.append({"notebook": path.name, "status": status, "detalhe": detail, "segundos": round(time.time() - t0, 1)})
        print(results[-1])
        if args.inplace and status == "ok":
            _strip_heavy_outputs(nb)
            nbformat.write(nb, path)
    out = ROOT / "reports" / "manifests" / "notebooks_execucao.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"executado_em": time.strftime("%Y-%m-%dT%H:%M:%S"), "resultados": results}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    return 0 if all(r["status"] == "ok" for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
