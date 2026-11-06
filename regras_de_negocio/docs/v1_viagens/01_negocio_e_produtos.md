# 01 — Negócio e produtos

## 1. O que a V1 Viagens é (pelo que o código mostra)

- **Mobilidade urbana por aplicativo**, com **frota própria e motoristas assalariados**. *INFORMADO* (`analises/funil_conversao_v1/README.md`: "motorista é assalariado: remuneração fixa, sem percentual por corrida e sem vínculo com produtividade"). Consequência registrada: **preço não tem canal de oferta** — baixar margem move demanda, não capacidade, e o custo do tempo parado é integralmente da V1.
- Mas **a exclusividade da frota é PENDENTE**: o TCC (`docs/REGRAS_NEGOCIO_TCC.md` §4) lembra que "frota própria" não prova ausência de agregados, aluguel ou cessão entre produtos. Há coluna `AGENDAMENTO ALUGUEL` na planilha de frota Prime (`frota_prime_20260817.xlsx`), o que sugere que **parte dos veículos é alugada** (*INFERIDO*).
- **Região-base:** `CD_REGIAO = 1` = **Grande Vitória/ES** (Vitória, Vila Velha, Serra, Cariacica…). *VERIFICADO no uso* (todas as análises). Há operação PJ em outras praças: Macaé/RJ (região 4, SIMCORP/Petrobras), com contratos Customizados registrados em São Paulo, Rio, Santos, Mauá, São José e Paulínia (praças **não** atendidas por frota dedicada da V1; `frota_dedicada_pj_v1/README.md`, decisão de 26/08).
- **Viagens estaduais/intermunicipais existem** (`carac. Oper = "PJ Intermunicipal"`; ISS de 5%/12% por regime intra/inter). O corte de "Maior que 100 km" é 0,2% das corridas de março/2026.
- **Escala (ordem de grandeza):** março/2026 = 18.675 corridas na base financeira (53,9% PJ, 46,1% PF); semana de 23–29/jul/2026 = 1.023 corridas PF região 1 não-Prime; julho/2026 = 13.220 cotações PF; dia de pico PF já teve **392 corridas**; mediana de ~285/dia nos dias de maior demanda.
- **O app tem um ambiente Azure**: o banco é **Azure SQL com Entra ID** (autenticação por token), e a API de rotinas é um Azure Functions (`https://mobile.v1app.com.br/rotinas-webhook/api`, chaves "function-level"). *VERIFICADO no código* (`regenerar_dados.py`, `sigma_api/`).
- Existe um site do produto Prime em `prime.v1.com.br` (lido em 28/09/2026 para comparar regras do plano Familiar — `prime_monetizacao_v1/README.md`).

## 2. Segmentos de cliente

A segmentação é determinada por colunas, não por cadastro de "tipo de cliente":

| Segmento | Regra no banco | Observações |
|---|---|---|
| **PF** (pessoa física) | `h.CD_EMPRESA IS NULL` | Só existe na **região 1** (VERIFICADO 03/08/2026: 76.956 solicitações PF, 124 dias, 100% região 1) |
| **PF Sem Cupom / Com Cupom / Com Parceria** | cupom (`CD_CUPOM`/`CD_CUPOM_LOTE`), `APP_DESCONTO.TX_TIPO_DESCONTO = 'Parceria'` | **51,5% das corridas PF têm cupom** (jul/2026), desconto efetivo 10,3% |
| **PJ Padrão** | `FIN_PARAMETRO_PAGAMENTO.TX_TIPO = 'Padrao'` (ou NULL, conforme a consulta) via `CD_PARAMETRO_PAGAMENTO` | Recebeu a fórmula nova de preço em junho/2026 |
| **PJ Customizado** | `FIN_PARAMETRO_PAGAMENTO.TX_TIPO <> 'Padrao'` (`'Customizado'`) | Tarifa **contratada** por cliente (bandeirada + R$/km + minuto parado + espera…). **Não** recebeu a fórmula nova → serve de grupo de controle |
| **Prime** | `TX_MODELO_SOLICITACAO = 'Prime'` | Produto de **assinatura de horas** (planos), tratado como "pessoa física" nas análises de transbordo. Ver [06](06_prime.md) |
| **PJ Fixo** | cotações em `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL` | PJ segue no fluxo de preço fixo; PF foi desligado do fixo em 08–14/06/2026 |

`TX_PERFIL` em `FIN_PARAMETRO_PAGAMENTO` distingue `PessoaFisica`/`PessoaJuridica` e é o caminho para separar PF de PJ **no fluxo fixo** (a tabela fixa não tem `CD_EMPRESA`).

> **Filtro Prime — divergência que custa meia hora.** `ISNULL(TX_MODELO_SOLICITACAO,'') <> 'Prime'` (canônico, **mantém** modelo NULL) × `TX_MODELO_SOLICITACAO <> 'Prime'` (**descarta** NULL). Contagens dos dois grupos não fecham; é esperado. Detalhe em [02](02_modelo_de_dados.md).

## 3. Carteira PJ Customizada (jan–ago/2026)

| Cliente | `CD_EMPRESA` | Notas |
|---|---|---|
| ArcelorMittal Brasil S/A | 20 | Contrato R$ 4,39 + R$ 4,18/km; minuto parado R$ 1,16 |
| Oiltanking Terminais Ltda | 766 | R$ 7,34 + R$ 4,28/km; minuto parado R$ 0,97; 99,5% das corridas agendadas |
| Usinas Siderúrgicas de Minas Gerais (Usiminas) | 53 | Duas tarifas no período (parâmetros 24920 → 25074, mudança em 17/04) |
| MG Vidros Automotivos Ltda | 4.499 | 4 parâmetros vigentes que são **faixas de horário**; existe **outra empresa com o mesmo nome** (2020) → chavear sempre por `CD_EMPRESA` |
| Petrobras (4 unidades Vitória/Macaé) | — | Escopo fechado em 4 unidades por decisão de 26/08 |
| AESMP (412), AMAGES (130) | — | Entraram só para leitura de perfil de uso (<5 corridas/dia) |
| SAITER HOTEIS | 4.071 | Fora de escopo — migrou para PJ Padrão |

Mais detalhe em [05](05_pj.md).

## 4. Modelo de serviço de corrida

- **Duas modalidades de preço em PF:** *Dinâmico* (`BL_PRECO_DINAMICO = 1`, cotação em `APP_ESTIMATIVA_PRECO`) e *Fixo* (`= 0`, cotação em `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL`; era a **viagem longa**, >10 km, 87–97% das corridas dessa faixa; **desligado para PF em 08–14/06/2026**).
- **Dois serviços visíveis no app** (avaliação de UX): "Serviço padrão V1" e **"V1 Prioridade"** (`feedback-app-v1/relatorios/recomendacoes-ux.md`; há também relatórios de 2025 sobre "Prioridade threshold km").
- **Agendamento:** `CD_AGENDAMENTO`. Corrida agendada tem fila/espera muito diferente (ver [02](02_modelo_de_dados.md) §6). Prime exige antecedência mínima de **45 min** (`APP_PARAMETRO_PRIME.NU_ANTECEDENCIA_AGENDAMENTO`); PF tem `DE_TAXA_AGENDAMENTO_PF`; PJ Customizado **não tem** instrumento de taxa de agendamento (é ausência de cláusula, não falha de cobrança).
- **Cupom/desconto/parceria/colaborador:** `APP_CUPOM_DESCONTO` (+`_LOTE`), `APP_DESCONTO` (`Parceria`, `Colaborador`), `DE_VALOR_DESCONTO_FUNCIONARIO`.
- **Piso de R$ 16** por corrida (fórmula nova), ativo em ~9,3% das corridas PF.

## 5. Quem trabalha nos dados (git log)

| Pessoa | Papel visível |
|---|---|
| **Vitor Amorim** | Dono do repositório e das análises de precificação/frota (80+ commits; "cientista de dados" no README de 09/2025) |
| **Marcelo Passamai Marques** | Prime: planos, simultaneidade, ociosidade (branches `analise-v1-prime`, `painel-simultaneidade`) |
| **Isllan Toso Pereira** | Análises PF/PJ, cancelamento, projeção de metas, ticket por km, bairro/H3, engenharia |
| **Entony Jovino dos Santos** | Demanda reprimida, resultado por carro, PJ padrão, análise geral outubro, LaTeX, Sigma |
| **Lara Araujo Nascimento** | Análises PF (receita, faixa de km, fixo × dinâmico, cancelamento) |
| **Elias De Nadai Nalesso Silva** | PF × cupom, queda de receita por PJ, utils_db |
| **Henrique Hiluey Roriz Perin** | Reestruturação do repositório (`fix/repos-restructuring`) |

Referências a papéis na empresa: FP&A (custos, parâmetros de PF), dev (gravação de campos, deploy), operação Prime (coordenador confirmou a frota de 23 carros em 26/08/2026), comercial (planos e SLA), RH (jornada).

## 6. Dois eixos estratégicos que atravessam o repositório

1. **Precificar pelo custo real da frota** (por hora alocada), não por tarifa: ver [03](03_precificacao.md). Meta: MC02 por hora de frota de R$ 30–40 (motor v2) / alvo de Fat/h R$ 91,03.
2. **Dimensionar e alocar a frota** (menos KM morto, menos ociosidade, mais cobertura): ver [07](07_frota_e_operacao.md). Inclui um TCC acadêmico de alocação preventiva D+1 (`docs/REGRAS_NEGOCIO_TCC.md`).
