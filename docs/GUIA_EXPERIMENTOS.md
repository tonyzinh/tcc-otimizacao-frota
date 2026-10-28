# Guia de experimentos

Campanhas, versões e como reproduzi-las. Estados e relações: [VERSOES_E_EXPERIMENTOS.md](VERSOES_E_EXPERIMENTOS.md). Interpretação de métricas: [guia completo §9](GUIA_COMPLETO_REPOSITORIO.md).

**Aviso.** Todos os comandos “reais” exigem `data/raw/` (fora do Git) e `TCC_REAL_DATA_AUTHORIZED=YES`. **Nenhum foi reexecutado na finalização do repositório**; só o sintético e os testes. Para não sobrescrever resultados congelados, aponte `--out`/`--publish` para pastas novas e compare com os hashes.

| Campanha | Semente / configuração | Comando | Saída (congelada?) |
|---|---|---|---|
| Sintético | semente 20261014 (padrão) | `tcc-frota build-synthetic-data --out reports/runs/medallion`; `tcc-frota run-synthetic --out reports/runs` | `reports/runs/` (ignorada) |
| Rodada final (v1) | `config/experiment.yaml`, calibração/seleção em `v2/experiment.py` | `tcc-frota prepare-raw --raw data/raw`; `tcc-frota final-run --raw data/raw --out reports/runs/tcc_final` | `reports/tcc_final/` **CONGELADA** (não usar `--publish` aqui) |
| Bateria | grades pré-registradas em `algoritmos/protocolo.py`; `resultados/registro_configuracoes.csv` | `scripts/bateria_algoritmos.ps1` | `resultados/` **CONGELADA** |
| Seletivo | ORCAMENTO §5 | `scripts/guloso_seletivo.ps1` | `resultados/seletivo/` **CONGELADA** |
| Demanda, pickup | — | `python scripts/rodar_demanda.py`; `python scripts/rodar_pickup.py` | `resultados/demanda`, `pickup` |
| Extensão v2 (pacote `v3`) | `docs/V2_PREREGISTRO.md` | `python scripts/v3_fase1.py`, `v3_fase2.py`, `v3_fase2_controle.py`, `v3_fase3.py`, `v3_fase4.py`, `v3_decisao.py`, `v3_mde_nb.py`, `v3_gerar_saidas.py` | `reports/tcc_v2/` **ATUAL** |
| Verificações independentes | — | `scripts/checagem_independente.py`, `conferencia_seletivo.py`, `nao_vazamento_seletivo.py`, `reexecucao_sementes.py` | impressão no console |

A ordem das Fases 1–4 e os argumentos de cada script estão nos próprios scripts (`--help`); confirme-os antes de rodar, pois esta tabela não os testou um a um.

## Como saber se algo mudou

```powershell
python scripts/validar_baseline.py --out reports/validation_current/baseline_novo.json
python scripts/verificar_repositorio.py
```

O primeiro compara hashes dos artefatos versionados, importações, métricas sintéticas determinísticas e a decisão F4; o segundo roda lint, formatação, compilação, pytest e as checagens de integridade.

## Limitações científicas

Resultado nulo (nenhum planejador reduz o KM vazio por corrida) vale para este simulador, dados e hipóteses; KM estimado não é KM faturado (DT003); sem aprovação da empresa as regras `PROPOSTA`/`PENDENTE` continuam hipóteses; o problema é de **reposicionamento preventivo D+1**, não PRV ([classificação](../reports/validation_current/16_CLASSIFICACAO_PRV_VRP.md)).
