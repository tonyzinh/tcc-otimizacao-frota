"""CLI: python -m tcc_frota.data.privacy status|inicializar|backup|restaurar. Nunca imprime o segredo."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from tcc_frota.data.extraction.writer import RAIZ_PADRAO
from tcc_frota.data.privacy import pseudonymization as p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="tcc_frota.data.privacy", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    ini = sub.add_parser("inicializar")
    ini.add_argument("--do-legado", type=Path, help="migra o valor de um arquivo de sal existente, sem alterá-lo")
    sub.add_parser("backup")
    res = sub.add_parser("restaurar")
    res.add_argument("chave_id")
    a = ap.parse_args(argv)
    raiz = RAIZ_PADRAO
    try:
        if a.cmd == "status":
            try:
                s = p.carregar_segredo()
                print(f"segredo presente em {p.arquivo_segredo()} chave_id={s.chave_id} esquema={p.ESQUEMA}")
            except p.SegredoAusente as e:
                print(f"AUSENTE: {e}")
                return 1
            reg = raiz / p.ARQUIVO_REGISTRO
            print("registro da extração:", reg.read_text(encoding="utf-8") if reg.is_file() else "inexistente")
        elif a.cmd == "inicializar":
            s = p.inicializar(raiz, a_partir_de=a.do_legado)
            print(f"segredo criado em {p.arquivo_segredo()} chave_id={s.chave_id}")
        elif a.cmd == "backup":
            print("cópia em", p.fazer_backup(p.carregar_segredo()))
        elif a.cmd == "restaurar":
            s = p.restaurar(a.chave_id)
            print(f"restaurado chave_id={s.chave_id}")
    except p.PseudonimizacaoError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
