# Atribuição conjunta com janela de 60 s: replicação (16–30/09/2026) e avaliação final (01–25/10/2026)

Simulação com entradas históricas da V1 Viagens. As diferenças abaixo são **simuladas**; não são economia observada na empresa. Protocolo, verificações e origem da escolha: `docs/CONGELAMENTO_ATRIBUICAO_60S.md`. Tabelas completas: `reports/atribuicao_final/analise/` (`tabelas.md`, CSV, JSON). Nada do TCC foi alterado; nada foi commitado nem adicionado ao stage.

## 1. O que foi executado

- Políticas: **A** mais próximo livre, despacho imediato; **B** mais próximo livre em lotes de 60 s (ordem fixa: chegada, depois id); **C** atribuição conjunta pelo húngaro (Kuhn–Munkres), lotes de 60 s. Mesmos pedidos, frota, jornadas, compromissos, parâmetros e distância nas três (assinaturas de entrada idênticas em todos os dias).
- **Contraste principal: C × A**, fixado antes das execuções. Complementares: C × B (isola a atribuição conjunta do efeito do lote) e B × A.
- Execução única, setembro e depois outubro, com a configuração congelada. O hash do código após a execução é igual ao do congelamento. **Falhas técnicas: 0. Reexecuções: 0. Ajustes entre períodos: 0.** Dias elegíveis: 15 de 15 e 25 de 25; nenhum dado ausente, nenhuma exclusão.
- Km vazio = km de busca (esta linha não tem reposicionamento). Km é estimado (reta × fator 1,3012), não odômetro.

## 2. Replicação 16–30/09/2026 (15 dias)

**Valores absolutos**

| Política | Pedidos elegíveis | Atendidos (%) | Não atendidos | Km vazio | Km vazio por atendido | Espera média (s) | P90 (s) | Tempo de computação (s, 15 dias) |
|---|---|---|---|---|---|---|---|---|
| A · imediato | 16.918 | 11.125 (65,76%) | 5.793 | 29.628,3 | 2,66 | 616,4 | 1.183,2 | 1,0 |
| B · lote 60 s, mais próximo | 16.918 | 10.950 (64,72%) | 5.968 | 28.644,9 | 2,62 | 630,6 | 1.195,8 | 1,4 |
| C · lote 60 s, húngaro | 16.918 | 11.141 (65,85%) | 5.777 | 27.861,1 | 2,50 | 600,8 | 1.171,6 | 1,9 |

**Contrastes (variação de km vazio: negativo = redução)**

| Contraste | Variação em km | Variação % | Diferença média diária em km (IC95%, blocos de 7 dias) | Dias com melhora / piora | Atendidos | Atendimento (p.p.) | Espera média (s) | P90 (s) | Serviço (E1–E3) |
|---|---|---|---|---|---|---|---|---|---|
| **C × A (principal)** | −1.767,1 | −5,96% | −117,8 (−133,0; −102,9) | 14 / 1 | +16 | +0,09 | −15,7 | −11,6 | preservado |
| C × B | −783,8 | −2,74% | −52,3 (−61,2; −43,1) | 14 / 1 | +191 | +1,13 | −29,9 | −24,2 | preservado |
| B × A | −983,4 | −3,32% | −65,6 (−76,1; −54,8) | 14 / 1 | −175 | −1,03 | +14,2 | +12,6 | **não** (E2 e E3) |

## 3. Avaliação final 01–25/10/2026 (25 dias)

**Valores absolutos**

| Política | Pedidos elegíveis | Atendidos (%) | Não atendidos | Km vazio | Km vazio por atendido | Espera média (s) | P90 (s) | Tempo de computação (s, 25 dias) |
|---|---|---|---|---|---|---|---|---|
| A · imediato | 23.523 | 14.551 (61,86%) | 8.972 | 39.205,0 | 2,69 | 621,0 | 1.189,7 | 1,3 |
| B · lote 60 s, mais próximo | 23.523 | 14.317 (60,86%) | 9.206 | 37.756,7 | 2,64 | 633,4 | 1.201,5 | 2,0 |
| C · lote 60 s, húngaro | 23.523 | 14.466 (61,50%) | 9.057 | 37.228,7 | 2,57 | 615,8 | 1.181,7 | 2,6 |

**Contrastes (variação de km vazio: negativo = redução)**

| Contraste | Variação em km | Variação % | Diferença média diária em km (IC95%, blocos de 7 dias) | Dias com melhora / piora | Atendidos | Atendimento (p.p.) | Espera média (s) | P90 (s) | Serviço (E1–E3) |
|---|---|---|---|---|---|---|---|---|---|
| **C × A (principal)** | −1.976,3 | −5,04% | −79,1 (−97,3; −62,8) | 25 / 0 | **−85** | **−0,36** | −5,2 | −8,0 | **E2 não cumprido** |
| C × B | −528,0 | −1,40% | −21,1 (−31,1; −11,5) | 16 / 9 | +149 | +0,63 | −17,6 | −19,8 | preservado |
| B × A | −1.448,3 | −3,69% | −57,9 (−77,0; −42,0) | 25 / 0 | −234 | −0,99 | +12,4 | +11,8 | **não** (E2 e E3) |

## 4. Leitura dos resultados

1. **Km vazio.** C teve menos km vazio que A e que B em setembro e em outubro; limite superior do IC95% < 0 em todos os contrastes C. Em C × A: −5,96% e −5,04%, com melhora em 14 de 15 e em 25 de 25 dias. O resultado é coerente com os 16 dias de validação (−4,76%).
2. **Atendimento: em outubro o critério E2 não foi cumprido em C × A.** C atendeu 85 pedidos a menos que A (−0,36 p.p.; −0,58% dos atendidos de A). O IC95% da diferença média diária de atendidos (−7,8; +0,9) inclui 0, e em 9 dos 25 dias C atendeu mais, em 15 menos e em 1 igual; ainda assim o critério fixado antes ("atendidos ≥ referência no período") **não foi cumprido** e a classe pré-definida é `reducao_sem_servico_preservado`. P90 e espera média de C foram menores que os de A nos dois períodos. Em setembro o serviço foi preservado (+16 atendidos). Como C atende menos corridas em outubro, parte da redução de km total pode vir de menos corridas atendidas; o **km por atendido** também caiu (−6,1% em setembro, −4,5% em outubro), o que indica efeito além da diferença no volume, mas esta é uma medida descritiva, não um contraste confirmatório.
3. **Lote × atribuição conjunta.** B (mais próximo livre em lotes) reduz km em relação a A (−3,3% e −3,7%) **à custa de atendimento e espera** (menos atendidos, P90 maior; reprova E2 e E3 nos dois períodos). O ganho de C sobre B (−2,7% e −1,4% de km) vem com **mais atendidos e menor espera** e preserva o serviço nos dois períodos. A atribuição conjunta explica, portanto, a parte do resultado que não vem do simples atraso do lote; o efeito do lote isolado piora o serviço.
4. **Tempo computacional** (inclui a simulação do dia) é desprezível: ~0,1 s por dia; o custo do húngaro nos lotes é de ~0,03 s por dia a mais que B.
5. **Violações.** 0 violações de compromisso causadas pela política nas três políticas, nos dois períodos; compromissos com posição de entrada inconsistente (independem da política): 19 em setembro e 17 em outubro, iguais nas três.

## 5. Conclusão permitida

Setembro e outubro, nas condições avaliadas: **a atribuição conjunta (C) apresentou menor km vazio que as referências simuladas A e B** (−6,0% e −5,0% contra A; −2,7% e −1,4% contra B). Com serviço preservado nos critérios fixados: em setembro contra A e B; em outubro contra B, mas **não contra A** (85 atendimentos a menos, E2 reprovado).

Não se conclui economia comprovada na operação real. O despacho pelo mais próximo é uma referência simples e calibrada, não uma reprodução validada da operação manual; a comparação mede a diferença entre políticas de despacho **neste simulador**. Em particular: o simulador usa velocidade e fator rua/reta únicos, raio de 4,5 km em linha reta, paciência de 180 s e atendimento de 62–66% dos pedidos (resultado do simulador calibrado, não medido na operação); km é estimado; o cenário J usa a jornada realizada; novas tentativas do mesmo passageiro não foram deduplicadas; o cadastro de veículos é uma foto única.

## 6. Independência e limites da evidência

Setembro e outubro nunca haviam sido simulados e o método não foi ajustado depois deles (hash do código inalterado). São evidência fora do período de seleção (fev–mar), mas não totalmente independente: mesma empresa, região, simulador e parâmetros calibrados em março; as sementes sintéticas 20001–20040 e a validação de março foram vistas antes da decisão de adotar o método (ver o congelamento, §4). A replicação e a final são duas observações de períodos distintos, não 40 experimentos independentes: dentro de cada período o dia é a unidade e há dependência temporal tratada por blocos de 7 dias (poucos blocos em setembro: 15 dias).

## 7. Reposicionamento D+1 (preservado)

O resultado negativo do reposicionamento D+1 permanece: nenhum dos métodos de reposicionamento reduziu o km vazio com evidência na validação real, e no sintético o guloso original piorou o km em 21–22 de 22 cenários. Atribuição e reposicionamento respondem a perguntas diferentes (atribuir durante a operação × posicionar antes); o resultado de despacho não invalida o de reposicionamento.

## 8. Evidência para decidir se vale mudar o recorte do TCC para atribuição

A favor:
- Redução de km vazio consistente em quatro conjuntos de dias reais (treino −5,0%, validação −4,8%, setembro −6,0%, outubro −5,0%, contra A) e em 22 de 22 cenários sintéticos (mediana −8,4%), com melhora em quase todos os dias e IC95% sempre abaixo de 0.
- O ganho sobre B mostra que a atribuição conjunta contribui além do lote.
- Método simples, determinístico, tempo desprezível, sem informação futura, implementação auditada contra um oráculo (2.628 lotes).

Contra / a ponderar:
- Em outubro, C × A reprova o critério de atendimento (−85 atendidos). É pequeno (−0,58%) e estatisticamente indistinto de 0 no nível diário, mas é o critério que fixamos.
- A referência não valida a operação manual; o ganho real depende de quão bem o despacho atual da empresa já faz atribuição.
- Muda o escopo: o húngaro decide durante a operação com pedidos já chegados (lote de 60 s, que acrescenta ~40 s de espera média por atraso do lote), não um plano D+1. Isso responde a pergunta diferente da pergunta original do TCC e depende de decisão do proprietário.
- Os dados cobrem fev–mar, set e out de uma única empresa e região.

Decisão sobre o escopo: **não tomada aqui**; o texto do TCC não foi alterado.

## 9. Arquivos

- `docs/CONGELAMENTO_ATRIBUICAO_60S.md`, `reports/atribuicao_final/CONGELAMENTO.json` (hashes, dependências, dados)
- `reports/atribuicao_final/verificacoes_desenvolvimento.json`, `elegibilidade_*.json`
- `reports/atribuicao_final/execucao/` (Parquet por dia), `analise/` (tabelas)
- Reprodução: `scripts/executar_atribuicao_final.py --executar` (com `TCC_COMPARACAO_VENCEDOR_CONGELADO=SIM`) e `scripts/analisar_atribuicao_final.py`
