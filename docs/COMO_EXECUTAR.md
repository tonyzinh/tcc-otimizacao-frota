# Como executar

Resumo prático; a descrição completa está no [guia](GUIA_COMPLETO_REPOSITORIO.md). PowerShell (Windows); em Linux/macOS troque `$env:X='v'` por `export X=v` (não testado).

## Instalação (verificado)

```powershell
python -m pip install -e ".[test,v2]"
python -m pytest            # 280 passed, 1 skipped em 28/10/2026
```

## Sintético (sem dados reais)

```powershell
tcc-frota build-synthetic-data --out reports/runs/medallion
tcc-frota run-synthetic --out reports/runs
```

## Impressão digital antes/depois de mudanças estruturais (verificado)

```powershell
python scripts/validar_baseline.py --out reports/repository_migration/baseline_depois.json
```

Compara hashes da v1 e dos artefatos versionados, importação de módulos, compilação, métricas sintéticas determinísticas e pytest. Não lê dados reais.

## Com dados reais (NÃO executado na reorganização)

```powershell
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'
tcc-frota prepare-raw --raw data/raw
tcc-frota final-run --raw data/raw --out reports/runs/tcc_final --publish reports/tcc_final
```

Atenção: `--publish reports/tcc_final` **sobrescreve a v1 congelada**; para reproduzir sem risco, publique em outra pasta e compare com os hashes de `docs/V2_PREREGISTRO.md` §1.
Bateria: `scripts/bateria_algoritmos.ps1`; seletivo: `scripts/guloso_seletivo.ps1`; extensão: `scripts/v3_fase1.py` … `v3_fase4.py`, `v3_decisao.py`, `v3_gerar_saidas.py`.

## Testes úteis

`python -m pytest tests/reproducibility/test_estrutura_repositorio.py` (contratos estruturais) e `python -m pytest -k v3` (extensão).
