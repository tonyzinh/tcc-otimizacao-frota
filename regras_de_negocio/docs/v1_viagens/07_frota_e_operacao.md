# 07 — Frota, operação e Sigma

Pasta principal: `analises/frota_dedicada_pj_v1/` (89 arquivos rastreados). Subpastas: `sql/`, `dimensionamento/`, `ocupacao_frota/`, `capacidade_prime/`, `osrm/`, `auditoria_20260911/`, `to_delete/`. Documentos: `README.md`, `PENDENCIAS.md` (45 KB), `RESUMO_PRIME.md`, `AUDITORIA_DADOS_E_CALCULOS.md` (71 KB, 11/09/2026).

## 1. Pergunta e método: frota dedicada PJ

*Quantos carros, por quantas horas, para atender cada cliente PJ com frota dedicada?* Escopo: ArcelorMittal, Oiltanking, Usiminas, Petrobras (4 unidades) → depois **10 empresas** (entram MG Vidros, AESMP, AMAGES); jan–jul/2026, depois 01/05–25/08/2026.

- **Carga** (hora-carro ÷ jornada) × **Pico** (p95 dos picos diários de simultaneidade); o `Fator_Concentracao` diz se a frota fica parada entre picos — e então "dedicar só a janela de pico".
- **Sweep-line:** cada corrida ocupa um carro num intervalo; `+1` ao tomar, `−1` ao liberar. **Início = `CondutorACaminho`** (não `AguardandoCondutor`: fila deixa de existir num cenário dedicado). **Fim = `DT_FIM_REALIZADA` [+ retorno estimado, se `@retorno_entra = 1`].** Desde 26/08, `@retorno_entra = 0` na carteira inteira (ocupação medida, não medida+premissa); hora-carro de agosto **não é comparável direto** com jan–jul (rodou com retorno a 25 km/h).
- **Critério abandonado em 17/08:** p95 do pico diário → **nível de serviço** = % das corridas de hoje que a frota dedicada atenderia (o que o comercial negocia).
- **Não mede** demanda suprimida (será medida por `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL`, escopo PJ customizado), nem o ganho de pickup da dedicação.
- **Sete lacunas** (`99_investigar_lacunas.sql` → `sql/exploracao_banco/`): coordenadas, demanda não atendida, horário pedido do agendamento (`APP_AGENDAMENTO`), passageiros por corrida, **jornada do motorista** (chute de 8 h → respondido depois), SLA contratado, custo do carro dedicado (FP&A; adiado por decisão 20/08).
- **Cinco hipóteses escritas antes de ver o dado:** demanda concentrada em duas janelas; origem é um ponto só (portaria); Oiltanking é a que mais se beneficia; já existe dedicação informal (poucas placas concentram um cliente); agendadas encadeiam melhor.

### Resultado: dimensionamento por faixa (Oiltanking + Arcelor + Usiminas; 152 dias úteis, 5.694 corridas, 37,5/dia, 46,8 hora-carro/dia)

Três faixas (detectadas minuto a minuto: média ≥ 0,25 carro, tolerando vales de 20 min):

| Faixa | Corridas/dia | % | Hora-carro/dia | Ocup. média | Pico p95 | Pico máx |
|---|---|---|---|---|---|---|
| 05:07–08:35 | 14,9 | 39,8% | 19,1 h | 5,50 | 14 | 15 |
| 13:10–18:26 | 14,6 | 39,1% | 20,0 h | 3,79 | 9 | 11 |
| 21:11–23:45 | 6,9 | 18,4% | 7,3 h | 2,86 | 5 | 6 |

As três somam **97,3% das corridas em 11 h 20** de janela; das 9–12 h, 19–20 h e 0–5 h a operação é praticamente inexistente. Manhã sem "joelho" (10 carros = 89,6%; 11 = 94,4%; 12 = 97,8%; 13 = 99,4%). Duas regras da simulação: o carro **não é devolvido** quando a faixa fecha; **sem reposicionamento** entre faixas. Pendentes: Petrobras sem dimensionamento por faixa; fim de semana não dimensionado; sensibilidade a `--limiar`/`--vale`.

## 2. Painel de ocupação (`ocupacao_frota/`)

Replay do **dia observado** (não simulação contrafactual — renomeado de `simulador/` em 20/08). Gerado por `montar_painel.py` (HTML autocontido, dados embutidos; multidia = 117 dias, 4,2 MB; botões Ver matriz / Ver transbordo / Ver tabela); `basemap.py` troca o provedor do mapa e aplica a key CARTO; regeneração dos dados: `regenerar_ocupacao_multidia.py` (orquestra consultas `11`, `20`, `30`, `31`, `33`, `35` e depois `exportar_frota.py`, `presenca_ociosos.py`, `estado_no_transbordo.py`; **não** gera os `.html` — comandos em `multidia/README.md`). Roteamento opcional OSRM em `osrm/` (`rotear_corridas.py` → `06_rotas_osrm.csv`).

## 3. Capacidade da frota Prime — achados (RESUMO_PRIME.md, 11/09/2026)

| # | Achado | Número |
|---|---|---|
| 1 | A frota são **23 carros** (centro de custo 300590260, cadastro mais recente de `APP_VEICULO`), confirmado pelo coordenador da operação em 26/08/2026 | planilha 18 placas → 74,3% das corridas; `BL_PRIME` 21 → 70,0%; **centro 23 → 82,1%** |
| 2 | **Carro nunca foi gargalo**: pico de **14** corridas Prime simultâneas em agosto contra frota ativa mediana de **17**; `SEM_CARRO = 0` em **313** transbordos (mediana de 12 carros parados) | |
| 3 | O estado da operação no transbordo = estado **normal** (motoristas Prime trabalhando 7 × 8; aptos 2 × 2; carros livres 12 × 11). Fim de turno não é o mecanismo (72% sem ninguém a <1 h do fim). "Havia apto em 81% dos transbordos" é **piso** | |
| 4 | Falta de motorista existe e é significativa (zero apto: 25,2% × 17,1% de transbordo, +8,1 pp, RR 1,48, Cochran-Armitage z = −5,741) mas explica **19 de 313 (6,1%)** | |
| 5 | **Cessão** = corrida não-Prime em placa da frota Prime: **172 corridas (11,0%), 13,2% das horas**, concentrada na noite (escalas `NNN 20:00-08:00 SL 4X2`: 45,3% cedidas; `SNN 20-08 4X2`: 36,4%; `NNN 08-20 4X2`: 30,3%; `NNN 12-21 6X1`: 7,7%; `NNN 06-18 5X2`: 6,7%). **"Transbordo reverso" é termo proibido** | |
| 6 | 35,5% de jornadas sem corrida = **escopo, não ociosidade**: 3.179 "escala fantasma" (60,2%) + 602 <60 min (11,4%) + 1.497 ociosidade real (28,4%). Ociosidade real = **10,1%** das jornadas. 47 motoristas nunca tiveram corrida em 4 meses | |
| 7 | **A escala é cumprida quase exatamente:** atraso mediano de entrada 7 min, hora extra −7 min, duração realizada/estimada 98%, absenteísmo 1,5%, `BL_Teto` 1,1%. Jornada realizada mediana **11,67 h** (a inferida por corrida era 9,15 h). 17 turnos distintos atendem o Prime; carga contratual 7 h 20 ou 8 h 48 | |

Definições: **Transbordo** = demanda Prime que sai da frota (corrida de modelo Prime em placa de fora: 313 em agosto, 18,2%); **Cessão** = capacidade Prime gasta com outra demanda. Transbordo diagnosticado em dois níveis: (1) `SEM_CARRO` × `CARRO_LIVRE`; (2) quebra de `CARRO_LIVRE` com a disponibilidade **medida** do log (`--disponiveis`, RS2 da `sql/32`). Não existe exclusividade de motorista entre Prime e V1 (o motorista V1 é puxado para o Prime), então "escala Prime esgotada" não classifica nada. Dentro das escalas Prime, jornadas sem corrida foram de **12,9% (maio) a 23,5% (agosto)**.

**Números aposentados (não citar):** 13,3% e 16,1% (transbordo, frota desatualizada) · 25,9% (agosto, MGS5 de 20/08 contados errado) · 20,2/79,8 e 32,9/67,1 (causas, escala errada/pressupunha exclusividade) · 35,5% (jornadas ociosas) · 9,15 h (jornada inferida).

**Aberto (por impacto):** conferir 20–30 transbordos com a operação; que operação é a "escala fantasma"; cruzar hora da cessão × hora do transbordo; rodar a `sql/20` sem filtro de modelo (fecha o piso do `SEM_CARRO`); comparar `Presentes_Total` com o `Online` da `sql/32`. A auditoria de 11/09 afirma, entre outros, que o indicador "apto" **não mede aptidão operacional** (§7.2) e que "painéis não são fonte independente" (§9.3) — ler antes de citar os 6%.

## 4. Consultas de frota (numeradas) — `analises/frota_dedicada_pj_v1/sql/`

`01_corridas_frota_dedicada`, `02_ocupacao_simultanea`, `03_perfil_od_horario`, `04_coordenadas_corridas`, `05_pontualidade_e_fila_agendamento`, `07_valor_corrida`, `10_petrobras_corridas`, **`11_pj_customizado_corridas`** (sucessor de 01+04+07+10; 10 empresas), `20_prime_corridas`, `21_prime_tipo_frota`, `30_jornada_turno_por_corrida` (8 grids), `31_disponibilidade_por_placa` (4 CSV: `31_prime_01..04`), `32_timeline_status`, `33_jornada_realizada` (jornada escalada × realizada e presença data × hora), `34_nome_motorista`, `35_pausa_motorista` (+ `35_pausas.csv`, `35_motivos_status.csv`), `exploracao_banco/99_investigar_lacunas.sql`. Cuidado: janelas de data **não são uniformes** — `11`, `20`, `30`, `33` usam fim **inclusivo** (`< DATEADD(DAY,1,@data_fim)`); `31` e `35` usam `< @dt_fim` **exclusivo**. Errar corta ou sobra um dia sem erro.

## 5. KM morto, rodagem e custos de frota

- **KM faturado × rodado por placa** (`analises/km_por_placa/`): `sql/km_faturado_por_placa.sql` soma `NU_DISTPERCORRIDA/1000` por placa/mês jan–mar/2026 (**sem dedup** — pode duplicar); a planilha `Distancia_percorrida.xlsx` traz a rodagem mensal por placa (Grupo, Placa, Modelo, Montadora, Ano, km; 542 linhas por aba jan/fev/mar, 1 placa repetida por aba); saída `km_faturado_por_placa_2026.xlsx` (Resumo Executivo, Por Placa, KM Faturado vs Rodado, Detalhe Placa × Perfil, Sem Corrida CC V1). Branches `development`/`analise-v1-prime`/`painel-simultaneidade` acrescentam `manutencao/Dados_Centro_de_custo_Veículos.csv`.
- **O repositório não mede KM morto.** Retorno é premissa; pickup realizado existe (`NU_DISTANCIA_ACEITE_CHEGUEI`); rodagem total existe só como agregado mensal por placa.

## 6. TCC: alocação preventiva de frota D+1 (`docs/REGRAS_NEGOCIO_TCC.md`, 14/10/2026)

Levantamento (não implementação) de regras de negócio para um TCC de **"Otimização da Alocação de Frota em Aplicativos de Transporte Urbano"**: recomendações **D+1** (sem tempo real) que reduzam KM sem passageiro mantendo cobertura. 33 regras (RN001–RN033) com status CONFIRMADA / PROPOSTA / PENDENTE / CONFLITANTE; 5 lacunas críticas: (L1) definição oficial de KM morto, (L2) extrato de pedidos com hora de criação e motivo, (L3) posição/disponibilidade histórica com chaves reconciliadas, (L4) política atual de despacho e autorização de reposicionamento, (L5) universo de modalidades e viagens estaduais. Conclusão: **o repositório especifica o experimento, mas não consegue ainda afirmar ganho operacional medido**. Viabilidade: reconstruir histórico de corridas = NÃO COMPROVADO; posição histórica, disponibilidade, KM morto observado, cenário atual e resultados comparáveis = INVIÁVEL COM OS DADOS ATUAIS; algoritmo guloso = VIÁVEL COM RESSALVAS. Inventário dos 11 XLSX e 24 perguntas P0–P2 estão no próprio documento.

## 7. API Sigma (`sigma_api/` e branches `feature/sigma`, `sigma`)

Base: `https://mobile.v1app.com.br/rotinas-webhook/api` (Azure Functions; header `x-functions-key`, **uma chave por endpoint**: `FunctionHttpListaMotorista`, `FunctionHttpAlteraValor`).

| Endpoint | Função |
|---|---|
| `GET /sigma/lista-motorista?codigoRegiao=1` | Motoristas **logados (não Prime)** da região: `codigo`, `status` (ex.: `Disponivel`), `previsaoDisponibilidade` (HH:mm:ss), `posicao{lat,lng,ultimaPosicao,h3}`, `fimTurno{local,lat,lng}` (opcional — **não** é regra de retorno à base), `corrida{h3 do destino, distanciaRestanteMetros, tempoRestanteSegundos, codigoSolicitacao, codigoProximaSolicitacao}` |
| `POST /sigma/altera-preco` `{"novoValor": ≥0}` | Altera o **preço dinâmico em produção** |

Código: `src/client.py` (`SigmaClient.listar_motoristas`, `.alterar_preco(confirmar=True)`), `config.py`, `scripts/01_listar_motoristas.py` (salva snapshot JSON), `scripts/02_alterar_preco.py` (`DRY_RUN=True`). **Não há histórico de snapshots no repositório**: a API só dá o estado atual. A branch `feature/sigma` (dez/2025) implementa um **coletor** `src/status_snapshot.py`: chama a API a cada 5 min (Agendador de Tarefas do Windows, tarefa `Coletor_Driver_Status`) e grava Parquet em `data/drivers_status/{ano}-{mês}/{dia}{mês}{ano}_driver_status_history.parquet` com `data_captura, hora_captura, qtdeOnline, qtdeIndisponivel, qtdeEmTransito, qtdeTotal`. O diagnóstico recomenda subir esse polling "agora" para ter disponibilidade real de frota **daqui para frente** (não explica junho). Existe `notebooks/marketing_segmentation/sql/test/sigma.sql` na branch `sigma`.

## 8. Dados de operação que existem no banco mas não são explorados em profundidade

`APP_JORNADA_MOTORISTA` (início/fim previsto × realizado), `APP_TURNO_TRABALHO`, `APP_LOG_STATUS_MOTORISTA` (online/ocupado/pausa, `APP_MOTIVOS_ALTERACAO_STATUS` — motivos de pausa: refeição, banheiro [motivo 6], abastecimento…), `APP_SOLICITACAO_JORNADA_MOTORISTA`, `APP_VEICULO_CONDUTOR`, `APP_MODELO_VEICULO` (modelo/placa: `placa_modelo_veiculo.sql`), `VW_DEMANDA_HORARIA_CIDADE`.
