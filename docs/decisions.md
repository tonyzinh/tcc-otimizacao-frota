# Registro de decisões

> Arquivo renomeado de `docs/REGISTRO_DECISOES.md` para `docs/decisions.md` em 09/11/2026. As entradas não foram reescritas: os caminhos citados nelas são os da época; o mapa antigo → novo está em `reports/manifests/repository_restructure/path_map.csv` e `code_rename_map.csv`.

Formato: **problema → evidência → alternativas → decisão e justificativa → impacto (código/TCC) → validação necessária.** Uma entrada por decisão; não reescreva entradas antigas, acrescente uma nova que as substitua. As decisões técnicas DT001–DT016 citadas em outros documentos viviam em `DECISOES_TECNICAS.md`, hoje ausente (ver `docs/DIAGNOSTICO_INICIAL.md`); não são reproduzidas aqui. Os desvios D1–D13 da extensão v2 estão em `docs_antigos/V2_PREREGISTRO.md` §12.

## R-01 · Reconstruir o guloso × "última tentativa" (06/11/2026) · ABERTA

- **Problema:** pedido de 06/11 prevê reconstruir o guloso a partir de formulação e dados; em 16/10 o proprietário declarou o seletivo C2 (0 movimentos no teste) a última tentativa.
- **Evidência:** memória do projeto (`guloso-seletivo-resultado`); `docs_antigos/RESULTADO_SELETIVO.md`; `reports/tcc_v2/RELATORIO_V2.md`.
- **Alternativas:** (a) manter só o protocolo de avaliação e a regra NB(e\*), sem novo algoritmo; (b) reconstruir o guloso com escopo e critérios fixados antes de qualquer execução.
- **Decisão provisória:** nenhuma implementação até o proprietário confirmar (b) e o escopo. A auditoria de formulação (somente leitura) pode andar.
- **Impacto:** se (b), muda objetivos e hipóteses do TCC; se (a), o texto segue `TCC_REFORMULACAO.md`.
- **Validação:** protocolo congelado antes do teste, teste independente intocado.

## R-02 · Premissa de frota e de quem paga o KM vazio (06/11/2026) · ABERTA

- **Problema:** o pedido fala em "frota própria"; a decisão D-A (28/10) supõe empresa que paga o KM e motorista com conformidade c; o parecer A3 aponta que os dados falam de motoristas que aceitam corridas.
- **Evidência:** `TCC_REFORMULACAO.md` §1; `TCC_PARECER_ORIENTADOR.md` A3; ausência de campo CLT/PJ nos dados brutos.
- **Decisão provisória:** manter D-A como premissa de trabalho **declarada e condicional**; resultados descritos como condicionais a ela.
- **Validação:** confirmação do proprietário ou da empresa; definir em uma passagem na introdução.

## R-03 · Instruções persistentes reorganizadas (06/11/2026) · DECIDIDA

- **Problema:** as quatro regras antigas citavam fontes ausentes e misturavam estado com regra; faltavam regras de rigor, dados/temporalidade, otimização, simulação e escrita.
- **Evidência:** `.claude/rules-legado/`; documentação do Claude Code (regras em `.claude/rules/` carregam no início; `paths:` condiciona; outras pastas não carregam).
- **Decisão:** `CLAUDE.md` conciso + seis regras novas; regras antigas movidas (não apagadas) para `.claude/rules-legado/`; estado mutável apenas em `docs/`. `AGENTS.md` mantido e importado.
- **Impacto:** nenhum no código ou nos resultados.
- **Validação:** abrir nova sessão e confirmar que as regras aparecem no contexto; revisar se as skills antigas devem ser atualizadas.

## R-04 · Delimitação da operação V1 Viagens nas fontes (06/11/2026) · PROPOSTA (aguarda aprovação)

- **Problema:** todo o trabalho de dados vale só para a operação V1 Viagens (nome da operação, não a "v1" do algoritmo). As views do DW divergem: `VW_FROTA_VIAGENS` e `VW_PLACAS_ATIVAS_MES_VIAGENS` usam `APP_VEICULO.CD_REGIAO IN (1,4)`; `VW_VEICULOS_V1` usa `NOT IN (3,5)` e rotula 3 e 5 como Aluguel.
- **Evidência (ODS, leitura local agregada, 06/11/2026):**
  - `APP_REGIAO.TX_PRODUTO`: `V1` nas regiões 1, 2, 4, 6, 7, 11, 12, 14–19; `FastRental` nas regiões 3, 5, 8, 9, 10, 13. O produto está em campo próprio; nome da tabela ou do índice não foi usado.
  - `APP_TIPO_SERVICO`: serviços V1 = 1 (V1 PADRÃO), 11 (V1 COM RETORNO), 12 (V1 INTRAMUNICIPAL), 19 (V1 Padrão II, PJ); os demais são grupos de locação (GRUPO B…LX).
  - `APP_SOLICITACAO_HIST` em mar/2026 (solicitações distintas): região 1 serviço 1 = 40.899 e serviço 12 = 1.679; região 4 = 932 + 715 (Macaé); região 14 = 725 (Mauá); região 2 = 8. Nenhuma solicitação de região FastRental no mês.
  - `APP_VEICULO` região 3 tem 12.123 ativos (locação), logo `NOT IN (3,5)` seria seguro para o histórico de março, mas inclui Macaé, Mauá e Guarapari, fora da Grande Vitória.
  - `APP_SOLICITACAO_HIST` no ODS tem 6.446.410 linhas e 6.446.410 solicitações distintas (uma linha por solicitação, ao contrário do que a documentação de regras descreve para a versão com transições); a fonte de transições precisa ser confirmada (STG/log de status).
- **Alternativas:** (a) `CD_REGIAO IN (1,4)` das views; (b) `NOT IN (3,5)`; (c) `TX_PRODUTO='V1'` ∩ `CD_REGIAO=1` (Grande Vitória, escopo do TCC), serviços 1/11/12/19.
- **Decisão proposta:** (c), com região 1 (a região do TCC) e serviços V1. Macaé (4) e demais cidades ficam fora; Prime fica fora até confirmação. Fontes sem região/serviço (telemetria, ofertas) entram só via junção por solicitação/veículo/motorista já filtrados, com vínculo vigente na data.
- **Impacto:** define o filtro de todos os extratores; nada foi extraído para arquivo ainda.
- **Validação necessária:** aprovação do proprietário; conferir que veículos/motoristas da região 1 não circulam em outra operação na mesma data (vínculo temporal em `APP_VEICULO_HISTORICO`/`APP_VEICULO_CONDUTOR`).

## R-05 · Prime fora e uso da Cobli (06/11/2026) · DECIDIDA (Prime) / ABERTA (Cobli)

- **Problema:** R-04 deixou Prime fora, mas a V1 PADRÃO (serviço 1) na região 1 contém solicitações Prime; o proprietário pediu investigar a Cobli.
- **Evidência (10/03/2026):** 127 de 1.452 solicitações têm `TX_MODELO_SOLICITACAO='Prime'`; resíduo de KM Cobli × corridas passou de 257 km para 1.922 km ao excluí-las, logo os veículos do grupo Cobli "Operação" também atendem Prime; 14 de 16 placas do grupo "Operação Prime" tinham corrida V1 região 1 no dia.
- **Decisão:** excluir `TX_MODELO_SOLICITACAO='Prime'` nas solicitações; Cobli entra pelo grupo "Operação", com a limitação declarada. Aberto: separar Prime × Normal por viagem Cobli e decidir sobre "Operação V1 VIX CAM".
- **Impacto:** extratores (`tcc_frota.extracao`); `docs/DADOS_V1_VIAGENS.md`.
- **Validação necessária:** casamento viagem a viagem Cobli × solicitação em mais de um dia, incluindo setembro.

## R-06 · Sal de pseudonimização recriado (06/11/2026) · DECIDIDA

- **Problema:** `data/.pseudo_salt` e `data/raw/` desapareceram durante a sessão (mesmo padrão de sumiço de arquivos ignorados já visto); o piloto de 10/03 tinha usado o sal anterior.
- **Decisão:** gerar novo sal local (ignorado pelo git) e regravar o piloto com `--forcar`; os pseudônimos anteriores deixaram de existir. **Faça cópia segura do sal** antes da extração do período: sem ele, lotes antigos e novos não se juntam.
- **Impacto:** nenhum resultado congelado usa estes pseudônimos.

## R-07 · Pseudonimização estável e guarda do segredo (08/11/2026) · DECIDIDA (implementada e testada)

- **Problema:** o sal sumiu em 06/11 e foi recriado; nada impedia continuar uma campanha com segredo diferente nem garantia que a mesma entidade gerasse o mesmo pseudônimo nas fontes (placa Cobli com espaço à direita em 2,2% das linhas).
- **Evidência:** `docs/PSEUDONIMIZACAO_E_VINCULOS.md` (interseções de IDs entre fontes; lixeira do Windows).
- **Alternativas:** manter `sha256(sal:valor)` com sal em `data/`; HMAC com segredo protegido, namespace por entidade e versão registrada.
- **Decisão:** esquema `hmac-sha256-v1`; segredo em `%LOCALAPPDATA%\tcc_frota\segredos`, cópia em `%USERPROFILE%\.tcc_frota_backup`; `chave_id` nos manifestos e em `PSEUDONIMIZACAO.json`; segredo ausente/diferente interrompe; nenhum segredo é criado se há dados dependentes. O valor do sal de 06/11 foi mantido (migração sem alteração), pois era o único com dados vivos.
- **Impacto:** piloto regravado; lotes antigos movidos (não apagados) para `data/extraido/v1_viagens_legado_sal_20261106/`. `v2/rules.py` e `data/.pseudo_salt` não foram alterados (pipeline v2).
- **Validação:** 17 testes novos (unitários e de integração); `status` da CLI.

## R-08 · Sumiço de `data/raw` e do sal: causa não determinada (08/11/2026) · REGISTRADA

- **Evidência:** itens na lixeira com data/hora (06/11 21:37 UTC), sem script do repositório que os remova; a lixeira não identifica o processo.
- **Decisão:** não atribuir causa. Material recuperável da lixeira; restauração depende do proprietário (`raw` 348 MB, sal original).
- **Risco aberto:** repositório sob OneDrive (dados e sal sincronizados); `data/.pseudo_salt` ainda existe para o v2.

## R-09 · Jornada vazia: família de ID diferente (08/11/2026) · CORRIGIDA

- **Problema:** `ods/jornada_motorista` retornou 0 linhas em 10/03.
- **Evidência (executada):** a origem tem 191 jornadas e 168 motoristas em 10/03 (500.319 linhas no total, 2.140 pessoas); `APP_JORNADA_MOTORISTA.CD_MOTORISTA` tem **0** de 129 em comum com o motorista das solicitações e **167 de 168** em comum com `APP_VEICULO_CONDUTOR.CD_CONDUTOR`. A coorte por solicitação nunca poderia casar.
- **Decisão:** coorte pela ponte veículo→condutor (`APP_VEICULO_CONDUTOR`), nova entidade `veiculo_condutor` (vigência) e `cd_veiculo_condutor` no log de status. Resultado: 161 jornadas extraídas (1 rejeitada). Nomeada "jornada registrada": não é escala nem disponibilidade.
- **Aberto:** o rótulo "motorista" na jornada é, na verdade, condutor; condutor de veículo compartilhado entra na coorte.

## R-10 · Relógio da Cobli é UTC; ODS e ES são locais (08/11/2026) · CONFIRMADA EM 1 DIA, VERIFICAR EM OUTROS

- **Evidência (executada, 10/03/2026):** (a) ES `passageiroEmbarcado` (primeira foto) vs `DT_INICIO_REALIZADA` do ODS em 597 corridas: mediana +1,0 min (p5 0,1; p95 1,9); sob a hipótese "ODS em UTC" seria +181 min ⇒ ODS = hora local; (b) conciliação por placa: corridas sem par 60,6% (sem deslocamento) → **27,1% com Cobli −3 h** → 73,9% com +3 h; mediana de 61 m entre fim do trecho e destino quando as bordas coincidem. ⇒ Cobli = UTC. (c) ponte placa: 598 de 598 concordam com a placa vista pelo ES.
- **Decisão:** não aplicar deslocamento global. A extração da Cobli passa a consultar o **dia local** (janela +3 h) e guarda o horário na hora da fonte (UTC); o deslocamento é parâmetro explícito da conciliação. RN024 segue **pendente de confirmação da empresa** para os demais campos.
- **Defeito encontrado:** o piloto cortava a Cobli pelo dia UTC; corridas após 21h locais tinham 82–100% sem par.

## R-11 · Demanda-alvo × compromissos externos × movimentos sem finalidade (08/11/2026) · DECIDIDA

- **Decisão:** A) demanda e resultados = V1 Viagens, região 1, serviços 1/11/12/19, **sem Prime**; B) `compromissos_externos`: corridas de veículos que atenderam V1 em ±7 dias que não são V1-sem-Prime (`prime`, `outro_servico`, `outra_regiao`), só veículo pseudonimizado, categoria e tempo, usados **apenas** para bloquear o veículo; C) trechos Cobli sem vínculo: `finalidade_desconhecida`. Prime nunca entra no KM vazio nem na demanda.
- **Evidência:** 10/03: 98 compromissos externos extraídos; 14 de 129 motoristas V1 do dia (10,9%) também fizeram Prime no dia.
- **Limite:** só cobre o que está em `APP_SOLICITACAO_HIST` (agendamento registrado há mais de 7 dias escapa; Aluguel/manutenção não aparecem).

## R-12 · Coortes de motoristas (08/11/2026) · REGISTRADA

Números de 10/03 em `docs/AVALIACAO_BASE_V1_VIAGENS.md` §4. A coorte ±7 dias é só retrospectiva e **não** pode alimentar o planejador D+1.


## R-13 · Períodos de treino, validação, replicação e avaliação final (08/11/2026) · DECIDIDA (pelo proprietário)
- **Problema:** definir janelas sem contaminar a avaliação final.
- **Decisão:** treino 01/02–15/03/2026; validação 16/03–31/03/2026; replicação temporal 16/09–30/09/2026; avaliação final reservada 01/10–25/10/2026.
- **Estado de independência (declarado com incerteza):** outubro é posterior ao desenvolvimento, mas **não é prospectivo** (estamos em novembro/2026). **Não há evidência identificada** de uso desse intervalo para ajustar método, mas isso **não comprova** ausência de consultas anteriores. Março foi usado para desenvolvimento (consultas de qualidade, inspeção de resultados e decisões de modelagem); setembro é **replicação do método congelado**: se seus resultados motivarem ajuste, passa a integrar o desenvolvimento e não será apresentado como confirmação independente.
- **Regra:** em outubro só integridade, schemas e cobertura. Nenhuma comparação de políticas para escolher algoritmo, parâmetro ou hipótese. Antes de avaliar outubro: congelar e registrar método e comparadores, parâmetros, hipóteses operacionais, métricas e critérios de sucesso, exclusões por qualidade, configuração e versão do código.
- **Aquecimento:** 07/12/2025–31/01/2026 (56 d antes de 01/02); 22/07–15/09/2026 (56 d antes de 16/09); posição de ofertas 28 d. Finalidade: histórico do método existente (`lookback_days=56`; frota 28 d), não resultado.

## R-14 · Semântica temporal: `available_at` removido (esquema 2) (08/11/2026) · CORRIGIDA
- **Evidência (executada, 4 dias, ES `posicao_ofertas`):** `dataAtualizacao` precede `dataHora` em quase todas as linhas (mediana −2,7 s; p1 ≈ −8 min): é o carimbo do último GPS, não a entrega. `ingested_at` = momento da extração local (~235 dias depois). ODS `dt_registro_atualizacao` mediana ~24 min, p90 ~21 h: última atualização do registro, não atraso de ingestão.
- **Decisão:** esquema 2: `known_at` (nulo = desconhecido), `extraido_em`, `gps_observado_em`, `ultima_atualizacao_em`, `event_time`. Hipótese de acesso da simulação em `config/hipoteses_tempo.yaml` (evento + atraso, com cenários e idade máxima da posição). `max(evento, GPS)` **não** recupera disponibilidade e foi retirado. Lotes do esquema 1 preservados em `data/extraido/v1_viagens_esquema1_20261108/` (não combinar).
- **Validação pendente:** sensibilidade a atrasos plausíveis; campos atualizados depois não podem representar estado original.

## R-15 · Inspeção Cobli com relógio errado (08/11/2026) · CORRIGIDA
Ver `docs/RECONCILIACAO_COBLI_COMPARACAO.md`: "1 em 2.749" decorreu de o script de inspeção não converter UTC→local; corrigido, reproduz 21,1% (4 dias). Sem mudança de tolerâncias. Cobli não é verdade de referência.

## R-16 · Leitura ES: retentativa e PIT (08/11/2026) · IMPLEMENTADA E TESTADA
Retentativa (até 4) só para queda transitória, repetindo a mesma página (mesmo corpo/`search_after`: sem pular nem duplicar). Erro de certificado TLS: permanente, não repetido, validação mantida. PIT expirado (404 em `/_search`): `ElasticPitExpirado`, sem reabrir; o lote é refeito do zero com novo PIT (outro snapshot pode diferir; não se supõe identidade).

## R-17 · Condições iniciais da referência: observada × matriz (08/11/2026) · A IMPLEMENTADA / B PENDENTE
- **Definição do proprietário:** "matriz" = base física de onde os veículos sairiam no início da jornada. Isso **não comprova** que todos comecem nela.
- **Busca (executada):** regras e documentos do repositório (só citam "matriz de regras RN") e metadados do ODS por nome (`MATRIZ`, `GARAGEM`, `FILIAL`, `PONTO`, `LOCAL`): **nenhuma tabela de base física nem coordenadas**. Único indício: `APP_JORNADA_MOTORISTA.CD_LOCAL_FIM_TURNO` (código inteiro, sem tabela de coordenadas identificada). Nenhuma coordenada foi inventada.
- **Decisão:** duas condições separadas. A `primeira_posicao_observada` (idade máxima 1.800 s; posição anterior só vale sem viagem/compromisso entre ela e o início; sem observação até o início = intervalo inicial **desconhecido**, motorista indisponível ao despacho até a 1ª observação, perda quantificada; nunca posição futura para instante anterior; posição do dia-alvo inicializa o ambiente mas **não** é informação do planejador na véspera). B `matriz_configurada`: levanta `MatrizNaoDefinida` até haver coordenadas e fonte.
- **Bloqueia:** só a variante B. **Pergunta objetiva:** onde fica a base física (coordenadas) e todos os veículos partem dela? Ou o que significa `CD_LOCAL_FIM_TURNO`?

## R-18 · Plano de extração: 211 = dias distintos de demanda, não combinações (08/11/2026) · REGISTRADA
Ver `docs/PLANO_EXTRACAO_DIAS.md`: 99 dias aprovados + 112 de aquecimento (56 d antes de 01/02 e de 16/09). `es/posicao_ofertas` de 07/12/2025–03/01/2026 é excedente (histórico de frota é 28 d): preservado, fora do plano. Concorrência: um leitor ODS pesado por vez, em ordem de prioridade; a contenção entre três fluxos elevou a leitura de 7 dias de `solicitacao` de ~74 s (sozinho) para vários minutos.

## R-19 · Cobli: resultado "1 em 2.749" inválido (08/11/2026) · SUBSTITUÍDO
Ver `docs/RECONCILIACAO_COBLI_COMPARACAO.md` (tabela com denominadores, teste de regressão `tests/unit/test_conciliacao_fuso.py`).

## R-20 · Primeira comparação A × B em desenvolvimento, 10/03/2026, cenário J (08/11/2026) · EXECUTADA, 1 dia
**Evidência** (`reports/ab_desenvolvimento/ab_2026-03-10_J.json`, `scripts/executar_ab_desenvolvimento.py`): mesmo mundo (1.279 pedidos, 132 motoristas, compromissos comuns), parâmetros de simulação herdados de março, guloso com `ARTICLE_GREEDY` sem ajuste. A: 1.034 atendidos, KM vazio 2.499,4 (pickup, sem reposicionamento). B: 1.036 atendidos, KM vazio 2.514,3 (pickup 2.507,1 + reposicionamento 7,2); 15 movimentos planejados, 3 executados (5 motorista ausente, 7 fora do limite). **Resultado:** B não reduziu o KM vazio (+14,9 km; +2 atendidos). Um dia de desenvolvimento: não conclui sobre a hipótese, não é teste final, sem IC. Nenhuma variação foi tentada para mudar o resultado. Limitações: parâmetros não recalibrados para V1 Viagens; J usa jornada realizada; escala de D+1 por persistência (hipótese).

## R-21 · Compromissos externos: deslocamento explícito; definição das políticas A e B (08/11/2026) · IMPLEMENTADA
**Comportamento confirmado (código `v2/sim.py` antes da correção):** ao iniciar um compromisso o motorista passava a ocupado até o fim e, no fim, assumia a posição final do compromisso; a **origem** nunca era usada. Logo a posição mudava do ponto em que o motorista estava para a origem do compromisso **sem tempo nem distância** (teletransporte), e o simulador aceitava uma corrida que terminasse antes do início do compromisso mesmo sem tempo hábil de chegar. `auditar_compromissos` só contava os casos (campo `inviaveis`), não os classificava como violação; "sem violações" não os cobria.
**Correção (opt-in, resultados congelados intactos):** `simulate(..., commit_origins=...)`. Uma tarefa só é aceita se, ao terminar, houver tempo de ir da posição final até a origem do compromisso seguinte (distância por rua estimada ÷ velocidade). Ao iniciar o compromisso o motorista parte de onde ficou livre e o km dessa aproximação é registrado (`commit_approach_km`), **fora do KM vazio comparado** e reportado como componente separado (varia entre políticas). Posição e vínculo acompanham o motorista (compromisso atribuído por placa → motorista do dia).
**Classes:** A inconsistência de entrada (a folga já era insuficiente desde a posição de entrada: sessão ou compromisso anterior; compromisso mantido no horário histórico, déficit registrado); B violação causada pela política (tarefa simulada impede chegar; entra em `auditar` como violação; deve ser 0); C limitação assumida (origem ou posição desconhecida: sem deslocamento modelado, marcado incerto). Compromissos ainda são conhecidos pelo despacho desde o início (known_at desconhecido).
**Políticas:** A = espera no destino = `espera_no_destino.rodar` = `simulate(moves={})`; o A×B (`executar_ab`) chama exatamente essa função (teste de equivalência). B = guloso existente (`GulosoMarginal`, `ARTICLE_GREEDY`), mesmo mundo, despacho, disponibilidade, compromissos, condição inicial `primeira_posicao_observada` e contabilidade de km. `matriz_configurada` é outra condição inicial, não política, e não bloqueia a comparação.

## R-22 · A×B em 59 dias de desenvolvimento, modelo de compromissos corrigido (08/11/2026) · EXECUTADA, DIAGNÓSTICO
**Escopo:** cenário J, 01/02–31/03/2026 (43 dias de treino e 16 de validação), todos elegíveis pela regra fixada antes das políticas (≥300 snapshots ES no alvo e em D, ≥200 pedidos TempoReal, ≥28 dias de histórico; `reports/ab_desenvolvimento_v2/elegibilidade_dias.json`: 59 de 59). Nenhum parâmetro foi ajustado; a validação **não** foi usada para escolher configuração. Outubro intocado. Artefatos: `reports/ab_desenvolvimento_v2/` (diário, agregado); tabela individual em `reports/runs/` (ignorada).
**10/03 repetido:** execução anterior preservada em `reports/ab_desenvolvimento/`. Mudanças que afetam o resultado: (1) deslocamento até a origem do compromisso (A: 1.034→1.014 atendidos; km 2.499,4→2.477,6); (2) corte do planejador com `atraso_base_s` (15→13 movimentos planejados). Nova: A 1.014 atendidos/2.477,6 km; B 1.019/2.537,4 (pickup 2.529,8 + reposicionamento 7,6); 3 de 13 movimentos executados.
**Agregado (59 dias):** km vazio A 123.841,7; B 124.116,5 (+0,22%); diferença diária média +4,66 km (IC95 bootstrap de dias −7,2 a +17,1; 32 dias B pior); atendidos 49.916 vs 49.920; espera mediana sem diferença detectável. Movimentos: 883 planejados, 219 executados (24,8%): ausente 197, fora do limite 454, ocupado 13. Descritivo; sem correção para comparações múltiplas e sem poder calculado; **não demonstra redução**, nem prova ausência de efeito (inconclusivo com 25% de adesão).
**Diagnóstico da baixa execução:** (a) escala persistente: 78,9% dos motoristas planejados aparecem em D+1; (b) 454 "limit": planejador e executor usam o mesmo limite (3 km), unidade e método (Haversine × fator), mas medem posições diferentes — a última posição de D até o corte × a primeira posição de D+1; o deslocamento mediano entre as duas é 11,6 km nesses casos (422 de 454 acima de 3 km); (c) os executados partiram de posições quase iguais (mediana 0,22 km). Diagnóstico independente do plano (4.392 pares motorista-dia, só dados disponíveis no corte): a primeira posição de D prevê a primeira de D+1 com mediana 0,05 km (73% ≤3 km); a última posição de D até o corte, com 2,54 km (52% ≤3 km).
**Compromissos nos 59 dias:** classe B (causada pela política) 0; classe A (entrada inconsistente) 60; classe C (incerta) 66. Aproximação a compromissos (fora do KM vazio comparado): A 13.178 km; B 13.416 km (diferença de +238 km, da mesma ordem e direção que os +275 km do KM vazio principal; não somada ao KM vazio por decisão de definição, mas relevante para interpretar o efeito do reposicionamento).
**Próxima alteração recomendada (uma só):** corrigir a incompatibilidade de posição do planejador, usando como posição prevista de D+1 a primeira posição observada de D (disponível no corte), não a última. Resolve a falha "posição prevista ≠ posição de execução"; não muda algoritmo nem acrescenta informação futura. Testar primeiro em treino, comparar com esta linha de base e registrar. Reposicionamento durante a operação mudaria o momento da decisão em relação ao D+1 e exigiria revisão de escopo: não proposto.
**Regra experimental para o atendimento (a fixar antes da avaliação final; hoje sem SLA):** reportar separadamente km, atendidos e espera; considerar o serviço preservado se a diferença diária média de atendidos tiver IC95 de bootstrap de dias contido em ±1% dos pedidos do dia e a espera mediana não aumentar além de 30 s no IC superior. Margens propostas por conveniência e sem evidência empírica; precisam de aprovação do proprietário antes de valerem.

## R-23 · MUDANÇA DE ESCOPO: estudo exclusivamente sintético na Grande Vitória (08/11/2026) · DECIDIDA PELO PROPRIETÁRIO
**Problema:** a base real V1 Viagens (cobertura parcial do feed, presença ≠ disponibilidade, 25% de adesão das recomendações por divergência de posição, compromissos externos) limita o que a simulação pode afirmar. **Decisão (pedido do proprietário):** o experimento principal passa a usar **somente dados operacionais sintéticos** (frota, jornadas, demanda) sobre geografia pública da Grande Vitória (ES). Pergunta: *em quais condições de distribuição espacial e temporal da demanda um guloso de reposicionamento preventivo reduz o km vazio, em comparação com a espera no destino?* **Fora do escopo agora:** novas extrações (DW, ODS, STG, Elasticsearch, Cobli), qualquer calibração com estatísticas dos dados privados, e a campanha de comparação de vários algoritmos (`docs/PLANO_COMPARACAO_ALGORITMOS.md` fica arquivado como etapa exploratória; o grupo B e os métodos de busca/tabu/recozimento/fluxo/Húngaro permanecem implementados e testados, sem campanha).
**Interrupção segura (executada em 08/11/2026):** nenhuma extração estava ativa (a campanha terminou); encerrados os processos de comparação em andamento; lotes, relatórios, segredos e resultados preservados (`data/extraido/`, `reports/`). **Parcial preservado e NÃO usado:** `reports/comparacao/grupo_B/treino` (43 dias) e `grupo_A/treino_etapa1` (19 dias), incompletos, sem conclusão.
**Estado arquivado (etapa exploratória real, sem integrar o experimento principal):** extração V1 Viagens (R-13 a R-19), A×B de desenvolvimento nos dados reais (R-20 a R-22: guloso sem redução; adesão 24,8%), módulos `referencia/`, `comparacao/`. Esses resultados seguem válidos apenas como diagnóstico do que a base real permitia.
**Impacto:** o novo fluxo (`src/tcc_frota/sintetico/`) não usa credenciais, `data/raw/`, `data/extraido/` nem o segredo de pseudonimização; roda só com a geografia pública baixada (manifesto com fonte, data, licença e hash). Validade externa para empresa real: não demonstrada. Texto do TCC: proposta de adequação entregue à parte; nada reescrito sem aprovação.

## R-24 · Desenvolvimento sintético: guloso pior que a espera no destino (08/11/2026) · EXECUTADO, DIAGNÓSTICO (sementes 101–120)
**Evidência** (`reports/sintetico/desenvolvimento/analise/resumo_por_cenario.csv`, 22 cenários × 20 sementes, mundo pequeno de grade validado por `tests/unit/test_sintetico.py`): Δ km vazio (B − A) médio positivo em 21 de 22 cenários (S1 +53,9 km, +2,3%; S2 +39,3; S3 +26,9; S4 +41,5; S5 +55,4; IC95 bootstrap sobre sementes acima de 0 em todos esses); `S3_res6` sem diferença detectável. Salto máximo maior piora (S2 6 km: +144,8; 10 km: +193,5; S3 10 km: +474,8, com mais atendidos, razão 1,12). Previsão perfeita (diagnóstico idealizado) também piora. Atendimento ≈ preservado nos cenários com salto de 3 km.
**Mecanismo:** o reposicionamento custa ≈ 30–60 km por dia (17–21 movimentos), e a redução de km de busca é de 0 a 9 km (aumenta em alguns cenários porque mais corridas são atendidas). Coerência: `km_modelo` = km de reposicionamento simulado (S2/101: 49,3 km), movimentos planejados = executados, assinatura de A = B. O ganho do modelo (≈ 25–28) é em corridas esperadas, não em km: o objetivo do guloso é cobertura esperada − α·km, não km vazio.
**Decisão:** nenhuma alteração do guloso, de α, ρ, salto ou previsão após ver os resultados; matriz congelada (hash em `docs/PLANO_EXPERIMENTO_SINTETICO.md` §9) e avaliação reservada (9001–9040) executada uma única vez. Resultado negativo é resultado.
**Validação necessária:** relatar a avaliação reservada; inspecionar casos (`scripts/inspecionar_mecanismo_sintetico.py`); a hipótese de que o desalinhamento objetivo (cobertura) × desfecho (km vazio) explica o resultado é **hipótese**, não testada por ablação.
**Avaliação reservada (executada uma vez, 9001–9040, 880 pares):** 21 de 22 cenários `piora` (IC95% > 0), 1 `sem_diferenca_detectavel` (`S3_res6`); nenhuma redução. S1 +48,9 km (+2,1%), S2 +69,0, S3 +37,8, S4 +59,3, S5 +67,3. Confirma o desenvolvimento. Relatório: `reports/sintetico/RELATORIO_SINTETICO.md`.

## R-25 · Nova orientação (09/11/2026): duas linhas (real histórica e sintética), grupos R e D · DECIDIDA PELO PROPRIETÁRIO, EM EXECUÇÃO
**Substitui** a decisão de R-23 de usar só dados sintéticos; R-23 permanece como registro histórico e a linha sintética continua. **Pedido:** comparar Húngaro, busca local, tabu, recozimento e fluxo de custo mínimo com o guloso e "não reposicionar" como referências, em (A) avaliação contrafactual por simulação com entradas históricas da V1 Viagens e (B) avaliação em cenários sintéticos. Resultados das duas linhas **nunca** somados. Grupo R (reposicionamento D+1: R0 não mover, R1 guloso, R2 guloso+busca local, R3 tabu, R4 recozimento, R5 fluxo regional) e grupo D (atribuição: D0 despacho atual, D1 Húngaro, D2 fluxo), sem misturar reposicionamento e despacho. Consultas read-only de lacunas autorizadas "pelos acessos e controles existentes"; **nenhuma consulta nova foi feita nesta etapa** e `TCC_REAL_DATA_AUTHORIZED` não foi alterada (o portão de `data/raw/` continua do proprietário).
**Inventário:** `docs/INVENTARIO_IMPLEMENTACOES.md`. Quase tudo já existe da campanha cancelada por R-23 (código preservado). Falta na linha sintética: tabu, recozimento, grupo D e R5.
**Uso dos períodos reais (levantamento, não suposição):** treino 01/02–15/03 e validação 16–31/03 foram **ambos examinados** no A×B de desenvolvimento de R-22 (59 dias, cenário J) e esse resultado orientou a escolha da "próxima alteração"; o grupo D (atribuição) foi executado só no treino. Portanto a validação 16–31/03 **não é mais intocada** para seleção de método do grupo R; ainda não foi usada para comparar os novos métodos. Setembro (replicação) e 01–25/10 (final) **não foram extraídos** (R-18 cobre 01/02–31/03) e ninguém os examinou. Sem extração direcionada autorizada e executada, **não existe teste real independente**; qualquer comparação real nesta etapa é desenvolvimento ou avaliação retrospectiva.
**Linha sintética:** sementes 9001–9040 já examinadas, só diagnóstico; avaliação final com sementes novas reservadas (`docs/PLANO_GULOSO_LIQUIDO.md` §1, 20001–20040). Gerador e matriz de 22 cenários não serão alterados.
**Interação com o trabalho em curso:** o guloso de benefício líquido (N1/N2) passa a ser o comparador R1′/R2 da linha sintética (mesmo espaço de planos, avaliação por simulação), e tabu e recozimento serão implementados sobre o mesmo avaliador (comparação controlada, item 8 do pedido).
**Correção de R-25 (09/11/2026, após `scripts/verificar_bases_reais.py`):** o parágrafo "Uso dos períodos reais" afirmou que setembro e 01–25/10 **não foram extraídos**. Isso estava **errado** (escrito de memória de R-18, que descreve o plano). Evidência (`reports/revisao/verificacao_bases_reais.json`): todos os 15 dias de 16–30/09 e os 25 de 01–25/10 têm partições para `ods/{solicitacao, status_solicitacao, jornada_motorista, log_status_motorista, compromissos_externos, reposicionamento, veiculo_condutor}` e `es/{posicao_ofertas, reposicionamento_sugerido, sumario_ofertas}`; `telemetria_cobli` só cobre fev–mar; `veiculo` é cadastro sem partição diária. Permanece verdadeiro que ninguém examinou o desempenho de métodos nesses dias; a verificação de integridade (contagens por partição) **não** equivale a uso para seleção. **Pendência de integridade:** 89 partições (73 de `ods/veiculo_condutor`, 16 de `ods/jornada_motorista`) têm 1–3 linhas a mais no Parquet do que o `LOG_LOTES.jsonl`; causa não investigada (hipótese: linhas gravadas em mais de um bloco; a unicidade é tratada por `referencia/disponibilidade.py::resolver_unicidade`, mas a dedução não foi verificada por dia).


## R-26 · Atribuição conjunta (húngaro, lote de 60 s): congelamento, replicação em setembro e avaliação final em outubro (09/11/2026) · EXECUTADA

**Problema:** o proprietário autorizou congelar o húngaro de 60 s e executar 16–30/09 e 01–25/10 (sem alterar o TCC, sem commit/stage). **Verificações:** húngaro idêntico ao ótimo do oráculo em 2.628 lotes de 4 dias de desenvolvimento; pedidos já chegados, elegibilidade, espera com atraso do lote, 0 sobreposições, 0 violações por política, entradas idênticas (`reports/atribuicao_final/verificacoes_desenvolvimento.json`). Defeito achado e corrigido no verificador de bases (somava `rejeitados.parquet`): as 89 "divergências" de linhas eram as linhas rejeitadas; 0 problemas. **Origem da escolha:** W=60 s pela regra do plano no treino real (43 dias); validação e sementes sintéticas 20001–20040 foram vistas antes da decisão de adotar (reclassificado em `docs/CONGELAMENTO_ATRIBUICAO_60S.md` §4). **Resultado (C × A, variação de km vazio, negativo = redução):** setembro −5,96% (IC −133,0; −102,9 km/dia; 14/15 dias melhores; atendidos +16, serviço preservado); outubro −5,04% (IC −97,3; −62,8; 25/25; atendidos −85, **E2 não cumprido**). C × B: −2,74% e −1,40%, serviço preservado. Falhas técnicas 0; sem ajuste entre períodos; hash do código inalterado. **Impacto:** a atribuição conjunta reduziu km vazio simulado frente às referências; não é economia observada; não confirma reposicionamento D+1 (resultado negativo preservado). Mudança de escopo do TCC não decidida. Relatório: `reports/atribuicao_final/RELATORIO_ATRIBUICAO_FINAL.md`.

## R-27 · Rodada 5: recalibração com janeiro–agosto e teste fora da amostra 26/10–08/11 (09/11/2026) · EXECUTADA, PÓS-HOC

**Problema:** o parecer pediu reduzir a distância simulador–operação e obter teste em dados novos, sem tocar nos 120 resultados congelados de set./out. Dados reais autorizados pelo proprietário só nesta rodada (somente leitura, local, agregados). **Plano:** `reports/pos_hoc_parecer/rodada5/PLANO.md` (15:03), escrito antes de qualquer simulação nova. **Extração:** jan. e abr.–ago. e 26/10–08/11 extraídos (HMAC-SHA256); cadastro de veículos tomado das partições diárias `veiculo_condutor` (fotografia por dia, declarada). **Incidente:** a reorganização deixou `parents[3]` (= `src/`) em `env.py` e `saida.py`; a extração gravou em `src/data/extraido`; os lotes faltantes foram movidos para `data/extraido/v1_viagens`, `src/data` removido e o caminho corrigido (`parents[4]`) com teste. **Calibração (só jan.–ago., 242 dias; set./out. não usados):** fator rua/reta 1,54 (n = 90.022; definição: km registrado ÷ reta com última posição ≤ aceite, reta ≥ 0,5 km; difere do 1,30 de março porque a distância registrada usada é outra), velocidade 18,3 km/h (n = 118.256), raio 4,5 km, paciência 240 s (borda da grade). Congelada em 2026-11-09 16:59:48 −0300 (`calibracao_congelada.json`, com hashes do código e do plano). `WORKERS` reduzido de 16 para 6 **antes** do congelamento por falha de memória (arquivo de paginação). Modelo de aceite: só descritivo (pseudo-R² 0,05). **Resultados:** teste 12 dias elegíveis (01/11 e 08/11 excluídos pela regra (a)): C×A −2,79% (IC t −55,8; +4,9 km/dia), ΔN −18; C×B +0,87%; D×C −0,62%, +29. Set./out. recalibrados: C×A −6,77% e −4,62%; C×B −3,64% e −2,83%. Fev.–ago.: C×A −5,2% a −7,6%, C×B −2,5% a −4,8%, todos IC < 0. A diferença de atendimento simulado × aceite observado persiste (9–23 p.p.). **Decisões depois de ver resultados (datadas 09/11):** reportar só IC t quando n ≤ 7 (bootstrap de blocos degenerado), sem nova execução; mover a tabela de validação para o apêndice por limite de páginas. **Impacto:** artigo revisado (Resumo, 2.3, 3, 4.2, Conclusão, Apêndice B); vantagem sobre B não confirmada fora da amostra; tudo rotulado pós-hoc. Relatório: `reports/pos_hoc_parecer/rodada5/RELATORIO.md`.

## R-28 · Rodada 6: simplificação do texto do artigo, sem nova análise (09/11/2026) · EXECUTADA

**Problema:** texto longo e com jargão; leitura do teste fora da amostra ainda não refletida na conclusão. **Feito:** reescrita com termos únicos (dados reais / cenários sintéticos; despacho imediato / lote simples / atribuição conjunta; critério de atendimento); tabela-resumo no corpo; lista "O que este estudo não mostra"; detalhes de método, dados, geografia e estatística movidos para o Apêndice A; conclusão em três partes. **Verificação:** SHA-256 de `reports/tcc_final` 19/19 iguais ao pré-registro (`cb00ee3`); 138/138 arquivos rastreados iguais a HEAD; Parquets de `atribuicao_final` sem hash registrado, totais iguais a `*_absolutos.csv`; números do texto comparados valor a valor (`reports/pos_hoc_parecer/rodada6/numeros_antes_depois.csv`). **Divergências com o pedido:** queda de participação em outubro mantida em 0,9 p.p. (valor exato 0,85; o 0,8 vem de participações arredondadas); o corte em 31/10 foi fixado no plano antes das simulações, depois do inventário, e é rotulado exploratório. **OneDrive:** cliente desinstalado em 15/10/2026; `data/` (desde 06/11) nunca sincronizada por esta máquina; lixeira contém duas pastas `data` do repositório apagadas em 14 e 15/10 (0,98 e 7,17 GB), não tocadas; decisão sobre elas e sobre mover o repositório fica com o proprietário. Relatório: `reports/pos_hoc_parecer/rodada6/RELATORIO.md`.

## R-29 · Rodada 7: plano escrito antes das simulações (09/11/2026 17:57:10 -03:00) · PLANO

**Autorização:** o pedido da rodada 7 (conferir os dados do teste e simular B, C e D) é tomado como autorização do proprietário para esta rodada, nos termos da rodada 5: somente leitura, processamento local, saídas agregadas.
**1. Conferência dos dados de 26/10 a 08/11** (sem simulação): por dia, de 01/09 a 08/11, contar instantes de posição, motoristas distintos no registro de posições, instantes por motorista, pedidos de tempo real, pedidos por hora e hora do primeiro e do último registro; conferir manifestos e o log de lotes da extração (data de extração, linhas, avisos) desses dias. Critério fixado agora: há **sinal de cobertura incompleta** se, num dia, (a) as horas com registro de posição forem menos de 20 de 24, ou (b) o último registro de pedidos ou de posições ficar antes das 22 h, ou (c) os instantes por motorista caírem abaixo da metade da mediana de 01–25/10, ou (d) o manifesto ou o log indicar lote incompleto ou com erro. Dia sem nenhum desses sinais é lido como queda da operação, não da coleta.
**2. Tabela B, C e D** (simulação nova, com mundos e parâmetros já fixados, sem escolha de parâmetros): (i) parâmetros de março (execução congelada, mundos em cache d5cb1289caea) para setembro e outubro; (ii) calibração nova lida de `reports/pos_hoc_parecer/rodada5/calibracao_congelada.json` (verificada pelos hashes) para setembro, outubro e 26/10–08/11. Métricas por período e política: km vazio, atendidos, km por atendido, espera média e P90 entre atendidos. Conferência obrigatória: km e atendidos devem reproduzir `base_por_dia.csv`, `setout_por_dia.csv` e `teste_por_dia.csv`; se não reproduzirem, a tabela não é usada.
**3. Intervalos de C×B por variante:** sem simulação; vêm de `rodada5/intervalos_variantes.csv` (t pareado e blocos de 7 dias), já calculados sobre execuções posteriores.
Saídas em `reports/pos_hoc_parecer/rodada7/`; script novo `scripts/pos_hoc_rodada7.py`; os scripts das rodadas 4 e 5 não são editados.

**R-29, adendo (09/11/2026 17:58:57 -03:00), decisão tomada depois de ver a conferência do item 1:** a coleta dos dias 26/10–07/11 não mostrou sinal de cobertura incompleta pelos critérios fixados (08/11 sim: último pedido às 21:51; dia já excluído). Como as três fontes caem juntas a partir de 31/10, acrescenta-se uma consulta agregada, somente leitura, ao banco operacional: pedidos por dia, região e código de serviço de 19/10 a 08/11, para saber se a queda vem do filtro do estudo (região 1; serviços 1, 11, 12 e 19; sem Prime) ou do total. Sem simulação; sem alteração dos critérios do item 1.

**R-29, resultado (09/11/2026 18:15 -03:00):** (1) Coleta: nenhum dia de 26/10 a 07/11 com sinal pelos critérios (a)–(d); 08/11 com sinal (b), já fora do teste. Medianas por dia, 01–25/10 → 31/10–08/11: motoristas no registro 80 → 41; pedidos 932 → 298; jornadas no recorte 99 → 45; jornadas em todas as regiões 106 → 50; instantes por motorista 334 → 330; 24 h com posição. A queda **não** é atribuída à coleta nem chamada de mudança de regime; a origem fica em aberto. A consulta por serviço do adendo **não foi executada**: SQL Server inacessível (`DBNETLIB ... SQL Server inexistente ou acesso negado`); não houve nova tentativa. (2) B, C e D: 276/276 pares (dia, política) reproduzem as execuções anteriores (diferença máxima de km 4,5e-13; 0 em atendidos); tabela usada. (3) Intervalos C×B: com t pareado, zero incluído em 3 de 12 variantes em cada mês; com blocos de 7 dias, em 2 (setembro) e 1 (outubro). **Correção de forma:** às 18:12 o texto do plano acima teve caracteres de controle (barras invertidas interpretadas ao gravar) substituídos pelos nomes de arquivo originais entre crases; o conteúdo do plano não mudou.

## R-30 · Rodada 7: correção da leitura dos resultados no artigo (09/11/2026) · EXECUTADA

**Problema:** o texto lia o guloso global e a queda do fim do teste de forma mais favorável do que os dados sustentam. **Evidência:** R-29; `reports/pos_hoc_parecer/rodada7/`. **Decisão:** Tabela `tab:bcd` no corpo (B, C, D; março congelada e calibração nova; D rotulado como posterior); "Mecanismo" reescrito (vantagem do Húngaro sobre um guloso global simples não confirmada); critério de setembro dito válido só com parâmetros de março (C×A ΔN = −40 com a calibração nova); "mudança de regime" removida; aceite unificado na definição da Tabela 13; frase "3 de 12" precisada com `tab:sensic`; fatores 1,30 / 1,36 / 1,54 explicados; declaração de dados reescrita (extração de 08 e 09/11; extrato de março guardado na pasta do OneDrive entre setembro e outubro, sincronização não verificada); nota visível ao orientador sobre a declaração não preenchida. **Impacto:** nenhum número congelado mudou (só "56" saiu, de "56–60%" trocado por 55,9/58,9). **Validação:** hashes 157/157 + 40 Parquets iguais à rodada 6; 203 testes aprovados; ruff limpo; compilação sem referência indefinida nem overfull; corpo nas páginas 2–23. Relatório: `reports/pos_hoc_parecer/rodada7/RELATORIO.md`.

## R-31 · Rodada 8: plano da tabela dia a dia de 26/10 a 08/11 (09/11/2026 18:22:00 -03:00) · PLANO

**Contexto:** pedido dos autores na rodada 8 (título, declarações, resumo, teste e queda a partir de 31/10). Sem simulação nova; só leitura de agregados já gravados (`rodada7/dados_por_dia.csv`, `rodada5/teste_por_dia.csv`, `rodada5/setout_por_dia.csv`). Os totais desses dias já tinham sido vistos nas rodadas 5 e 7; o critério abaixo é fixado agora, antes de montar a tabela.
**Tabela:** para cada dia de 26/10 a 08/11: dia da semana, pedidos em tempo real, motoristas no registro de posições, atendidos e % de atendidos em A com a calibração nova (01/11 e 08/11 ficaram fora do teste e aparecem sem A). Referência: mediana dos mesmos dias da semana em 01–25/10, sem 12/10 (feriado nacional).
**Calendário:** 31/10 e 07/11 são sábados; 02/11 é feriado (Finados); 01/11 e 08/11 são domingos.
**Critério:** um dia tem queda se os pedidos ficarem abaixo de 80% da referência do mesmo dia da semana. Se os quatro dias úteis de 03 a 06/11 tiverem queda, o texto diz que a queda não é só de calendário; se nenhum tiver, diz que a queda é de calendário; caso misto, relata dia a dia.
**Saídas:** `reports/pos_hoc_parecer/rodada8/`; script `scripts/pos_hoc_rodada8.py`.

**R-31, resultado (09/11/2026 18:40 -03:00):** dias úteis de 03 a 06/11 com 26–38% dos pedidos da mediana de outubro no mesmo dia da semana; os quatro abaixo do limite de 80% ("todos com queda"). Motoristas nesses dias: 61–81% de outubro. Antes de 31/10, 26, 29 e 30/10 já estavam abaixo do limite (60–75%). Leitura: parte da queda é de calendário (sábados 31/10 e 07/11, domingos 01 e 08/11, Finados em 02/11), mas não toda; causa desconhecida. Saídas: `reports/pos_hoc_parecer/rodada8/dia_a_dia.csv`, `referencia_outubro.csv`, `criterio.txt`.

## R-32 · Rodada 8: decisões dos autores no artigo (09/11/2026) · EXECUTADA

**Decisões dos autores (pedido de 09/11):** título novo; declarações sem nota ao orientador, sem os campos de vínculo, termos de acesso e conflito de interesse, e sem o trecho do OneDrive; operação descrita só como "uma empresa de transporte por aplicativo que opera na Grande Vitória (ES)" no corpo. **Divergência com o pedido:** a frase pedida para o resumo dizia que o guloso global "atendeu o mesmo ou mais que o Húngaro com a calibração nova"; com a calibração nova ele atendeu 41 e 25 a menos em setembro e outubro (0,37% e 0,17%) e 29 a mais só no teste. A frase foi escrita como "atendeu quase o mesmo em setembro e outubro (até 0,4% a menos) e mais no teste". **Também:** "mesmo km por atendido (2,84)" vale no arredondamento (C 2,8404; B 2,8378). O Apêndice D mantém os códigos de produto, região e serviços (fora do corpo, para rastreio). **Validação:** hashes 157/157 + 40 Parquets iguais à rodada 7; nenhum número antigo saiu do texto; 0 citação/referência indefinida, 0 caixa estourada; corpo p. 2–23; 203 testes aprovados; Ruff limpo. Relatório: `reports/pos_hoc_parecer/rodada8/RELATORIO.md`.

## R-33 · Rodada 9: identificadores da empresa retirados do artigo (09/11/2026) · EXECUTADA

**Problema:** o Apêndice D trazia o código do produto, da região, dos serviços e o nome de uma categoria de serviço. **Decisão (autores):** recorte descrito de forma genérica no artigo; códigos só no repositório. **Divergência com o pedido:** o texto pedido dizia que os códigos "constam dos arquivos de configuração"; eles estão no código de extração (`src/tcc_frota/data/extraction/filtro.py`), e a frase foi ajustada para isso. **Ficaram de propósito:** "viagens" (palavra comum) e V1–V3 do exemplo hipotético da Tabela 2. **Validação:** busca repetida no PDF e nos metadados sem códigos restantes; hashes iguais à rodada 8; números iguais; 203 testes aprovados; Ruff limpo. Relatório: `reports/pos_hoc_parecer/rodada9/RELATORIO.md`.

## R-34 · `v1_viagens` identifica a empresa no repositório (09/11/2026) · REGISTRO

**Problema:** o artigo é anônimo desde R-33, mas o nome `v1_viagens` aparece no repositório. Ele está em pastas de dados (`data/raw/v1_viagens*`), no código de extração, em manifestos e em relatórios, e é o nome da origem dos dados.
**Decisão (pedido dos autores na reestruturação):** manter o identificador `v1_viagens`. Renomeá-lo quebraria os manifestos gravados e a rastreabilidade das extrações.
**Impacto:** o repositório identifica a empresa, embora o artigo não a identifique. Antes de qualquer divulgação do repositório, o proprietário deve decidir se isso é aceitável. Os nomes externos de tabelas, campos e serviços não foram alterados.

## R-35 · Reestruturação de pastas, nomes e documentação (09/11/2026) · EXECUTADA

**Problema:** havia várias raízes de resultados e estudos antigos misturados aos vigentes. Os nomes misturavam português e inglês e havia pastas de rodadas.
**Decisão:**
- uma única raiz de resultados (`reports/`, dividida em `historical`, `synthetic`, `diagnostics`, `data_quality`, `figures`, `manifests` e `examples`);
- dados em `data/{raw,processed,geographic}`;
- rodadas renomeadas por finalidade, cada uma com `provenance.json`;
- módulos e scripts em inglês;
- `docs/` consolidado em nove documentos temáticos.

O estudo anterior saiu da árvore e está preservado fora dela, com SHA-256 por arquivo. A trava da calibração da rodada 5 passou a resolver os caminhos antigos por um adaptador. Os arquivos alterados só em caminhos e imports são aceitos pelo registro revisado `frozen_code_equivalence.json`, e o valor congelado não foi recalculado.
**Validação:** `docs/repository_migration.md` §8. Nenhum resultado foi regenerado, e a equivalência histórica com dados reais não foi executada.

## R-36 · Equivalência histórica e reprodutibilidade dos números da rodada 6 (09/11/2026) · EXECUTADA

**Autorização:** o proprietário autorizou, em 09/11/2026, rodar a equivalência histórica com dados reais. `TCC_REAL_DATA_AUTHORIZED=YES` foi levantado só no processo dessa execução, com processamento local e sem saída individual.

**Equivalência:** `scripts/check_equivalence.py --historical` rodou nos 40 dias da avaliação congelada (16–30/09 e 01–25/10). As políticas A, B e C, reconstruídas pelo código reestruturado a partir de `data/raw/`, ficaram iguais aos Parquet congelados em todas as colunas e nas esperas: 40 de 40 dias, 0 diferenças (`reports/manifests/repository_restructure/equivalence_historical_40days.json`).

**Rodada 6:** os números do artigo calculados por scripts locais da sessão eram:
- participação do km vazio no km total modelado e sua queda em p.p.;
- km vazio evitado por dia;
- diferença de atendidos por dia no treino, em setembro e em outubro.

Esses números passaram a ser recalculados por `scripts/compute_article_derived_values.py`, a partir dos dados por dia gravados pelos scripts versionados das rodadas 4 e 5. O script também recalcula a preterição e o 0,48% do teste, e confere o valor arredondado no texto. Resultado: 21 de 21 valores conferem, tanto com o texto quanto com os resumos. Teste: `tests/regression/test_article_derived_values.py`.

**Limitação:** a conferência no texto procura a cadeia formatada. Valores curtos e comuns ("1,3", "0,9") aparecem em outras frases do artigo, e para eles a conferência só garante presença, não a frase. Por isso o script grava também a chave e a fonte de cada valor.

