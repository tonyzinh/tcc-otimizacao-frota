"""Pseudonimização estável das extrações V1 Viagens (esquema `hmac-sha256-v1`).

Propriedades:
- segredo guardado FORA do repositório e fora de pastas sincronizadas (padrão: `%LOCALAPPDATA%/tcc_frota/segredos`),
  com permissão restrita ao usuário e cópia de segurança separada;
- `chave_id` = impressão digital derivada do segredo (HMAC com rótulo fixo): identifica a versão sem expor o segredo;
- pseudônimo = HMAC-SHA256(segredo, "<entidade>\\x1f<valor normalizado>") truncado em 20 hex. A mesma entidade
  (motorista, placa...) dá o mesmo pseudônimo em qualquer fonte, depois de normalizada;
- o segredo NUNCA é criado em silêncio: `inicializar` é explícito e recusa-se quando já há dados dependentes;
- o registro `PSEUDONIMIZACAO.json` na raiz da extração fixa a `chave_id`; segredo ausente ou diferente interrompe.

É pseudonimização, não anonimização.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ESQUEMA = "hmac-sha256-v1"
HEX = 20
ARQUIVO_REGISTRO = "PSEUDONIMIZACAO.json"
MIN_SEGREDO = 32

# Coluna de origem -> entidade lógica. Mesma entidade em fontes distintas => mesmo pseudônimo.
# `placa` (ES `placa`, Cobli `license_plate`) e `veiculo_cod` (ODS `CD_VEICULO`) são famílias diferentes:
# a equivalência entre elas não é presumida (ver docs/PSEUDONIMIZACAO_E_VINCULOS.md).
ENTIDADE_POR_COLUNA = {
    "cd_motorista": "motorista",
    "user_id": "motorista",
    "codigo": "motorista",
    "cd_passageiro": "passageiro",
    "cd_veiculo": "veiculo_cod",
    "cd_veiculo_pseudo": "placa",
    "license_plate": "placa",
    "placa": "placa",
    "vehicle_id": "cobli_veiculo",
    "device_id": "cobli_dispositivo",
    "driver_id": "cobli_motorista",
    "cd_condutor": "condutor",
    "cd_veiculo_condutor": "veiculo_condutor",
    "tx_placa": "placa",
    "cd_integracao_vehicle_id": "cobli_veiculo",
    "tx_integracao_device_id": "cobli_dispositivo",
}


class PseudonimizacaoError(RuntimeError):
    """Base: nunca inclui o segredo na mensagem."""


class SegredoAusente(PseudonimizacaoError):
    pass


class SegredoIncompativel(PseudonimizacaoError):
    pass


@dataclass(frozen=True)
class Segredo:
    valor: str
    chave_id: str

    def __repr__(self) -> str:  # nunca expõe o valor
        return f"Segredo(chave_id={self.chave_id!r})"


def chave_id_de(valor: str) -> str:
    return hmac.new(valor.encode(), b"tcc_frota/chave_id/" + ESQUEMA.encode(), hashlib.sha256).hexdigest()[:12]


def pasta_segredos() -> Path:
    base = os.getenv("TCC_SEGREDOS_DIR")
    if base:
        return Path(base)
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local") / "tcc_frota" / "segredos"
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share") / "tcc_frota" / "segredos"


def pasta_backup() -> Path:
    base = os.getenv("TCC_SEGREDOS_BACKUP_DIR")
    return Path(base) if base else Path.home() / ".tcc_frota_backup"


def arquivo_segredo() -> Path:
    return pasta_segredos() / "pseudo_secret"


def _restringir(path: Path) -> None:
    """Permissão só do usuário atual (best effort; falha é avisada, não silenciada)."""
    try:
        if os.name == "nt":
            user = os.environ.get("USERNAME", "")
            alvo = str(path)
            subprocess.run(["icacls", alvo, "/inheritance:r"], capture_output=True, check=True)
            subprocess.run(
                ["icacls", alvo, "/grant:r", f"{user}:(OI)(CI)F" if path.is_dir() else f"{user}:F"], capture_output=True, check=True
            )
        else:
            path.chmod(0o700 if path.is_dir() else 0o600)
    except (OSError, subprocess.SubprocessError):
        print(f"AVISO: não foi possível restringir permissões de {path.name}", file=sys.stderr)


def _gravar_protegido(destino: Path, valor: str) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    _restringir(destino.parent)
    destino.write_text(valor + "\n", encoding="utf-8")
    _restringir(destino)


def carregar_segredo(caminho: Path | None = None) -> Segredo:
    """Lê o segredo protegido. Nunca cria. Variável `TCC_PSEUDO_SECRET` serve só a testes/CI."""
    valor = os.getenv("TCC_PSEUDO_SECRET", "")
    if not valor:
        arq = caminho or arquivo_segredo()
        if arq.is_file():
            valor = arq.read_text(encoding="utf-8").strip()
    if not valor:
        raise SegredoAusente(
            "segredo de pseudonimização ausente. Não é gerado automaticamente. Restaure a cópia de segurança "
            "(`python -m tcc_frota.data.privacy restaurar`) ou, se NÃO houver dados dependentes, `inicializar`."
        )
    if len(valor) < MIN_SEGREDO:
        raise SegredoIncompativel(f"segredo curto demais (< {MIN_SEGREDO} caracteres)")
    return Segredo(valor, chave_id_de(valor))


def existem_dados_dependentes(raiz: Path) -> bool:
    return raiz.is_dir() and any(raiz.rglob("manifest.json"))


def inicializar(raiz: Path, *, a_partir_de: Path | None = None, destino: Path | None = None) -> Segredo:
    """Cria o segredo. Sem `a_partir_de`, só se NÃO houver dados dependentes em `raiz`.

    `a_partir_de` migra um valor existente (ex.: o sal legado) sem alterá-lo.
    """
    destino = destino or arquivo_segredo()
    if destino.is_file():
        raise PseudonimizacaoError("já existe segredo protegido; nada foi alterado")
    if a_partir_de is not None:
        valor = a_partir_de.read_text(encoding="utf-8").strip()
        if len(valor) < MIN_SEGREDO:
            raise SegredoIncompativel(f"segredo de origem curto demais (< {MIN_SEGREDO} caracteres)")
    else:
        if existem_dados_dependentes(raiz):
            raise SegredoAusente("há dados extraídos dependentes de um segredo anterior: um novo segredo os tornaria incompatíveis")
        valor = os.urandom(32).hex()
    _gravar_protegido(destino, valor)
    return Segredo(valor, chave_id_de(valor))


def fazer_backup(segredo: Segredo, destino_dir: Path | None = None, origem: Path | None = None) -> Path:
    """Cópia separada, nomeada pela chave_id; confere a impressão digital depois de gravar."""
    pasta = destino_dir or pasta_backup()
    arq = pasta / f"pseudo_secret.{segredo.chave_id}.bak"
    if not arq.exists():
        _gravar_protegido(arq, segredo.valor)
    if chave_id_de(arq.read_text(encoding="utf-8").strip()) != segredo.chave_id:
        raise PseudonimizacaoError("a cópia de segurança não confere com o segredo")
    return arq


def restaurar(chave_id: str, destino: Path | None = None, backup_dir: Path | None = None) -> Segredo:
    destino = destino or arquivo_segredo()
    arq = (backup_dir or pasta_backup()) / f"pseudo_secret.{chave_id}.bak"
    if not arq.is_file():
        raise SegredoAusente(f"cópia de segurança {chave_id} não encontrada")
    if destino.is_file():
        raise PseudonimizacaoError("já existe segredo protegido; nada foi alterado")
    valor = arq.read_text(encoding="utf-8").strip()
    if chave_id_de(valor) != chave_id:
        raise SegredoIncompativel("a cópia de segurança não corresponde à chave_id pedida")
    _gravar_protegido(destino, valor)
    return Segredo(valor, chave_id)


# --- transformação -----------------------------------------------------------------------------------------------

_NAO_ALNUM = re.compile(r"[^0-9A-Za-z]")
_INTEIRO = re.compile(r"^-?\d+\.0+$")


def normalizar(entidade: str, valor: object) -> str | None:
    """Forma canônica por entidade; None/vazio => None. Placa: maiúscula, só alfanuméricos."""
    if valor is None:
        return None
    s = str(valor).strip()
    if not s or s.lower() in {"nan", "none", "<na>"}:
        return None
    if _INTEIRO.match(s):  # 5.0 -> 5 (mesmo identificador vindo como float)
        s = s.split(".")[0]
    if entidade.startswith("cobli_"):  # UUIDs/ids: caixa não distingue a mesma entidade
        return s.lower()
    if entidade == "placa":
        s = _NAO_ALNUM.sub("", s).upper()
        return s or None
    return s


def pseudonimo(entidade: str, valor: object, segredo: Segredo) -> str | None:
    n = normalizar(entidade, valor)
    if n is None:
        return None
    return hmac.new(segredo.valor.encode(), f"{entidade}\x1f{n}".encode(), hashlib.sha256).hexdigest()[:HEX]


def entidade_da_coluna(coluna: str) -> str:
    try:
        return ENTIDADE_POR_COLUNA[coluna]
    except KeyError as e:
        raise PseudonimizacaoError(f"coluna sem entidade declarada para pseudonimização: {coluna}") from e


def descricao(segredo: Segredo) -> dict:
    """Vai nos manifestos: identifica a versão, nunca o segredo."""
    return {"esquema": ESQUEMA, "chave_id": segredo.chave_id, "hex": HEX}


# --- registro e guarda da campanha ----------------------------------------------------------------------------------


def garantir_compatibilidade(raiz: Path, segredo: Segredo | None) -> dict:
    """Interrompe se o segredo estiver ausente ou diferente do registrado; registra na primeira extração.

    Lotes antigos sem `pseudonimizacao` no manifesto (legado) bloqueiam: precisam ser regravados com `--forcar`
    por quem confirmou que podem ser substituídos.
    """
    reg = raiz / ARQUIVO_REGISTRO
    if reg.is_file():
        dados = json.loads(reg.read_text(encoding="utf-8"))
        if segredo is None:
            raise SegredoAusente(f"há extração registrada com chave_id {dados['chave_id']} e o segredo está ausente: não continue")
        if dados["chave_id"] != segredo.chave_id or dados["esquema"] != ESQUEMA:
            raise SegredoIncompativel(
                f"segredo atual (chave_id {segredo.chave_id}) difere do registrado ({dados['chave_id']}, {dados['esquema']}): "
                "combinar lotes quebraria os vínculos"
            )
        return dados
    legados = [p for p in raiz.rglob("manifest.json") if "pseudonimizacao" not in _ler(p)] if raiz.is_dir() else []
    if legados:
        raise SegredoIncompativel(
            f"{len(legados)} lote(s) sem versão de pseudonimização (legado). Regrave-os com --forcar ou mova-os para outra pasta"
        )
    if segredo is None:
        raise SegredoAusente("segredo ausente")
    dados = {**descricao(segredo), "criado_em_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")}
    raiz.mkdir(parents=True, exist_ok=True)
    reg.write_text(json.dumps(dados, indent=1), encoding="utf-8")
    return dados


def _ler(p: Path) -> dict:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def lote_compativel(manifesto: dict, segredo: Segredo) -> bool:
    p = manifesto.get("pseudonimizacao") or {}
    return p.get("chave_id") == segredo.chave_id and p.get("esquema") == ESQUEMA


__all__ = [
    "ESQUEMA",
    "PseudonimizacaoError",
    "Segredo",
    "SegredoAusente",
    "SegredoIncompativel",
    "carregar_segredo",
    "fazer_backup",
    "garantir_compatibilidade",
    "inicializar",
    "normalizar",
    "pseudonimo",
    "restaurar",
]
_ = shutil  # reservado: cópia de arquivos de segredo é feita por leitura/escrita para controlar permissões
