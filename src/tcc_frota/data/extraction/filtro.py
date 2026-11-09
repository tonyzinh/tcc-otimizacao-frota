"""Delimitação da operação V1 Viagens (decisão R-04 em `docs/REGISTRO_DECISOES.md`, aprovada em 06/11/2026).

"V1 Viagens" é o nome da operação (aplicativo de corridas), não a "v1" do algoritmo ou dos experimentos.
Critério: produto `V1` (`APP_REGIAO.TX_PRODUTO`) na região 1 (Grande Vitória, escopo do TCC) e serviços V1.
Prime, Aluguel/FastRental e Assinatura ficam fora. Regiões e serviços saem de campos, não de nomes de tabelas.
"""

from __future__ import annotations

from dataclasses import dataclass

REGIAO_GRANDE_VITORIA = 1
SERVICOS_V1 = (1, 11, 12, 19)  # V1 PADRÃO, V1 COM RETORNO, V1 INTRAMUNICIPAL, V1 Padrão II (PJ)
VERSAO_FILTRO = "R-04/2026-11-06"


@dataclass(frozen=True)
class FiltroV1:
    regiao: int = REGIAO_GRANDE_VITORIA
    servicos: tuple[int, ...] = SERVICOS_V1

    @property
    def servicos_sql(self) -> str:
        return ",".join(str(int(s)) for s in self.servicos)

    def descricao(self) -> dict:
        return {"versao": VERSAO_FILTRO, "regiao": self.regiao, "servicos": list(self.servicos)}
