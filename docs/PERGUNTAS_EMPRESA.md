# Perguntas para a empresa

**16/10/2026.** Perguntas objetivas que bloqueiam a interpretação de resultados do TCC. A medida descritiva que motivou as perguntas 1 e 2 está em `resultados/seletivo/deslocamento_livre.csv`; ela não diz por que os veículos se movem.

1. **Status "livre" em movimento.** Nas fotos da frota, motoristas com status livre (estado 1) aparecem em posições diferentes em fotos consecutivas (intervalos de até 11 min na janela 04–11h). O que esse movimento costuma ser? (a) reposicionamento indicado pela operação; (b) abastecimento ou parada; (c) deslocamento até um passageiro ainda não aceito no sistema; (d) outro motivo. Existe algum campo que distinga esses casos?
2. **Política de reposicionamento.** Existe hoje uma regra operacional de reposicionamento (quem decide, quando, para onde e com qual limite de distância)? Os campos `tX_H3INDEX_REPOSICIONAMENTO_REAL` e `nU_DR_REAL` das corridas registram essa decisão? O que significa cada um, e em qual unidade está `nU_DR_REAL`? A cobertura observada desses campos está em `resultados/seletivo/cobertura_campos_reposicionamento.csv`.
3. **Autorização.** Pedimos autorização escrita para (a) usar os extratos de 2026 no TCC e no artigo, com dados pseudonimizados e só agregados publicados; e (b) citar ou não os valores financeiros (preço por km e por minuto, margens por corrida). Sem essa autorização, o texto usa apenas uma grade paramétrica genérica.
4. **Ticket e repasse.** Para setembro/2026 (e, se possível, março/2026), qual é o ticket bruto mediano e o repasse ao motorista por corrida, por faixa horária (04–07h, 07–10h, 10–11h)? A amostra de custos disponível (6–15/out/2026, PF, imediatas, 04–10h, n = 280) não é do período do estudo.
5. **Diferença de custo gravado.** O custo gravado pelo sistema difere do custo recalculado com os parâmetros de precificação (diferença média por corrida informada à parte). Qual dos dois representa o custo marginal real de um km vazio?

## Respostas recebidas em 16/10/2026 — SIMULADAS

O proponente encaminhou uma resposta da "Equipe de Operações e Sistemas" que se declara **fictícia, elaborada para construção de cenários de simulação acadêmica**: não é manifestação oficial da empresa nem autorização jurídica. Por isso nenhuma resposta abaixo muda o status de regras na matriz RN; elas orientam cenários e precisam ser confirmadas com a empresa real.

| Pergunta | Resposta simulada (resumo) | Como foi usada |
|---|---|---|
| 1. Livre em movimento | Pode ser ida a região de demanda (iniciativa própria ou orientação), abastecimento ou alimentação, retorno a ponto de espera ou transição de estado; não há campo que identifique o motivo. Orientação: não tratar como KM morto evitável. | A medida da Fase E fica só descritiva; nenhuma causa é atribuída. |
| 2. Política de reposicionamento | Orientações operacionais, sem otimização global diária nem limite de distância parametrizado. `tX_H3INDEX_REPOSICIONAMENTO_REAL` = célula H3 da região registrada; `nU_DR_REAL` "assumido" em km, a verificar no dicionário de dados. Cobertura parcial não é taxa de reposicionamento. | Campos só descritivos; unidade de `nU_DR_REAL` continua não confirmada. |
| 3. Autorização | Cenário de uso acadêmico agregado, com pseudônimos; **valores financeiros internos não autorizados para publicação**; nome da empresa não deve constar. | Valores financeiros só em `config/custos_privado.yaml` e `reports/runs/` (ignorados); publicação apenas com valores sintéticos rotulados. |
| 4. Ticket e repasse | Tabela **sintética** (repasse = 70% do ticket): diferença de R$ 8,85 (04–07h), R$ 10,44 (07–10h) e R$ 8,16 (10–11h). | Grade pública `tabelas/tab_seletivo_valor_liquido_parametrico.tex`, rotulada como sintética. |
| 5. Custo gravado × recalculado | Nenhum dos dois é custo marginal do km vazio; sugere grade sintética de R$ 0,50 a 1,50 por km. | Mesma grade pública. |
| 6. Considerações | Recomenda comparar também contra um baseline sintético com a movimentação operacional dos livres. | Registrada como próximo passo; não altera o C0 pré-registrado desta rodada. |
