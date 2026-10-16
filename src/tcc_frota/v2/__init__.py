"""Rodada v2: extratos Elasticsearch paginados (jan–mar e jul–set/2026).

Pacote separado do fluxo legado (DT010–DT012) para não alterar seus contratos. Os módulos
seguem a ordem do medalhão: `raw` (lotes e manifestos), `rules` (regras de limpeza),
`silver`/`gold` (tabelas locais equivalentes aos notebooks `nb_*_v2`), `forecast`, `fleet`,
`sim`, `policy` e `experiment`.
"""
