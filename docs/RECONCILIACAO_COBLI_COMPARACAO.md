# Cobli × corridas V1: por que 21,8% de "alta" virou 1 em 2.749 (08/11/2026)

**Conclusão (executada):** foi **erro meu na inspeção**, não mudança de dados, regras ou população. `scripts/inspecionar_vinculos_cobli.py` chamou a conciliação com o relógio Cobli **sem converter UTC→local** (padrão `deslocamento_cobli_s=0`), enquanto o relatório anterior usava `--desloc-cobli-s -10800`. Corrigido: `preparar()` converte explicitamente (`analise/tempo.py::para_local(..., "cobli")`); a nova execução reproduz **exatamente** os JSON anteriores nos 4 dias (comparação programática: `True` ×4; originais preservados em `reports/extracao_v1_viagens/anterior_desloc_manual/`).

## Tabela de reconciliação

| Item | Relatório anterior (piloto/4 dias) | Inspeção com erro | Inspeção corrigida |
|---|---|---|---|
| Universo/denominador | corridas encerradas com placa: 512 + 738 + 810 + 689 = **2.749** | idêntico (2.749) | idêntico (2.749) |
| Dias / veículos | 07, 10, 13, 17/03/2026; mesmos lotes | idem | idem |
| Regras (classes, tolerâncias, 180 s, 0,90/0,60/0,30, 300/1000 m) | iguais | iguais | iguais |
| Chaves/vínculos | placa (ponte `APP_VEICULO.TX_PLACA`) + intervalo | iguais | iguais |
| **Fuso Cobli** | UTC→local (−10800 s) | **nenhum (tratada como local)** | UTC→local explícito |
| Cobertura dos arquivos | Cobli por dia local (+3 h na janela) | idem | idem |
| Código/esquema | esquema 1 | esquema 1 | dados refeitos em esquema 2 (08/11); regra de conciliação inalterada |
| alta / provável / ambíguo / sem | 10/03: 21,82 / 48,78 / 7,59 / 21,82 % (4 dias: 580 / 1.477 / 194 / 498 de 2.749 = 21,1 / 53,7 / 7,1 / 18,1 %) | 1 / 600 / 547 / 1.601 | 580 / 1.477 / 194 / 498 |
| Natureza da diferença | — | **correção de erro (script de inspeção)** | — |

Já constava no relatório de 10/03 o teste de relógio: com deslocamento 0, "alta" = 0,0% e "sem correspondência" = 60,7%; com −3 h, 21,8% e 21,8%. A inspeção com erro reproduziu o cenário "0".

## Camadas de verificação (não confundir)
1. **Verificação automática** (feita): `inspecionar_vinculos_cobli.py`, 125 corridas estratificadas (classe × contexto), semente 20261108, recomputa sobreposição bruta e distância de borda a partir dos registros; 0 erros pelo critério fixado antes. Mede **consistência com as regras implementadas**, com o mesmo relógio e placa; não é confirmação independente.
2. **Revisão técnica de casos com evidência** (pendente): requer leitura caso a caso da amostra em `reports/runs/inspecao_vinculos_cobli.csv`; ainda não feita.
3. **Confirmação operacional** (pendente, depende de quem conhece o processo): se um trecho Cobli é a mesma operação da corrida.

## Uso permitido
Com a evidência atual a Cobli **não** é verdade de referência para validar km morto. Pode apoiar diagnósticos específicos (por exemplo, fração de km sem finalidade identificada) com as limitações declaradas: trechos são contêineres, relógio UTC inferido por evidência (RN024 pendente), 18,1% das corridas sem correspondência.

## Consolidação (registro de 08/11/2026)
**Resultado inválido, SUBSTITUÍDO:** "1 `alta` em 2.749 corridas" (1 / 600 / 547 / 1.601) e a amostra de 106 corridas daquela execução. Causa: o script de inspeção não convertia UTC→local. O arquivo `reports/extracao_v1_viagens/inspecao_vinculos_cobli.json` foi regravado com a execução corrigida; os números inválidos ficam registrados somente aqui. Não devem ser citados.

**Resultado corrigido (fonte: lotes do esquema 1 em `data/extraido/v1_viagens_esquema1_20261108/`, 4 dias, mesma regra):**

| Dia | Corridas (denominador) | alta | provável | ambíguo | sem correspondência |
|---|---|---|---|---|---|
| 07/03 | 512 | 87 | 304 | 20 | 101 |
| 10/03 | 738 | 161 | 360 | 56 | 161 |
| 13/03 | 810 | 145 | 461 | 59 | 145 |
| 17/03 | 689 | 187 | 352 | 59 | 91 |
| **Total** | **2.749** | **580 (21,1%)** | **1.477 (53,7%)** | **194 (7,1%)** | **498 (18,1%)** |

Denominador: corridas `CorridaEncerrada` com início e fim realizados e placa na ponte `APP_VEICULO.TX_PLACA` (solicitações V1 da região, sem Prime). Os dias 07, 10 e 13 são de treino e 17 é de validação; nenhum parâmetro foi ajustado com eles.

**Teste de regressão do erro:** `tests/unit/test_conciliacao_fuso.py` (corrida diurna e corrida que cruza 23:50→00:10; com conversão vincula, sem conversão não vincula).

**Alcance:** a reprodução dos JSON anteriores mostra consistência entre execuções do mesmo código e dados. Não mostra que cada correspondência seja a mesma operação real (verificação automática ≠ revisão técnica ≠ confirmação operacional). Após o esquema 2, os dias 07, 10 e 13 serão reconciliados de novo sobre os lotes novos como checagem de consistência.
