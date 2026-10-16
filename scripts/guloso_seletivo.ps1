# Guloso seletivo (C0-C3), execução local reprodutível. Pré-registro: docs/ORCAMENTO_CONFIGURACOES.md §5.
$ErrorActionPreference = 'Stop'
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'; $env:PYTHONPATH = 'src'; $env:PYTHONIOENCODING = 'utf-8'
$py = '.venv\Scripts\python.exe'
& $py -m tcc_frota.algoritmos.cli regressao
& $py -m tcc_frota.algoritmos.cli seletivo-calibrar --workers 10      # só 2-15/03
& $py -m tcc_frota.algoritmos.cli seletivo-variantes --workers 10     # 4.4, só calibração
& $py -m tcc_frota.algoritmos.cli seletivo-congelar
git add resultados/seletivo/finalistas.json; git commit -m "results(seletivo): freeze finalist before test"
foreach ($p in 'mar2026','set2026') {
  & $py -m tcc_frota.algoritmos.cli seletivo-testar $p --workers 10
  & $py -m tcc_frota.algoritmos.cli seletivo-analisar $p
}
& $py -m tcc_frota.algoritmos.cli seletivo-relatorio
& $py -m tcc_frota.analise.valor_liquido          # lê config/custos_privado.yaml (fora do Git)
& $py -m tcc_frota.analise.deslocamento_livre
& $py scripts\nao_vazamento_seletivo.py
& $py scripts\conferencia_seletivo.py
& $py scripts\checagem_independente.py resultados\seletivo
