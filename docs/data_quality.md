# Qualidade dos dados

> Documento consolidado em 09/11/2026 na reestruturação do repositório. Cada parte abaixo é o documento de origem, com o conteúdo preservado; só os caminhos de arquivos foram atualizados para a estrutura nova (mapa em `reports/manifests/repository_restructure/path_map.csv`). Datas e afirmações são as da origem.
> Caminhos marcados com † são de arquivos retirados da árvore ativa nas reorganizações de 09/11/2026 (código e documentos do estudo anterior, scripts substituídos pelo pacote). As cópias estão na pasta de preservação `../tcc-otimizacao-frota_preservacao_2026-11-09/` (`arvore_antiga/`, `rodada4_arquivamento/`, `copia_completa_pre_migracao/`). Nos trechos anteriores a 09/11/2026, `data/raw/` designa a pasta de extrato bruto antiga, apagada em 08/11; desde a reestruturação, `data/raw/` é a antiga `data/extraido/`.


## Avaliação da base V1 Viagens antes dos cenários (08/11/2026)

_Origem: `docs/data_quality.md`._

Evidência: execuções de 08/11/2026 sobre **4 dias** (07, 10, 13 e 17/03/2026) e consultas agregadas ao ODS/DW. Nada aqui afirma ganho do guloso, que **não foi alterado**. Complementa `data_dictionary.md` (06/11) e substitui as afirmações dele que divergem (ver §11). Pseudonimização: `data_dictionary.md`.

### 1. Demanda, compromissos externos e movimentos sem finalidade
| Classe | Definição | Fonte | Uso |
|---|---|---|---|
| A. Demanda-alvo | V1 Viagens, região 1, serviços 1/11/12/19, sem Prime | `ods/solicitacao`, `status_solicitacao` | única demanda e único resultado |
| B. Compromisso externo | corrida de veículo que atendeu V1 em ±7 dias e não é A (`prime`, `outro_servico`, `outra_regiao`) | `ods/compromissos_externos` (só veículo pseudonimizado, categoria e horários) | bloqueia o veículo; nunca entra em demanda, atendimento ou KM vazio |
| C. Finalidade não identificada | trecho Cobli sem corrida A nem compromisso B | `ods/telemetria_cobli` | "quilometragem não conciliada" |

10/03: 98 compromissos externos. Limite: só o que está em `APP_SOLICITACAO_HIST` registrado até 7 dias antes (agendamento mais antigo escapa); Aluguel/manutenção não aparecem. Se B não bastar, alternativas: subconjunto de veículos sem compromisso B no dia (perde representatividade: 11 das 117 placas do grupo "Operação" também fizeram Prime em 10/03) ou sensibilidade (cenário B).

### 2. Frota e grupos Cobli (10/03, placas por grupo × corridas no dia via `TX_PLACA`)
| Grupo Cobli | Placas | com V1 | com Prime | V1∩Prime | Evidência de vínculo V1 | Compartilha | Validade temporal | Tratamento |
|---|---|---|---|---|---|---|---|---|
| Operação | 117 | 105 | 15 | 11 | forte (105/117) | **sim, com Prime** | grupo é rótulo atual; histórico desde 2022 | incluir; marcar compartilhadas; usar B |
| Operação V1 VIX CAM | 5 | 4 | 1 | 1 | forte (4/5), **estava excluído** | sim (1) | desde 30/01/2026 | **incluir** (pendente: confirmar significado "CAM") |
| Operação Prime | 16 | 1 | 14 | 1 | fraca para V1 | sim (1) | desde 18/11/2024 | excluir da frota V1; 1 placa V1 vira compartilhada |
| Macaé, Mauá, Santos, Rio, Petrobras | 2–15 | 0 | 0 | 0 | nenhum V1 | não | — | excluir (outras regiões/contratos) |

Cadastro: 9.598 veículos (`APP_VEICULO` região 1, **foto de 06/11**, 1.928 placas repetidas entre `CD_VEICULO`); **observados** em 10/03: 116 com corrida V1 (114 com placa), 121 placas em ofertas ES, 117 placas Cobli "Operação". **Elegíveis** = observados com corrida V1 na janela, ligados por `TX_PLACA`; vínculo vigente por data (`APP_VEICULO_CONDUTOR`/`APP_VEICULO_HISTORICO` tem `CD_REGIAO`, `CD_TIPO_SERVICO`, `TX_STATUS_VIAGENS`) está **extraído só para vínculo veículo-condutor**; o histórico do veículo não foi extraído. Não incluí/excluí veículo por nome atual de grupo; o nome só orienta.

### 3. Regras de negócio e filtros
Região 1 e serviços 1/11/12/19: aplicados nas solicitações (campos próprios). Prime excluído por `TX_MODELO_SOLICITACAO`. Um veículo Prime executa corrida "Normal" (conflito de R-05) e vice-versa: a classe vem da **corrida**, não do veículo.

### 4. Coortes de motoristas (10/03)
| Conjunto | Motoristas | Observação |
|---|---|---|
| Atendimento V1 em D (presença efetiva mínima) | 129 | |
| Previsível até o corte: V1 em D−14..D−1 | 198 | cobre 127 dos 129; 2 novos; 71 sem corrida em D |
| Coorte retrospectiva ±7 dias (usada na extração) | 189 | contém 5 que só aparecem **depois** de D (informação futura) |
| Log de status em D | 175 | 41 fora da coorte |
| Contaminação por Prime no dia | 14/129 (10,9%) dos que atenderam V1; 32/189 na coorte | |
| Outro produto/região no dia | 0/129; 1/189 | |
Em ES ofertas houve 132 motoristas ofertados. A coorte ±7 dias é só recurso retrospectivo; o planejador D+1 deve usar o conjunto "até o corte", e o simulador a presença efetiva.

### 5. Jornada
Causa do zero: família de ID (R-09). Corrigido: 161 jornadas (1 rejeitada) em 10/03; 500.319 jornadas na origem desde antes de 2024 (~4.900/mês em 2026). Cobertura: 167 de 168 condutores de jornada em 10/03 ligam a `APP_VEICULO_CONDUTOR`; a ligação condutor↔motorista das solicitações usa `cd_veiculo_condutor` do log (extraído; **não validado**). Duração realizada em março: mediana 8,8 h, mínimo negativo (−0,5 h) e máximo 46 h ⇒ dados ruidosos, e **sem escala de 8/9/10 h assumida**. Nomeação: "jornada registrada" (`DT_INICIO/FIM_REALIZADO`) = janela de atividade registrada. Não foi transformado primeiro/último atendimento em jornada, login em disponibilidade nem ausência de corrida em indisponibilidade. "Não houve jornada" × "não observamos": a tabela tem jornadas em todos os meses de 2024–2026, mas a cobertura por pessoa (condutores com corrida V1 e sem jornada) **não foi medida**.

### 6. Semântica temporal (evidência)
| Campo | Interpretação | Evidência |
|---|---|---|
| ODS `DT_*` (datetime) | **hora local** | ES (foto com passageiro) − `DT_INICIO_REALIZADA`: mediana +1,0 min em 07, 10, 13 e 17/03 (n = 437, 597, 682, 609; p5 0,1; p95 ≤ 2,2); sob UTC seria +181 min. Perto da meia-noite (n = 100): mediana 0,6–1,3 min |
| ES (`-03:00` explícito) | local com offset | idem |
| Cobli `datetime2` | **UTC** | corridas sem par: 54–63% sem deslocamento → 13–22% com −3 h → 72–77% com +3 h (4 dias); mediana 57 m entre fim do trecho e destino |
Defeito corrigido: Cobli era consultada pelo dia UTC. **Pendências:** data de evento × ingestão (só `ingested_at` da extração foi guardado), `DT_REGISTRO` como criação (proxy), e RN024 oficial da empresa. Sem deslocamento indiscriminado.

### 7. Conciliação Cobli × corridas (`tcc_frota.conciliacao`, `scripts/conciliar_cobli.py`†)
Cobli aqui = trechos entre paradas (`trips`), **contêineres** de várias fases: o trecho começa em mediana 12 min antes e termina 12 min depois da perna com passageiro (10/03). Por isso a localização só vale como evidência quando a borda do trecho coincide no tempo com a borda da corrida (±folga).
Critérios (folga 180 s, cobertura ≥ 0,9 alta/ ≥ 0,6 provável / < 0,3 sem; destino ≤ 300 m confirma): **alta** = cobertura ≥ 0,9, trechos contíguos, uma borda alinhada e confirmada no espaço; **provável** = cobertura ≥ 0,9 (ou ≥ 0,6 contíguo) sem contradição espacial; **ambíguo** = fragmentado, contradição (> 1 km) ou cobertura intermediária; **sem correspondência** = cobertura < 0,3 ou sem placa.
10/03 (738 corridas encerradas; placa da ponte concorda com ES em 598 de 598 comparáveis):
| Classe | Corridas | % |
|---|---|---|
| alta | 161 | 21,8 |
| provável | 360 | 48,8 |
| ambíguo | 56 | 7,6 |
| sem correspondência | 161 | 21,8 |
Trechos: 1.523 (13.660 km): 28,0% (59,0% do km) ligados a corrida A; 7,5% (10,9%) ambíguos; 1,3% (1,0%) a compromisso externo; **63,3% dos trechos (29,1% do km) sem finalidade identificada**. 77 corridas usam vários trechos; 102 trechos cobrem várias corridas (muitos-para-muitos preservado). Cobertura por veículo: 17 de 114 placas sem nenhum vínculo; mediana 80% das corridas ligadas. Sensibilidade (folga 60–300 s × destino 200–1000 m): alta 14,8–22,5%; provável 44–55%; sem correspondência constante em 21,8%; km ligado 57–64%. Inspeção: `data/processed/run_outputs/conciliacao_amostra_*.csv` (15 por classe, pseudônimos) — **a inspeção manual ainda não foi feita por mim**.
Limites: sem horário real de embarque/desembarque (usa `DT_INICIO/FIM_REALIZADA`), sem trajetória, ponte placa por foto atual. Nenhuma distância foi rateada por tempo.

### 8. Componentes de KM (10/03; sem subtração entre fontes)
| Componente | km | Natureza |
|---|---|---|
| Cobli, trechos ligados a corrida A | 8.057,7 | medido por trecho (inclui aproximação/ociosidade do trecho) |
| Cobli, ambíguos | 1.491,6 | medido, não atribuível |
| Cobli, compromisso externo | 133,9 | medido, outro produto |
| Cobli, finalidade desconhecida | 3.976,9 | **quilometragem não conciliada** |
| App, passageiro (`NU_DISTPERCORRIDA`) | 8.303,1 | reportado (fonte distinta) |
| App, aproximação (`NU_DISTANCIA_ACEITE_CHEGUEI`) | 3.246,1 | reportado; 42,6% nulo |
| KM morto total / reposicionamento / circulação e retorno | — | **não identificáveis** só com estas fontes |
Mensurável: pickup reportado (parcial) e trecho com passageiro. Dependem do simulador: reposicionamento e KM vazio contrafactual. Só inferível por telemetria sem vínculo: circulação e retorno. O DW tem `FT_KM_RODADO` (`KM_BUSCAR_PASSAGEIRO_PF/PJ`, `KM_REPOSICIONAMENTO`, `KM_RODADO`) e `FT_OFERTA_KM_RODADO`: **só os nomes das colunas foram lidos**; método e cobertura não verificados.

### 9. DW e STG
Delimitação possível por conjuntos de ID confirmados: `FT_FATURAMENTO_VIAGEM` (745 linhas, uma por corrida faturada, para os 1.325 ids V1 de 10/03: filtro por `CD_SOLICITACAO` funciona; 745 ≠ 738 encerradas, a diferença não foi investigada), `FT_COBLI_MOTOR_OCIOSO_VIAGENS` e `FT_JORNADA` (têm `CD_SOLICITACAO`), `FT_SOLICITACAO` (`CD_JORNADA_MOTORISTA`; a coluna de solicitação tem outro nome), `FT_OFERTA_KM_RODADO` (`codigoSolicitacao`), `FT_KM_RODADO` (placa). A contagem em `FT_OFERTA_KM_RODADO`, a concordância de placa do DW e o STG **não foram concluídas** (consulta pesada interrompida por mim). **Nada do DW/STG foi extraído**; metadados inspecionados ≠ dados extraídos.

### 10. Período
Calendário documentado: calibração 02–15/03, teste 16–31/03, setembro 16–30/09. **Conflito:** esses dias de teste já foram consultados várias vezes (`V2_PREREGISTRO.md` §12), logo não são "teste independente intocado" para um guloso reconstruído (R-01 aberta). Extraído até agora: 07, 10, 13, 17/03 (verificação), sem lote completo. **Proposta:** treino/histórico 01/02–15/03; validação 16–31/03 (declarada como já consultada); teste independente intocado 01–25/10 (mês ainda não usado, com D+1 completo); setembro como replicação. Pergunta única no fim deste documento.

### 11. Correções às afirmações de 06/11
Jornada = 0 era defeito de coorte, não ausência de dado; Cobli UTC (janela de extração e "resíduo 14%" foram afetados); grupo "Operação" não é só V1; `VIX CAM` tem 4/5 placas V1; o resíduo de KM não é KM morto; "14/14 solicitações" para o fuso foi substituído por 2.300+ eventos.

### 12. Critérios para avançar
| Pergunta | Resposta (nível) |
|---|---|
| Identificamos a demanda V1? | **Sim** para solicitações (executado, 4 dias); `dt_registro` segue proxy; agendadas e demanda suprimida fora |
| Veículos elegíveis? | **Parcial**: observados sim (placa↔corrida); vigência histórica de grupo/região não extraída |
| Disponibilidade e compromissos externos? | **Parcial**: B extraído (só o registrado, 10/03); jornada registrada; sem escala |
| Estados para a simulação? | **Parcial**: posições ES ~2 min (observadas); início/fim de corrida (observados); entre fotos (inferido); pós-ação (simulado) |
| KM morto mensurável? | pickup reportado e trecho com passageiro; o resto, não |
| Hipóteses necessárias | regime de escala (B), repouso no destino, circulação ausente, fator rua/reta, RN024 fora do ES/ODS/Cobli |

#### Cenários (classificação)
| Cenário | Classe | Razão |
|---|---|---|
| **Referência: espera no destino** (veículo fica onde terminou, despacho ao mais próximo) | **A** | só usa solicitações, ofertas e compromissos; é o baseline já calibrado (simplificado) |
| Referência + circulação observada pela Cobli | B | exige tratar trechos sem finalidade como hipótese (sensibilidade) |
| Reposicionamento D+1 de poucas alternativas justificadas (hotspot por hora) | B | exige regime de escala, conformidade e disponibilidade incerta (sensibilidade) |
| Comparação com a operação manual real / reposicionamento operado | **C** | sem política documentada; `reposicionamento` ODS/ES têm semântica pendente |
| Medição de KM morto observado ponta a ponta | **C** | circulação/retorno não separáveis; `FT_KM_RODADO` não verificado |
| Cenário com Prime ou outros produtos | **C** (fora de escopo) | não é objeto do TCC |
Não é demonstração de que o guloso funciona; é a base para escolher e avaliar a política.

### 13. Bloqueios restantes
1. Confirmação da empresa: RN024, significado de "Operação V1 VIX CAM", política de despacho, escala conhecida na véspera.
2. Pergunta de período (§10); sem ela, nada além dos 4 dias foi extraído.
3. Inspeção manual da amostra de vínculos e dos sem correspondência.
4. DW/STG: método de `FT_KM_RODADO` e `FT_OFERTA_KM_RODADO`.
5. Vigência histórica por veículo (região/serviço/grupo) e agenda de Aluguel/manutenção.


## Cobli × corridas V1: por que 21,8% de "alta" virou 1 em 2.749 (08/11/2026)

_Origem: `docs/data_quality.md`._

**Conclusão (executada):** foi **erro meu na inspeção**, não mudança de dados, regras ou população. `scripts/inspecionar_vinculos_cobli.py`† chamou a conciliação com o relógio Cobli **sem converter UTC→local** (padrão `deslocamento_cobli_s=0`), enquanto o relatório anterior usava `--desloc-cobli-s -10800`. Corrigido: `preparar()` converte explicitamente (`analise/tempo.py::para_local(..., "cobli")`); a nova execução reproduz **exatamente** os JSON anteriores nos 4 dias (comparação programática: `True` ×4; originais preservados em `reports/data_quality/v1_viagens_extraction/anterior_desloc_manual/`).

### Tabela de reconciliação

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

### Camadas de verificação (não confundir)
1. **Verificação automática** (feita): `inspecionar_vinculos_cobli.py`, 125 corridas estratificadas (classe × contexto), semente 20261108, recomputa sobreposição bruta e distância de borda a partir dos registros; 0 erros pelo critério fixado antes. Mede **consistência com as regras implementadas**, com o mesmo relógio e placa; não é confirmação independente.
2. **Revisão técnica de casos com evidência** (pendente): requer leitura caso a caso da amostra em `data/processed/data_quality_samples/inspecao_vinculos_cobli.csv`; ainda não feita.
3. **Confirmação operacional** (pendente, depende de quem conhece o processo): se um trecho Cobli é a mesma operação da corrida.

### Uso permitido
Com a evidência atual a Cobli **não** é verdade de referência para validar km morto. Pode apoiar diagnósticos específicos (por exemplo, fração de km sem finalidade identificada) com as limitações declaradas: trechos são contêineres, relógio UTC inferido por evidência (RN024 pendente), 18,1% das corridas sem correspondência.

### Consolidação (registro de 08/11/2026)
**Resultado inválido, SUBSTITUÍDO:** "1 `alta` em 2.749 corridas" (1 / 600 / 547 / 1.601) e a amostra de 106 corridas daquela execução. Causa: o script de inspeção não convertia UTC→local. O arquivo `reports/data_quality/v1_viagens_extraction/inspecao_vinculos_cobli.json` foi regravado com a execução corrigida; os números inválidos ficam registrados somente aqui. Não devem ser citados.

**Resultado corrigido (fonte: lotes do esquema 1 em `data/raw/v1_viagens_schema1_20261108/`, 4 dias, mesma regra):**

| Dia | Corridas (denominador) | alta | provável | ambíguo | sem correspondência |
|---|---|---|---|---|---|
| 07/03 | 512 | 87 | 304 | 20 | 101 |
| 10/03 | 738 | 161 | 360 | 56 | 161 |
| 13/03 | 810 | 145 | 461 | 59 | 145 |
| 17/03 | 689 | 187 | 352 | 59 | 91 |
| **Total** | **2.749** | **580 (21,1%)** | **1.477 (53,7%)** | **194 (7,1%)** | **498 (18,1%)** |

Denominador: corridas `CorridaEncerrada` com início e fim realizados e placa na ponte `APP_VEICULO.TX_PLACA` (solicitações V1 da região, sem Prime). Os dias 07, 10 e 13 são de treino e 17 é de validação; nenhum parâmetro foi ajustado com eles.

**Teste de regressão do erro:** `tests/unit/test_conciliacao_fuso.py`† (corrida diurna e corrida que cruza 23:50→00:10; com conversão vincula, sem conversão não vincula).

**Alcance:** a reprodução dos JSON anteriores mostra consistência entre execuções do mesmo código e dados. Não mostra que cada correspondência seja a mesma operação real (verificação automática ≠ revisão técnica ≠ confirmação operacional). Após o esquema 2, os dias 07, 10 e 13 serão reconciliados de novo sobre os lotes novos como checagem de consistência.


## Plano de extração: de onde vêm os 211 dias (08/11/2026)

_Origem: `docs/data_quality.md`._

**211 não é a soma de combinações entidade–dia nem duplicação.** É o número de dias de calendário **distintos** da entidade `solicitacao` (e de `status_solicitacao`): os 99 dias dos períodos aprovados mais 112 dias de **histórico de aquecimento** necessário ao método existente (`lookback_days=56` para previsão de demanda). Antes eu mostrei esse 211 sem rotulá-lo; a unidade correta é "dias distintos por entidade".

### Períodos aprovados (99 dias distintos)
| Finalidade | Intervalo | Dias |
|---|---|---|
| Treino | 01/02–15/03/2026 | 43 |
| Validação | 16/03–31/03/2026 | 16 |
| Replicação | 16/09–30/09/2026 | 15 |
| Avaliação final reservada (só integridade) | 01/10–25/10/2026 | 25 |

### Aquecimento (112 dias; justificativa: janela de 56 dias anteriores ao primeiro dia-alvo)
| Finalidade | Intervalo | Dias | Entidades |
|---|---|---|---|
| Histórico do treino (1º alvo 01/02) | 07/12/2025–31/01/2026 | 56 | solicitacao, status_solicitacao |
| Histórico da replicação (1º alvo 16/09; cobre também 01/10, que precisa de 06/08) | 22/07–15/09/2026 | 56 | solicitacao, status_solicitacao |

Contigüidade: 56 + 43 + 16 = 115 dias (07/12–31/03) e 56 + 15 + 25 = 96 dias (22/07–25/10); 115 + 96 = **211**. Os dias 01/04–21/07 não são extraídos. Setembro e outubro não são usados para ajustar método.

### Tabela por entidade (dias distintos esperados)
| Entidade | Intervalos | Dias | Finalidade |
|---|---|---|---|
| ods/solicitacao, ods/status_solicitacao | 07/12/25–31/03/26; 22/07–25/10/26 | 211 cada | demanda (incl. não atendidas) e histórico |
| ods/veiculo | snapshot | 1 | ponte código→placa |
| ods/veiculo_condutor, jornada_motorista, log_status_motorista | 99 dias aprovados | 99 cada | vínculos, jornada, disponibilidade |
| ods/reposicionamento, compromissos_externos, telemetria_cobli (com vehicle_group) | 99 dias aprovados | 99 cada | KM/ações de reposicionamento, compromissos, diagnóstico Cobli |
| es/posicao_ofertas | 04/01–31/03/26; 19/08–25/10/26 | 87 + 68 = 155 | posições da frota (histórico de 28 d, `fleet._comparable_days`) |
| es/sumario_ofertas, es/reposicionamento_sugerido | 99 dias aprovados | 99 cada | contexto de oferta e sugestões |

Soma: 1.017 lotes ODS-dia + 353 ES-dia (`2×211 + 1 + 6×99` e `155 + 2×99`); antes do ajuste de ES eram 381.

### Excedente preservado
`es/posicao_ofertas` de **07/12/2025 a 03/01/2026** (28 dias) foi extraído antes do ajuste e **não tem finalidade** com histórico de frota de 28 dias. Fica preservado (lotes válidos, esquema 2), fora do plano, e `scripts/cobertura_campanha.py`† os relata como `excedentes_preservados`.

### Concorrência (adotada)
Um único leitor ODS pesado por vez, na ordem: P0 fatia técnica de treino (07–13/03, todas as entidades) → P1 núcleo e vínculos do desenvolvimento (01/02–31/03) → P2 compromissos, reposicionamento e Cobli com `vehicle_group` → P3 aquecimento do treino → P4 replicação e avaliação final → P5 aquecimento 22/07–15/09. ES roda em fluxo próprio (outro sistema; ~2 s por dia, não é gargalo). Investigações complementares do DW só quando o ODS estiver ocioso. Cada lote grava duração, linhas e falhas em `data/raw/v1_viagens/LOG_LOTES.jsonl`; o tempo restante é estimado desses números, sem prometer prazo.
