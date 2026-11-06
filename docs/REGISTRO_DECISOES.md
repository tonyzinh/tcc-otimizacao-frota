# Registro de decisões

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
