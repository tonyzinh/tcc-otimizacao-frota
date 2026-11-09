# Rodada 7: leitura dos resultados, dados do teste e guloso global (09/11/2026)

Tudo aqui é **análise posterior aos resultados congelados**. Nenhum número das Tabelas 6 e 7 nem dos valores congelados citados no texto mudou. Nada foi commitado nem adicionado ao stage.

## 1. Plano escrito antes de rodar

Registrado em `docs/REGISTRO_DECISOES.md`, R-29, às **09/11/2026 17:57:10 −03:00**, antes da conferência e das simulações:

- **Autorização:** o pedido da rodada 7 foi tomado como autorização do proprietário para esta rodada (somente leitura, processamento local, saídas agregadas).
- **Item 1, conferência da coleta, sem simulação.** Há sinal de coleta incompleta num dia se:
  - (a) houver menos de 20 horas com posição;
  - (b) o último pedido ou a última posição for antes das 22h;
  - (c) os instantes por motorista ficarem abaixo da metade da mediana de 01–25/10;
  - (d) o manifesto ou o log apontar lote incompleto ou erro.
- **Item 2, B, C e D:** parâmetros de março (mundos em cache) para setembro e outubro; calibração nova lida de `rodada5/calibracao_congelada.json` para setembro, outubro e 26/10–08/11. A tabela só seria usada se km e atendidos reproduzissem `base_por_dia.csv`, `setout_por_dia.csv` e `teste_por_dia.csv`.
- **Item 3, intervalos C×B por variante:** lidos de `rodada5/intervalos_variantes.csv`, sem simulação.

**Adendo às 17:58:57**, decidido depois de ver o item 1: uma consulta agregada de pedidos por dia, região e serviço (19/10–08/11), para separar a queda do recorte do estudo da queda do total. **Não foi executada**: o SQL Server estava inacessível (`DBNETLIB ... SQL Server inexistente ou acesso negado`). Não houve nova tentativa.

**Correção de forma no registro:** o texto do plano tinha caracteres de controle no lugar de `\r`, `\b` e `\t` dos nomes de arquivo. Às 18:12 eles foram trocados pelos nomes originais. O conteúdo do plano não mudou, e isso está anotado em R-29.

## 2. Item 1: conferência dos dados

Arquivos: `dados_por_dia.csv`, `dados_pedidos_por_hora.csv`, `dados_resumo_periodo.csv`, `dados_distribuicao_horaria.csv`.

**Medianas por dia:**

| Grandeza | 01–25/10 | 26–30/10 | 31/10–08/11 |
|---|---:|---:|---:|
| Instantes com posição | 711 | 713 | 716 |
| Horas com posição | 24 | 24 | 24 |
| Motoristas no registro de posições | 80 | 81 | 41 |
| Instantes por motorista | 334 | 336 | 330 |
| Pedidos em tempo real | 932 | 817 | 298 |
| Horas com pedido | 24 | 24 | 22 |
| Jornadas no recorte do estudo | 99 | 102 | 45 |
| Jornadas em todas as regiões (inventário da rodada 5) | 106 | 114 | 50 |

**Sinais de coleta incompleta:**

- 26/10–07/11: nenhum.
- 08/11: tem o sinal (b), com último pedido às 21h51. Esse dia já estava fora do teste.
- Setembro: 15 dias com sinal, todos em 01–15/09 (sem manifesto). Ficam fora do período estudado (16–30/09).
- Alguns dias do teste têm 239–270 instantes por motorista, acima do limite de 167.

**Distribuição horária dos pedidos:**

| Faixa | 31/10–08/11 | Outubro |
|---|---:|---:|
| 00–05h | 0,109 | 0,102 |
| 06–11h | 0,299 | 0,254 |
| 12–17h | 0,280 | 0,360 |
| 18–23h | 0,312 | 0,284 |

**Leitura:**

- Não há sinal de coleta incompleta nos dias do teste.
- A queda aparece ao mesmo tempo em fontes independentes: posições, pedidos, jornadas no recorte e jornadas em todas as regiões.
- Ela pode vir da operação ou de mudança no que os sistemas registram ou no recorte do estudo.
- Sem a contagem por serviço não dá para separar essas causas.
- O artigo **não** chama mais a queda de "mudança de regime". A leitura "pouca demanda por lote" ficou como não testada, e entrou a frase de que a queda pode vir de limitação dos dados.

**Os dois valores 50,3 da Tabela 13 (agora Tabela 15), última coluna:**

- **Não** são cópia um do outro.
- Em `rodada5/componentes_antes_depois.csv`, `A_marco_atendidos_pct = 50,288` e `motoristas_simulados_dia = 50,286`. Coincidem no arredondamento.
- Os valores ficaram iguais e a explicação foi acrescentada na fonte da tabela.

## 3. Item 2: B, C e D lado a lado

Arquivos: `bcd_resumo.csv`, `bcd_por_dia.csv`, `bcd_conferencia.json`.

**Conferência:** 276 de 276 pares (dia, política) reproduzem as execuções anteriores. A diferença máxima de km foi 4,5e−13, e não houve diferença em atendidos. A tabela entrou no corpo (Tabela 8, `tab:bcd`).

**Arredondamento:** nas linhas de março, B e C usam os valores impressos na Tabela 6, para não haver duas versões do mesmo número. A recomputação dá diferença na última casa em dois valores:

| Valor | Tabela 6 | Recomputado |
|---|---:|---:|
| Espera média de C em setembro | 600,8 | 600,7 |
| P90 de B em outubro | 1.201,5 | 1.201,4 (valor bruto 1.201,4499) |

A Tabela 6, congelada, não foi alterada.

**D contra C:**

| Período | Calibração | Km de D × C | Atendidos D − C |
|---|---|---:|---:|
| Setembro | março | −2,66% | −179 |
| Outubro | março | −1,88% | −83 |
| Setembro | nova | −1,23% | −41 |
| Outubro | nova | −2,04% | −25 |
| Teste 26/10–08/11 | nova | −0,62% | +29 |

A vantagem do Húngaro sobre um guloso global simples **não se confirmou**. D foi definido depois dos resultados congelados, e isso está rotulado na tabela e no texto.

## 4. Item 3: intervalos C×B por variante

A nova Tabela 14 (`tab:sensic`, Apêndice B) traz, para cada variante, o intervalo do t pareado e o do bootstrap de blocos de 7 dias.

**Variantes, entre 12, cujo intervalo inclui zero:**

| Método | Setembro | Outubro |
|---|---:|---:|
| t pareado | 3 | 3 |
| Blocos de 7 dias | 2 | 1 |

A frase "incluiu zero em 3 de 12 variantes" estava certa para o t pareado. Agora ela diz qual intervalo usa e remete à tabela.

## 5. Item 4: declarações e OneDrive

**Datas de criação** (`datas_criacao_dados.csv`):

- Todas as partições de `data/extraido/v1_viagens` usadas (janeiro a novembro), os mundos em cache e `data/geografia` foram criados entre **08/11 01:51 e 09/11 17:00**.
- A rodada 6 dizia que a extração começou em 06/11; os arquivos usados são de 08 e 09/11. O texto foi corrigido.

**Cliente OneDrive:**

- Desinstalado pelo usuário em 15/10/2026 19:14 (`UserInitiatedUninstall=1`).
- Não há executável, e o último log é de 15/10.
- A pasta de instalação é de 18/09/2026.

**Parâmetros de março:**

- Vêm do estudo anterior (`reports/tcc_final`, gerado em 16/10 01:39 UTC; commit em 15/10 22:43).
- O "extrato anterior" (466 aproximações) ficou na pasta do OneDrive enquanto o cliente estava instalado, entre 18/09 e 15/10.
- **Não é possível verificar daqui** se foi sincronizado com a nuvem.

**Lixeira do Windows:** duas pastas `data` do repositório, não tocadas.

| Tamanho | Apagada em | Situação do OneDrive |
|---:|---|---|
| 0,98 GB | 14/10 19:14 | instalado |
| 7,17 GB | 15/10 21:11 | já desinstalado |

**Texto novo da declaração:** dados de jan–nov/2026 extraídos em 08 e 09/11/2026, com o cliente desinstalado. O extrato de março ficou na pasta entre setembro e outubro, e sua sincronização não foi verificada.

**Falta conferir no OneDrive pela web:**

- a lixeira da nuvem;
- o histórico de versões da pasta do repositório entre 18/09 e 15/10, para saber se `data/` ou o extrato de março subiram.

**Nota ao orientador:** caixa visível na p. 21, acima dos campos não preenchidos. Ela deve sair da versão final.

## 6. O que os autores precisam responder

1. **Vínculo:** qual é a relação dos autores com a empresa da operação.
2. **Termos de acesso:** quem autorizou o uso dos dados, por qual meio e com quais restrições (publicação, agregação, prazo, anonimização).
3. **Conflito de interesse:** se há ou não, e de que tipo.
4. **OneDrive:** se a pasta do repositório foi sincronizada entre 18/09 e 15/10, o que fazer com as duas pastas `data` da lixeira e com eventuais cópias na nuvem.
5. **Título:** decisão final com o orientador.
6. **(Opcional) Queda a partir de 31/10:** a empresa sabe de mudança operacional, de cadastro ou de sistema nesses dias? A consulta por serviço pode ser refeita quando o SQL Server estiver acessível.

## 7. Mudanças no texto

**Seção 4.2, Atendimento:** "o critério de atendimento foi cumprido com os parâmetros de março (com a calibração posterior, não; Seção 4.3)".

**Seção 4.2, Simulador:** definição de aceite ("pedido com registro de motorista a caminho") e valores 55,9 / 58,9 / 44,2 / 40,5.

**Seção 4.3, Sensibilidade:** "3 de 12" precisado (t pareado; 2 e 1 com blocos; Tabela 14).

**Seção 4.3, Recalibração:**

- Explicação dos fatores 1,30 / ≈1,36 / 1,54: origem de cada um, nenhum é de odômetro, a avaliação congelada usa 1,30 e a recalibração 1,54, e a sensibilidade com 1,6 está na Tabela 13.
- Conferência da coleta: sem sinal; queda simultânea nas fontes; causa em aberto; contagem por serviço não feita.
- Atendimento com a calibração nova: −40 em setembro, −54 em outubro e −114 em abril. O critério de setembro só vale com parâmetros de março.
- "uma mudança de regime" removida.

**Seção 4.3, Guloso global:**

- Reescrito: D é posterior, com os resultados de março, da calibração nova e do teste.
- "A vantagem do Húngaro sobre um guloso global simples, portanto, não se confirmou."
- Nova Tabela 8 (`tab:bcd`).

**Seção 4.5, Mecanismo:** reescrito como pedido.

**Seção 4.5, Atendimento e km:** frase nova: "A queda de motoristas e de atendimento nesses dias também pode vir de limitação dos dados."

**Seção 4.6, limites:**

- Aceite pela definição única (55,9 e 58,9 → 44,2 e 40,5).
- Generalização: "queda de pedidos e motoristas não foi explicada".

**Conclusão, "O que não foi confirmado":**

- Setembro com a calibração refeita: 40 a menos.
- Guloso global (179 e 83 a menos com março; 41 e 25 com a nova; +29 e −0,62% no teste) e "A vantagem do Húngaro sobre esse guloso não se confirmou."

**Declarações:** texto de dados reescrito (item 5) e nota ao orientador.

**Apêndice B:**

- Nova Tabela 14 (`tab:sensic`).
- Nota sobre os dois 50,3 na Tabela 15.
- Parágrafo e nova Tabela 18 (`tab:dados`) com a conferência da coleta.

**Apêndice D:** rastreio de `rodada7/` e `scripts/pos_hoc_rodada7.py`.

**Renumeração das tabelas** (a Tabela 8 entrou no corpo; as Tabelas 6 e 7 continuam com os mesmos números):

| Tabela | Antes | Agora |
|---|---:|---:|
| Sintéticos | 8 | 9 |
| Sensibilidade | 12 | 13 |
| Grandezas observadas | 13 | 15 |
| Recalibração | 14 | 16 |
| Corte mensal | 15 | 17 |
| Cenários sintéticos por cenário | 16 | 19 |

## 8. Verificação

**Resultados congelados** (`hashes_congelados.csv`):

- `reports/tcc_final`: 19 de 19 iguais ao pré-registro (`cb00ee3`).
- Arquivos rastreados: 138 de 138 iguais a HEAD (`3e65f3b`).
- 40 Parquets sem hash registrado: SHA-256 igual ao da rodada 6.
- Falhas: 0.

**Números** (`numeros_antes_depois.csv`):

- Só um valor saiu: "56", de "56–60%", substituído por 55,9 e 58,9 da definição única.
- Todos os valores novos vêm das Tabelas 8, 14 e 18 e dos parágrafos que as citam.
- Nenhum número das Tabelas 6 e 7 mudou.

**Compilação** (XeLaTeX, BibTeX e XeLaTeX ×2):

- 0 citações ou referências indefinidas.
- 0 caixas estouradas.
- 36 páginas. O corpo, da introdução (p. 2) ao fim das referências (p. 23), tem 22 páginas, abaixo do limite de 25.
- Os apêndices começam na p. 24.
- PDF copiado para `article/ARTIGO_ATRIBUICAO_HUNGARO.pdf`.

**Testes:** `pytest` deu 203 testes, 0 falhas, 0 erros e 0 pulados, em 8,1 s (`pytest_junit.xml`).

**Lint:** `ruff check .` sem erros ("All checks passed!"); `ruff format --check .` com 124 arquivos já formatados.

**Não executado:** a consulta por serviço (SQL Server inacessível).
