"""Descoberta e conferência dos lotes extraídos por `extrair.js`.

Cada lote tem um `manifest_<tag>.json` com as fases (`req`, `hist`, `snap`, `sum`, `diag`),
os arquivos de cada fase e as contagens `lidos`/`total`. Os `.zip` gerados no Windows podem
criar pasta duplicada (`dados_x/dados_x/`) ou nomes com barra invertida
(`dados_x\\req_x_p01.json`); a descoberta aceita essas formas sem alterar os originais.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

REQUIRED_TAGS = ("mar2026", "historico56", "set2026", "historico56_set")
PHASES = ("req", "hist", "snap", "sum")


def _base_name(path: Path) -> str:
    """Nome do arquivo sem prefixo de pasta embutido por zip do Windows."""
    return path.name.replace("\\", "/").rsplit("/", 1)[-1]


@dataclass
class Batch:
    tag: str
    folder: Path
    manifest: dict
    files: dict[str, list[Path]] = field(default_factory=dict)
    problems: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def expected(self, phase: str) -> int | None:
        info = self.manifest.get("fases", {}).get(phase)
        return None if info is None else info.get("total")


def _index_folder(folder: Path) -> dict[str, Path]:
    index: dict[str, Path] = {}
    for path in folder.rglob("*.json"):
        index.setdefault(_base_name(path), path)
    return index


def read_batch(manifest_path: Path) -> Batch:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    tag = str(manifest.get("tag") or _base_name(manifest_path)[len("manifest_"):-len(".json")])
    folder = manifest_path.parent
    index = _index_folder(folder)
    batch = Batch(tag, folder, manifest)
    for phase, info in manifest.get("fases", {}).items():
        names = info.get("arquivos", [])
        paths = [index.get(name) for name in names]
        missing = [name for name, path in zip(names, paths) if path is None]
        if missing:
            batch.problems.append(f"{phase}: {len(missing)} arquivo(s) ausente(s)")
        batch.files[phase] = [p for p in paths if p is not None]
        if "lidos" in info and info.get("lidos") != info.get("total"):
            batch.problems.append(f"{phase}: lidos {info.get('lidos')} != total {info.get('total')}")
        if info.get("ok") is False:
            batch.problems.append(f"{phase}: fase marcada como não ok")
    return batch


def discover(root: str | Path) -> dict[str, Batch]:
    """Encontra lotes pelos manifestos; em duplicata do mesmo tag, mantém o primeiro em ordem de caminho."""
    root = Path(root)
    found: dict[str, Batch] = {}
    for manifest_path in sorted(root.rglob("*.json")):
        name = _base_name(manifest_path)
        if not (name.startswith("manifest_") and name.endswith(".json")):
            continue
        batch = read_batch(manifest_path)
        if batch.tag in found:
            continue
        found[batch.tag] = batch
    return found


def prepare_raw(root: str | Path, required: tuple[str, ...] = REQUIRED_TAGS, *,
                materialize_to: str | Path | None = None, echo=print) -> dict[str, Batch]:
    """Lista lotes encontrados, ausentes e rejeitados; falha se faltar algum lote exigido.

    Com `materialize_to`, copia cada lote aceito para `<destino>/<tag>/` com o nome original do
    arquivo, sem mover nem alterar a origem.
    """
    batches = discover(root)
    accepted = {tag: b for tag, b in batches.items() if b.ok}
    rejected = {tag: b for tag, b in batches.items() if not b.ok}
    missing = [tag for tag in required if tag not in accepted]
    echo(f"lotes encontrados: {sorted(batches)}")
    echo(f"lotes aceitos: {sorted(accepted)}")
    for tag, batch in sorted(rejected.items()):
        echo(f"lote rejeitado {tag}: {'; '.join(batch.problems)}")
    echo(f"lotes exigidos ausentes ou rejeitados: {missing}")
    if missing:
        raise FileNotFoundError(f"lotes exigidos ausentes ou rejeitados: {missing}")
    if materialize_to is not None:
        for tag, batch in accepted.items():
            target = Path(materialize_to) / tag
            target.mkdir(parents=True, exist_ok=True)
            for paths in batch.files.values():
                for source in paths:
                    destination = target / _base_name(source)
                    if not destination.exists():
                        shutil.copy2(source, destination)
            manifest_name = f"manifest_{tag}.json"
            if not (target / manifest_name).exists():
                (target / manifest_name).write_text(json.dumps(batch.manifest, ensure_ascii=False, indent=2),
                                                    encoding="utf-8")
    return accepted


def iter_hits(batch: Batch, phase: str) -> Iterator[tuple[str, int, dict]]:
    """Gera (arquivo, página, `_source`) na ordem do manifesto."""
    for page, path in enumerate(batch.files.get(phase, []), start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for hit in payload["hits"]["hits"]:
            yield _base_name(path), page, hit["_source"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_hashes(batches: dict[str, Batch]) -> dict[str, str]:
    """SHA-256 de cada arquivo de dados usado, chaveado por `<tag>/<arquivo>`."""
    out: dict[str, str] = {}
    for tag, batch in sorted(batches.items()):
        for phase in sorted(batch.files):
            for path in batch.files[phase]:
                out[f"{tag}/{_base_name(path)}"] = sha256_file(path)
    return out
