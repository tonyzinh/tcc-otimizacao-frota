"""Contratos estruturais do repositório: não alteram a ciência, só protegem a organização e a reprodutibilidade."""

import hashlib
import importlib
import pkgutil
import re
import subprocess
import tomllib
from pathlib import Path

import pytest

import tcc_frota

ROOT = Path(__file__).resolve().parents[2]
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
DOCS_NOVOS = (
    "docs/GUIA_COMPLETO_REPOSITORIO.md",
    "docs/ARQUITETURA_REORGANIZADA.md",
    "docs/COMO_EXECUTAR.md",
    "docs/MAPEAMENTO_TCC_CODIGO.md",
    "reports/repository_migration/RELATORIO_REORGANIZACAO.md",
    "reports/repository_migration/VALIDACAO_ANTES_DEPOIS.md",
    "README.md",
)


def _git(*args: str) -> list[str]:
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        pytest.skip("git indisponível")
    return [ln for ln in r.stdout.splitlines() if ln]


def test_artefatos_da_v1_continuam_identicos_aos_hashes_do_registro():
    texto = (ROOT / "docs/V2_PREREGISTRO.md").read_text(encoding="utf-8")
    linhas = re.findall(r"^\| (\S+\.(?:csv|json)) \| ([0-9a-f]{64}) \|", texto, re.M)
    assert len(linhas) == 19
    divergentes = [n for n, h in linhas if hashlib.sha256((ROOT / "reports/tcc_final" / n).read_bytes()).hexdigest() != h]
    assert divergentes == []


def test_todos_os_modulos_do_pacote_sao_importaveis():
    falhas = {}
    for m in pkgutil.walk_packages(tcc_frota.__path__, "tcc_frota."):
        try:
            importlib.import_module(m.name)
        except ImportError as e:
            if (getattr(e, "name", "") or "").split(".")[0] not in OPCIONAIS:
                falhas[m.name] = str(e)
    assert falhas == {}


def test_pontos_de_entrada_do_pyproject_resolvem_para_funcoes():
    scripts = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["scripts"]
    assert {"tcc-frota", "tcc-frota-disponibilidade"} <= set(scripts)
    for destino in scripts.values():
        modulo, funcao = destino.split(":")
        assert callable(getattr(importlib.import_module(modulo), funcao))


def test_configuracoes_existem_e_nao_estao_vazias():
    for nome in ("business_rules.yaml", "data_contract.yaml", "experiment.yaml"):
        assert (ROOT / "config" / nome).read_text(encoding="utf-8").strip()


def test_dados_reais_nao_estao_versionados():
    permitidos = {"data/synthetic/README.md"}
    versionados = {p for p in _git("ls-files", "data")}
    assert versionados <= permitidos or all(p.startswith("data/synthetic/") for p in versionados)
    assert not [p for p in _git("ls-files", "reports/runs")]


def test_sem_caminho_absoluto_de_usuario_no_codigo_versionado():
    padrao = re.compile("C:" + re.escape("\\") + "Users|/Users/|/home/[a-z]+/", re.I)
    ofensores = []
    for p in _git("ls-files", "src", "scripts", "tests", "config"):
        arq = ROOT / p
        if (
            arq.suffix in {".py", ".yaml", ".ps1", ".toml"}
            and arq.name != Path(__file__).name
            and padrao.search(arq.read_text(encoding="utf-8", errors="replace"))
        ):
            ofensores.append(p)
    assert ofensores == []


def test_artefatos_da_auditoria_foram_movidos_para_reports():
    assert (ROOT / "reports/thesis_audit/DATA_SCIENCE_AUDIT.md").exists()
    assert not (ROOT / "reviews").exists()


@pytest.mark.parametrize("doc", DOCS_NOVOS)
def test_links_relativos_dos_documentos_novos_resolvem(doc):
    arquivo = ROOT / doc
    if not arquivo.exists():
        pytest.skip(f"{doc} ainda não existe")
    ruins = []
    for alvo in re.findall(r"\]\(([^)\s]+)\)", arquivo.read_text(encoding="utf-8")):
        if alvo.startswith(("http://", "https://", "mailto:", "#")):
            continue
        caminho = (arquivo.parent / alvo.split("#")[0]).resolve()
        if not caminho.exists():
            ruins.append(alvo)
    assert ruins == []
