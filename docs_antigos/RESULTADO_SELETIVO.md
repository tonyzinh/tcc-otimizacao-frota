# Guloso seletivo por economia líquida — resultado

**16/10/2026.** Pré-registro em [ORCAMENTO_CONFIGURACOES.md](ORCAMENTO_CONFIGURACOES.md) §5 (`0a24fed`), auditoria em [AUDITORIA_SELETIVO.md](AUDITORIA_SELETIVO.md), finalista congelado em `8bffde9` antes de qualquer dia de teste. Números de execuções registradas em `resultados/seletivo/` (sementes 11, 23, 37, 41, 53). São estimativas de simulação (Haversine × fator rua/reta calibrado, baseline simulado), não KM rodado.

## Resumo executivo

**O guloso seletivo (C2) não passou nos 5 critérios, nem em março nem em setembro, porque praticamente não move ninguém.** Nas condições estudadas, o reposicionamento preventivo não encontra oportunidades que compensem o próprio custo. Na calibração (2–15/03, 12 configurações × 14 dias × 5 sementes), 9 configurações não executaram nenhum movimento e as outras 3 executaram, em média, 0,2 a 0,4 movimento em 14 dias (+0,02% de KM vazio por corrida). O finalista pela regra pré-registrada (salto de 2 km, K = 16, τ = 1) é, na prática, o plano vazio. No teste, ele não moveu nenhum motorista em março (16 dias) nem em setembro (15 dias), nos regimes B e A: corridas e KM vazio por corrida idênticos ao baseline (0,00%, IC de largura zero). Das decisões por motorista no teste (regime B), 76–79% foram "permaneceu: sem candidato" (nenhum destino com ganho esperado ao alcance), 20–22% "sem economia", 0,6–0,8% "sem ganho de atendimento", 0,25–0,39% "reprovado na validação" e 0% "movido". Nenhuma das três variantes de previsão espacial (4.4) mudou isso, então não há C3. A referência C1 (guloso de valor marginal α = 0,2) reproduz o artigo: +9,88% de KM vazio por corrida em março e +7,83% em setembro. H-S1 não se sustenta (não há redução); H-S2 não se aplica ao C2, que não gera corridas extras.

## Tabela dos 5 critérios (teste, regime B, 04–11h)

| Cenário | Corridas mar (%) | Corridas set (%) | KM vazio/corrida mar (%) | KM vazio/corrida set (%) | Movimentos (mar; set) | C1 | C2 | C3 | C4 | C5 | Aprovado |
|---|---:|---:|---:|---:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| C0 sem reposicionamento | — | — | — | — | 0; 0 | — | — | — | — | — | referência |
| C1 guloso de valor marginal (α = 0,2) | +0,40 [−0,37; +1,20] | +2,06 [+1,21; +3,10] | +9,88 [+8,36; +11,48] | +7,83 [+5,85; +9,66] | 286; 136 | não | sim | não | não | sim | não |
| C2 guloso seletivo | +0,00 [+0,00; +0,00] | +0,00 [+0,00; +0,00] | +0,00 [−0,00; +0,00] | −0,00 [−0,00; +0,00] | 0; 0 | não | sim | não | não | sim | não |
| C3 (C2 + previsão espacial) | não existe: nenhuma variante venceu C2 na calibração | | | | | | | | | | |

C1: IC 95% do KM vazio por corrida abaixo de zero nos dois meses (com Holm). C2: limite inferior do IC das corridas ≥ −1%. C3: redução no simulador. C4: ≥ 50% dos dias com redução e regime A sem aumento. C5: plano ≤ 900 s/dia (C2: média de 7,3 s e máximo de 14,8 s em março; 2,5 s e 6,3 s em setembro). B + R = total conferido em todas as linhas. Regime A: C2 0,00% nos dois meses; C1 +3,08% (mar) e +3,27% (set). Fontes: `resultados/seletivo/finalistas_*.csv`, `tabela_criterios.csv`, `motivos_decisao.csv`; LaTeX em `tabelas/tab_seletivo_criterios.tex`; Pareto em `resultados/seletivo/pareto_C0_C3.png`.

## Discussão

- **Por que o C2 não se move.** Três em cada quatro motoristas não têm nenhum destino com ganho esperado positivo a até 2 km pelo proxy do guloso. Para os demais, a economia líquida simulada nos cenários históricos (busca evitada menos reposicionamento) não é positiva ou não supera o erro padrão. Isso é coerente com a desigualdade triangular e com a bateria anterior (DT017): o reposicionamento só reduz o total quando muda quem atende cada pedido de forma vantajosa, e isso não se repete de um dia histórico para outro.
- **A proteção contra ruído funcionou como previsto.** Só 0,25–0,49% das decisões chegaram a passar na seleção e foram reprovadas na validação; nos casos aprovados nos dois conjuntos (0,4 movimento em 14 dias, na melhor configuração), o efeito no dia real foi +0,02%. O falso ganho do exploratório (seleção sobre o ruído das sementes) não apareceu.
- **Variantes 4.4 (só calibração).** Com blocos de 3 h e com déficit persistente, nenhum movimento foi executado. Com H3 r6 e o salto de 2 km herdado do finalista, nenhum centróide r6 ficou ao alcance com ganho positivo (pré-filtro vazio). A sensibilidade a r6 com saltos maiores não foi testada (fora do pré-registro).
- **Valor líquido (Fase D).** O C2 não gera corridas extras, então *e* e o valor líquido não se definem para ele. Para C1, *e* = 68,7 km (março) e 12,7 km (setembro) por corrida extra. A comparação com *e*\* usa os custos privados (`config/custos_privado.yaml`, não publicados; tabela em `reports/runs/seletivo/`, ignorada). A tabela publicada usa a grade paramétrica dos autores (`docs_antigos/PREMISSAS_E_LIMITACOES.md`, seção 3; valores hipotéticos, não da empresa): margem de R$ 10 a 30 e c_v = r_km + r_min × 60 / v, com r_km ∈ {0,5; 1,0; 1,5}, r_min ∈ {0,15; 0,30; 0,45} e v ∈ {14; 17; 20} km/h, o que dá *e*\* de 2,9 a 31,6 km em 135 células (`tabelas/tab_equilibrio_grade.tex`). Leitura pela regra da grade: o C1 de março (*e* = 68,7 km) fica acima de *e*\* em toda a grade e não compensa em nenhuma hipótese testada; o C1 de setembro (*e* = 12,7 km) fica abaixo de *e*\* em 40 das 135 células, então o resultado depende do custo (e o limite superior do IC de *e*, 20,6 km, fica abaixo de *e*\* em só 9 células); o C2 não tem corridas extras, e a grade não se aplica a ele. *e* de todos os cenários: `resultados/seletivo/km_vazio_por_corrida_extra.csv`; classificação por cenário em `tabelas/tab_equilibrio_cenarios.tex`.
- **Movimento dos livres (Fase E, descritivo).** Motoristas livres em fotos consecutivas (≤ 11 min, 04–11h) somam em média 359 km/dia em linha reta em março (503 km × 1,4) e 361 km/dia em setembro (505 km × 1,4); 41,6% e 36,3% desses intervalos têm deslocamento > 0,5 km. O valor fica abaixo do ~595 km/dia exploratório; as duas medidas não foram reconciliadas (o código exploratório não está disponível). A causa não é atribuída. `nU_DR_REAL` e `tX_H3INDEX_REPOSICIONAMENTO_REAL` estão preenchidos em 33,5% (março) e 58,8% (setembro) das corridas encerradas. Segundo a documentação do banco da empresa (dicionário de dados, a confirmar), `nU_DR_REAL` está em metros — mediana de 2.264 m (março) e 2.508 m (setembro), ≈ 2,3 e 2,5 km — e é a estimativa espelhada (≈ 97% iguais a `NU_DR`); portanto não mede reposicionamento. Ver `docs_antigos/PREMISSAS_E_LIMITACOES.md` (limitação 3).

## Conferências

- `pytest` aprovado (ver o commit de resultados).
- Regressão do artigo: 372 linhas idênticas (`resultados/seletivo/regressao.json`).
- Não vazamento com dados reais: em 3 dias (05/03, 20/03 e 22/09), remover os pedidos reais de D+1 ou trocá-los pelos de outro dia não altera o plano (`resultados/seletivo/nao_vazamento.json`).
- Recalibração do zero de `C2|H4|K8|tau1`: corridas, KM vazio por corrida e movimentos idênticos ao registro (`resultados/seletivo/conferencia.json`).
- Seleção só na calibração: `finalistas.json` commitado antes do teste; o teste recusa rodar sem isso.
- Segunda checagem: (a) recálculo independente em NumPy (`checagem_independente.txt`) reproduz C1 e C2; (b) C2 com 5 sementes novas no teste: 0,2 movimento em março (+0,006%) e nenhum em setembro.

## Limitações

- Baseline estacionário (P1 em `docs_antigos/PREMISSAS_E_LIMITACOES.md`): os livres ficam parados entre corridas; a Fase E mostra que se movem, por motivo desconhecido. Comparar com um baseline que inclua a movimentação operacional não foi feito, pois mudaria o C0 pré-registrado.
- λ > 0 não testado (teto de 12 configurações); os cenários de demanda reamostram pedidos de dias passados e não incluem compromissos externos.
- Custos: valores internos não publicados; grade paramétrica dos autores (P10 em `docs_antigos/PREMISSAS_E_LIMITACOES.md`). A diferença entre o custo gravado pelo sistema e o recalculado fica registrada como limitação.
- Uma região, dois meses; regime B depende de escala conhecida.
