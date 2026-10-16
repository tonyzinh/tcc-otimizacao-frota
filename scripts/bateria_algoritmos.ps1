# Bateria de algoritmos de reposicionamento D+1 (execução local, reprodutível).
# Pré-requisitos: extratos em data/raw (fora do Git), sal em data/.pseudo_salt, .venv com a extra v2 e scipy.
# Ordem: regressão -> calibração (só 2-15/03) -> congelamento e commit -> teste de março -> setembro -> relatório.
$ErrorActionPreference = 'Stop'
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'   # processamento local autorizado (DT010-v2)
$env:PYTHONPATH = 'src'
$env:PYTHONIOENCODING = 'utf-8'
$py = '.venv\Scripts\python.exe'
& $py -m tcc_frota.algoritmos.cli regressao
foreach ($f in 'fluxo_custo_minimo','hungaro','milp','busca_local','recozimento','pso','robusto_cenarios') {
  & $py -m tcc_frota.algoritmos.cli calibrar $f --workers 10
  & $py -m tcc_frota.algoritmos.cli congelar $f
}
& $py -m tcc_frota.algoritmos.cli nsga2-busca
& $py -m tcc_frota.algoritmos.cli calibrar nsga2 --workers 10
& $py -m tcc_frota.algoritmos.cli congelar nsga2
foreach ($f in 'mpc','despacho') {
  & $py -m tcc_frota.algoritmos.cli calibrar $f --workers 10
  & $py -m tcc_frota.algoritmos.cli congelar $f
}
git add resultados/finalistas.json resultados/finalistas_extras.json
git commit -m "results(bateria): freeze finalists before test"   # o teste recusa rodar sem isso
foreach ($p in 'mar2026','set2026') {
  & $py -m tcc_frota.algoritmos.cli testar $p --workers 10
  & $py -m tcc_frota.algoritmos.cli testar-extra $p --workers 10
  & $py -m tcc_frota.algoritmos.cli analisar $p
}
& $py -m tcc_frota.algoritmos.relatorio
