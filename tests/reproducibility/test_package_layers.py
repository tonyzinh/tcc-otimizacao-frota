"""Camadas de dependência entre pacotes: cada pacote só importa os permitidos (sem ciclos)."""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "tcc_frota"
ALLOWED = {
    "domain": set(),
    "assignment": {"domain"},
    "simulation": {"domain", "assignment", "data"},
    "data": {"domain"},
    "scenarios": {"domain", "assignment", "simulation"},
    "metrics": {"domain", "simulation", "assignment"},
    "visualization": {"scenarios", "metrics", "domain"},
    "cli": {"domain", "assignment", "simulation", "data", "scenarios", "metrics", "visualization"},
}


def _imports(pkg: str) -> set[str]:
    found: set[str] = set()
    for f in (SRC / pkg).rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            for name in names:
                parts = name.split(".")
                if parts[0] == "tcc_frota" and len(parts) > 1 and parts[1] != pkg:
                    found.add(parts[1])
    return found


def test_packages_only_import_allowed_layers():
    for pkg, allowed in ALLOWED.items():
        assert _imports(pkg) <= allowed, (pkg, _imports(pkg) - allowed)


def test_dependency_graph_has_no_cycles():
    graph = {pkg: _imports(pkg) for pkg in ALLOWED}
    visiting, done = set(), set()

    def visit(node):
        assert node not in visiting, f"ciclo em {node}"
        if node in done:
            return
        visiting.add(node)
        for dep in graph.get(node, ()):
            visit(dep)
        visiting.discard(node)
        done.add(node)

    for pkg in graph:
        visit(pkg)
