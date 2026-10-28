"""Portão de qualidade local: lint, formatação, compilação, testes e integridade dos artefatos científicos.

Uso: python scripts/verificar_repositorio.py [--rapido]   (--rapido pula o pytest)
Não lê dados reais, não escreve em diretórios protegidos e não altera arquivos. Código de saída 0 só se nada falhar;
verificações indisponíveis (ex.: Ruff não instalado) aparecem como PULADO, nunca como aprovadas.
"""

import argparse
import compileall
import shutil
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CODIGO = ("src", "scripts", "tests", "app")


def executar(rotulo: str, comando: list[str]) -> str:
    """Roda um comando na raiz e devolve 'OK' ou 'FALHOU'."""
    resultado = subprocess.run(comando, cwd=RAIZ, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if resultado.returncode:
        print(f"[FALHOU] {rotulo}\n{(resultado.stdout + resultado.stderr)[-1500:]}")
        return "FALHOU"
    print(f"[OK]     {rotulo}")
    return "OK"


def comando_ruff() -> list[str] | None:
    """Ruff instalado, ou executado via uvx; None se nenhum dos dois existir."""
    if shutil.which("ruff"):
        return ["ruff"]
    if shutil.which("uvx"):
        return ["uvx", "ruff"]
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--rapido", action="store_true", help="não executa o pytest")
    argumentos = parser.parse_args()
    status: dict[str, str] = {}

    ruff = comando_ruff()
    if ruff:
        status["lint"] = executar("ruff check", [*ruff, "check", *CODIGO])
        status["formatação"] = executar("ruff format --check", [*ruff, "format", "--check", *CODIGO])
    else:
        print("[PULADO] ruff indisponível (instale com `uv tool install ruff`)")
        status["lint"] = status["formatação"] = "PULADO"

    compilou = all(compileall.compile_dir(RAIZ / pasta, quiet=1) for pasta in CODIGO)
    print(f"[{'OK' if compilou else 'FALHOU'}]     compilação")
    status["compilação"] = "OK" if compilou else "FALHOU"

    if argumentos.rapido:
        status["pytest"] = "PULADO"
    else:
        status["pytest"] = executar("pytest", [sys.executable, "-m", "pytest"])

    status["hashes e estrutura"] = executar(
        "hashes da v1, imports, dados fora do Git",
        [sys.executable, "-m", "pytest", "tests/reproducibility/test_estrutura_repositorio.py"],
    )
    print("\nResumo:", ", ".join(f"{k}={v}" for k, v in status.items()))
    return 1 if "FALHOU" in status.values() else 0


if __name__ == "__main__":
    sys.exit(main())
