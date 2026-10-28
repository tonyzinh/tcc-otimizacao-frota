"""Calculadora de decisão NB(e*) sobre um CSV diário agregado (ex.: reports/tcc_v2/fase4_dias.csv). Exemplo em docs/EXEMPLO_DECISAO.md."""
import argparse
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

if __name__ == "__main__":
    from tcc_frota.v3 import decisao
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", type=Path, default=ROOT / "reports/tcc_v2/fase4_dias.csv")
    ap.add_argument("--periodo", required=True)
    ap.add_argument("--cenario", required=True, help="nome do plano (ex.: proporcional)")
    ap.add_argument("--grupo", help="valor da coluna `grupo` do plano")
    ap.add_argument("--par", help="valor da coluna `par` (baseline e plano)")
    ap.add_argument("--e-star", type=float, required=True, help="km vazio extra aceito por corrida adicional")
    ap.add_argument("--reps", type=int, default=10000)
    a = ap.parse_args()
    plano, base = decisao.dias_de_csv(a.csv, periodo=a.periodo, cenario=a.cenario, grupo=a.grupo, par=a.par)
    for k, v in asdict(decisao.decidir(a.e_star, plano, base, reps=a.reps, rotulo=a.periodo)).items():
        print(f"{k}: {v}")
