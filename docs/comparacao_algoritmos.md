# Comparação de algoritmos de alocação preventiva D+1

**Atualizado em 15/10/2026.** Todos os algoritmos recebem as mesmas entradas do corte D+1 e passam pela mesma materialização e pelo mesmo replay de [experimento_real.md](experimento_real.md): setembro/2026, 30 dias, janela 07–10 h, presença prevista ≥ 50%, reposicionamento ≤ 12 km e tolerância de execução de 30 min. As distâncias são Haversine estimadas; os resultados não são economia observada nem política da empresa.

## Candidatos e o que cada um testa

| Algoritmo | Família (PDF, cap. 2) | Ideia | Pergunta que responde |
|---|---|---|---|
| Sem reposicionamento | referência | despacho do veículo livre mais próximo | ponto zero da comparação |
| **Guloso** (`greedy.py`, DT001) | heurística construtiva | adiciona o movimento que mais reduz pickup projetado + reposicionamento, sem reduzir a cobertura projetada | a escolha do PDF funciona? |
| Proporcional | regra simples | vagas por zona proporcionais à demanda prevista, preenchidas pelo par veículo–vaga mais próximo | uma regra de operador basta? |
| Atribuição ótima | método exato | mesmas vagas, preenchidas pelo algoritmo húngaro com a menor soma de km (ótimo garantido para essa formulação) | otimalidade muda o resultado? |
| Busca local | metaheurística | *simulated annealing* sobre o mesmo objetivo do guloso, partindo da solução gulosa; nunca piora esse objetivo | otimizar melhor o objetivo do guloso ajuda? |
| Guloso simulado | heurística com avaliação por simulação | guloso cujo objetivo é o KM vazio **simulado** nos 4 dias de treino mais recentes (pedidos reais deslocados para D+1), sem reduzir a cobertura simulada | o problema está no objetivo aproximado? |

Formulações e testes: `src/tcc_frota/optimization/alternatives.py` e `tests/unit/test_alternatives.py`. O húngaro é conferido contra força bruta; a busca local nunca piora o objetivo inicial; o guloso simulado só usa dias anteriores ao corte.

## Resultados (setembro/2026)

Redução positiva = preventivo melhor. KM vazio = pickup + reposicionamento. O cenário sem reposicionamento é o mesmo para todos: 4.603,2 km de pickup e 93,3% de cobertura.

| Algoritmo | Recomendações | Executadas | Pickup (km) | Reposicionamento (km) | Redução KM vazio | Cobertura | Dias sem piora de cobertura | Tempo de plano (s/dia) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Guloso (DT001) | 640 | 129 | 4.536,9 | 737,4 | −14,6% | 92,4% | 17/30 | 220 |
| Proporcional | 718 | 115 | 4.611,2 | 710,7 | −15,6% | 92,4% | 16/30 | 0,03 |
| Atribuição ótima | 752 | 121 | 4.495,6 | 650,3 | −11,8% | 92,3% | 13/30 | 0,04 |
| Busca local | 657 | 129 | 4.521,6 | 724,2 | −14,0% | 92,1% | 15/30 | 244 |
| **Guloso simulado** | 26 | 4 | 4.595,8 | 17,1 | **−0,2%** | **93,3%** | **30/30** | 58 |

Diagnóstico com oráculo, que usa a frota e as posições reais das 07:00 e viola o corte:

| Algoritmo (oráculo) | Executadas | Reposicionamento (km) | Redução KM vazio | Cobertura |
|---|---:|---:|---:|---:|
| Guloso | 114 | 439,9 | −9,0% | 92,4% |
| Proporcional | 147 | 424,9 | −8,3% | 92,7% |
| Atribuição ótima | 156 | 503,9 | −8,6% | 92,5% |
| Guloso simulado | 8 | 16,4 | −0,5% | 93,5% |

### Promessa do plano versus replay

| Algoritmo | Economia de pickup projetada | Reposicionamento planejado | Economia de pickup no replay |
|---|---:|---:|---:|
| Guloso | 5.881 km | 2.970 km | 66 km |
| Atribuição ótima | 6.552 km | 3.757 km | 108 km |
| Busca local | 6.184 km | 3.098 km | 82 km |
| Guloso simulado | 150 km | 94 km | 7 km |

O objetivo aproximado (distribuir a demanda prevista pela capacidade dos veículos mais próximos do centróide da zona) promete economias de pickup dezenas de vezes maiores (de 55 a 89 vezes) do que as obtidas no despacho pedido a pedido.

## Por que esses resultados

1. **Desigualdade triangular.** Em linha reta, ir até uma zona e depois atender ali nunca custa menos que atender direto da posição original. O reposicionamento só gera ganho quando corrige uma escolha míope do despacho "mais próximo" (ver `test_simulated_greedy_gains_only_by_correcting_myopic_dispatch`) ou quando permite atender um pedido que expiraria. Esses casos são raros nos dados.
2. **O gargalo é o objetivo, não o otimizador.** O método exato e a metaheurística otimizam melhor o mesmo objetivo e continuam perdendo; mesmo com o oráculo, perdem 8–9%. Só o objetivo avaliado por simulação deixa de prejudicar.
3. **Previsão de presença.** Só 16–20% das recomendações dos métodos aproximados chegam a ser executadas. O oráculo reduz a perda, mas não a inverte.

## Por que manter o guloso, e o que muda

| Critério | Guloso | Proporcional | Atribuição ótima | Busca local | Guloso simulado |
|---|---|---|---|---|---|
| Interpretabilidade | alta: cada movimento tem ganho explícito | alta | média: solução global | baixa: estocástica | alta: cada movimento tem ganho simulado |
| Garantia de ótimo | não | não | sim, para as vagas fixadas | não | não |
| Custo computacional | alto (O(movimentos × V × Z)) | mínimo | baixo | alto | médio |
| Dependência da previsão por zona | alta | alta | alta | alta | baixa: usa dias históricos |
| Resultado no replay real | −14,6% | −15,6% | −11,8% | −14,0% | **−0,2%, sem piorar a cobertura** |

**Conclusão proposta (para validação na orientação):** o guloso continua sendo a abordagem interpretável indicada no PDF, mas o objetivo aproximado não deve guiar a decisão. A variante defensável é o **guloso com avaliação por simulação histórica**. Ela mantém a lógica passo a passo explicável e o corte D+1, e é a única que não prejudica nem KM nem cobertura. Seu comportamento mostra que, nesta operação e nesta janela, o reposicionamento preventivo quase nunca compensa o próprio deslocamento. A resposta à pergunta de pesquisa, com estes dados e premissas, é que a alocação preventiva D+1 **não reduziu** o KM morto estimado. A mudança da abordagem principal fica registrada como proposta (DT012), sem alterar DT001 até a decisão acadêmica.

## Como reproduzir e visualizar

```powershell
$env:TCC_REAL_DATA_AUTHORIZED = 'YES'
foreach ($a in 'guloso','proporcional','atribuicao_otima','busca_local','guloso_simulado') {
  .venv\Scripts\python.exe -m tcc_frota.cli gold-replay --start 2026-09-01 --end 2026-09-30 --workers 7 --details --algorithm $a
}
.venv\Scripts\python.exe -m streamlit run app\plano_d1.py --server.address 127.0.0.1
```

A página local mostra a tabela comparativa, a evolução diária e um mapa por dia: demanda prevista por zona, frota prevista e real, plano do corte, reposicionamentos executados e pedidos atendidos e não atendidos.
