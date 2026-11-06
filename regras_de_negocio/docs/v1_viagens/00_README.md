# V1 Viagens — documentação do conhecimento extraído do repositório

**Gerado em:** 2026-11-06 · **Base:** repositório `data-science-v1`, branch `analise/dimensionamento-frota-pj` (HEAD `c445050`) + as 24 branches remotas
**Método:** leitura de consultas SQL, código Python, notebooks (cabeçalhos), READMEs e documentos de análise. Nada foi executado contra o banco, a API Sigma ou qualquer extrato.

> **Como ler esta pasta.** Cada afirmação carrega um nível de confiança, herdado das fontes:
>
> | Marca | Significa |
> |---|---|
> | **VERIFICADO** | Medido em dado real pelo próprio repositório, com n e teste registrados |
> | **PRECEDENTE** | Uso consistente em várias consultas, sem teste próprio |
> | **INFORMADO** | Dito pelo dono do dado ou pela operação e registrado em documento; não medido |
> | **INFERIDO** | Deduzido por mim lendo código/consulta. Plausível, não confirmado |
> | **ABERTO** | Ninguém sabe; exige dev, FP&A ou operação |
>
> Onde a fonte não traz marca, trato como PRECEDENTE.

## Índice

| # | Arquivo | Conteúdo |
|---|---|---|
| 00 | `00_README.md` | Este índice, escopo, limites |
| 01 | [`01_negocio_e_produtos.md`](01_negocio_e_produtos.md) | O que é a V1 Viagens, segmentos (PF, PJ Padrão, PJ Customizado, Prime), regiões, modelo operacional |
| 02 | [`02_modelo_de_dados.md`](02_modelo_de_dados.md) | Tabelas, chaves, ciclo de vida da corrida, armadilhas de coluna, unidades, regras de dedup e filtro |
| 03 | [`03_precificacao.md`](03_precificacao.md) | Fórmula do preço, custos, MC0.1→MC1, piso, σ, fixo × dinâmico, cupom/desconto, deploy de 13/06/2026 |
| 04 | [`04_pessoa_fisica.md`](04_pessoa_fisica.md) | Comportamento PF, funil de conversão, elasticidade, CRM, marketing, aeroporto |
| 05 | [`05_pj.md`](05_pj.md) | PJ Customizado e Padrão: contratos, cláusulas de espera, MC02 por cliente, simulação de preço |
| 06 | [`06_prime.md`](06_prime.md) | Produto Prime (assinatura de horas): planos, consumo, simultaneidade, monetização, ociosidade |
| 07 | [`07_frota_e_operacao.md`](07_frota_e_operacao.md) | Frota dedicada PJ, capacidade Prime, jornada/escala, ocupação, Sigma API, KM morto |
| 08 | [`08_branches.md`](08_branches.md) | Inventário das 25 branches: dono, período, o que cada uma contém, o que só existe nela |
| 09 | [`09_catalogo_codigo_e_sql.md`](09_catalogo_codigo_e_sql.md) | Mapa de pastas, convenções, catálogo de consultas e scripts, pipeline de regeneração |
| 10 | [`10_lacunas_e_perguntas_abertas.md`](10_lacunas_e_perguntas_abertas.md) | O que não se sabe, contradições entre documentos, números aposentados |
| 11 | [`11_glossario.md`](11_glossario.md) | Siglas e termos (DV, DP, DR, MC02, σ, cessão, transbordo…) |

## Escopo — o que "V1 Viagens" quer dizer aqui

O repositório não tem um documento institucional da empresa. **V1 Viagens** (também "V1", "V1 Mobilidade", "App V1") é, pelo que o código e os relatórios mostram, uma **empresa de mobilidade urbana por aplicativo com frota e motoristas próprios**, operando na **Grande Vitória/ES** (região 1) e com atendimento corporativo em outras praças (Macaé, por exemplo). O repositório é do time de dados/precificação e gira em torno de uma pergunta:

> Qual preço maximiza **margem operacional por hora de frota**, dado que cada corrida consome o carro em três pernas (pickup, viagem, retorno) e a receita só olha uma?

Tudo o que se segue é o que dá para saber sobre a V1 **a partir da perspectiva desse time**: banco, preço, frota, clientes. Não há aqui contrato social, organograma, finanças consolidadas nem especificação do app (exceto a avaliação de UX em `feedback-app-v1/`).

## Cobertura desta documentação

| Fonte | Lida? |
|---|---|
| `CLAUDE.md` (39 KB) e `sql/DICIONARIO_BANCO.md` | Integralmente |
| `docs/REGRAS_NEGOCIO_TCC.md` | Integralmente |
| `analises/dre_simulacoes_preco/` (README, equações, dicionário, clientes_pj) | Integralmente |
| `analises/diagnostico_novo_preco_v1/` (README, hipóteses, C4, o_que_falta_buscar, LEIA-ME) | Integralmente; `roteiro_investigacao.md` e `dicionario_metricas.md` só pelos títulos |
| `analises/frota_dedicada_pj_v1/` (README, RESUMO_PRIME, PENDENCIAS, dimensionamento) | README e RESUMO_PRIME integrais; PENDENCIAS, AUDITORIA, ocupacao_frota e capacidade_prime por título/trecho |
| `analises/prime_*`, `funil_conversao_v1`, `pessoa_fisica`, `custos_operacao_v1`, `sigma_api`, `scripts/sql_pipeline`, `feedback-app-v1` | READMEs |
| Branches remotas | `git ls-tree` (inventário), diferenças contra o HEAD, e a documentação principal de cada uma (`README`/`Documentacao.md`); notebooks e SQLs só por nome e cabeçalho |
| SQL (`sql/` raiz + `analises/**/sql`) | Cabeçalhos e contagem de tabelas citadas (~830 arquivos rastreados no HEAD; leitura integral só das consultas citadas nos documentos) |
| `.xlsx`, `.pdf`, `.tex`, `.docx`, imagens | Não abertos (nomes e referências em documentos apenas) |

**Limite honesto:** onde eu digo "a consulta X faz Y" sem marca, é porque o cabeçalho/README da própria consulta diz. Não reexecutei nem reauditei os números; reproduzo os que os documentos do repositório já registram, com a fonte.

## Cinco coisas para saber antes de qualquer outra

1. **Várias colunas do banco não são o que o nome diz** (`DE_VALOR_HORA_MOTORISTA` está em R$/**minuto**; `h.NU_DP` é a *estimativa*; `NU_DR_REAL` é quase sempre a estimativa). Ver [02](02_modelo_de_dados.md).
2. **`APP_SOLICITACAO_HIST` tem uma linha por transição de status** — sem dedup toda contagem infla. Ver [02](02_modelo_de_dados.md).
3. **O preço é congelado no aceite**; erro de tempo custa margem da V1, não confiança do cliente. Ver [03](03_precificacao.md).
4. **O deploy do "preço real" em ~13/06/2026** é o evento central das análises recentes; 53% da queda inicialmente atribuída a ele era artefato de mudança de fluxo (o preço fixo de PF foi desligado na mesma semana). Ver [03](03_precificacao.md) e [04](04_pessoa_fisica.md).
5. **A frota Prime tem capacidade sobrando, não faltando** (23 carros; zero transbordo por falta de carro). Ver [06](06_prime.md) e [07](07_frota_e_operacao.md).
