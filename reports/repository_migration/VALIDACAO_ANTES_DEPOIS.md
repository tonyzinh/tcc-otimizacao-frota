# Validação antes/depois

Geração: `python scripts/validar_baseline.py` (28/10/2026). Antes = `baseline_antes.json`; depois = `baseline_depois.json` (Python 3.12).

| Item | Antes | Depois | Status |
|---|---|---|---|
| Imports | 103 módulos importados, 0 falhas | 103 módulos, 0 falhas | Igual |
| Compilação | `compileall` OK | OK | Igual |
| Testes | 266 passed, 1 skipped | 280 passed, 1 skipped | Aumentou (+14 testes estruturais; 0 falhas) |
| Execução (CLI) | pontos de entrada `tcc-frota`, `tcc-frota-disponibilidade` resolvem | idem (teste novo) | Igual |
| Métricas | experimento sintético determinístico (dia 0, 2 cenários × 2 políticas): ex. `alcancavel|proporcional` KM vazio 43,949411552; `sem_reposicionamento` 37,825672611 | idênticas, casa a casa | Igual |
| Decisão F4 (set, proporcional, e\*=30) | NB −0,5377, IC [−1,1569; 0,0862], “inconclusivo” | idêntica | Igual |
| Resultados | v1: 19/19 hashes conferem com o pré-registro; digest de `reports/tcc_final`, `tcc_v2`, `resultados`, `tabelas`, `config`, `databricks` | digests idênticos | Igual |
| Reprodutibilidade com dados reais | não executável (sem `data/raw/`) | idem | **Bloqueado** (não afirmado) |

Uma primeira execução do `baseline_depois` registrou 1 falha (o teste de links do guia apontava para este relatório ainda inexistente); após criar os documentos, o JSON foi regerado e mostra 280 passed, 1 skipped.
