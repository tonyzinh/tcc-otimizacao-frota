# Premissas e limitações

**Substitui `docs/PERGUNTAS_EMPRESA.md`.** Data: 16/10/2026.

Este documento registra o que o estudo **assume** porque a empresa ainda não confirmou. Nenhuma resposta da empresa foi recebida. Nada aqui é posição da empresa, e nenhum valor financeiro interno é publicado. As lacunas vêm de `docs/REGRAS_NEGOCIO_TCC.md` (L1–L5) e do dicionário do banco da empresa.

## 1. Premissas adotadas

| ID | Premissa | Por que é premissa | Como o estudo a trata | Efeito se for falsa |
|---|---|---|---|---|
| P1 | Entre corridas, o motorista livre permanece onde terminou a última corrida (baseline estacionário, C0) | O repositório da empresa não documenta política de espera nem de reposicionamento (L4, RN019, RN021). As fotos da frota mostram livres se movendo (359–361 km/dia em linha reta), mas não dizem o motivo | Declarada como simplificação. Resultados valem **contra este baseline**, não contra a operação real | Se a operação já reposiciona, o ganho possível do algoritmo é menor ou outro, e o KM vazio do baseline está subestimado |
| P2 | KM vazio = busca (pickup) + reposicionamento. Retorno obrigatório, abastecimento, manutenção e troca de turno ficam fora | Definição oficial de KM morto pendente (L1, RN010). A planilha de custos da empresa separa "KM Pickup" e "KM Morto", mas o repositório não diz como o segundo é calculado | Definição **dos autores**, rotulada "proposta"; B e R reportados separadamente | Se a empresa incluir retorno ou abastecimento, o total muda, mas o contraste entre cenários só muda se esses km diferirem entre eles |
| P3 | Distâncias do simulador são estimadas: Haversine × fator rua/reta calibrado. Não são km rodados | Não há GPS nem odômetro por trecho no repositório. `NU_DP` e `NU_DR_REAL` são a estimativa, não medição (96,8–100% iguais) | Todo resultado é "KM vazio estimado em simulação". Pickup real, `NU_DISTANCIA_ACEITE_CHEGUEI`, usado só para calibrar | O nível absoluto do KM vazio pode estar errado. O erro é igual nos dois cenários, mas a razão entre eles pode mudar |
| P4 | A demanda é a das corridas observadas (encerradas, PF, imediatas, 04–10h59, região 1). Não inclui pedidos não atendidos nem demanda suprimida | Extrato com `NaoAtendida` e `LimiteEsperaAtingido` e hora de criação do pedido não está disponível (L2, RN004, RN005) | Cobertura reportada como **condicional às corridas observadas**; sem alegar efeito sobre a demanda total | Corridas extras simuladas podem não existir como demanda real |
| P5 | A hora de cada pedido é a registrada no extrato. `DT_REGISTRO` é carimbo da linha de status (RN023) | Pode deslocar pedidos próximos à meia-noite; a janela 04–11h está longe da meia-noite | Verificar na extração qual carimbo foi usado e declarar | Efeito pequeno nesta janela; maior se a janela for ampliada |
| P6 | Os veículos livres e a escala em D+1 são conhecidos (regime B). O regime C (oráculo) não é limite superior | Histórico de jornada, pausa e vínculo veículo–motorista não é reconstruível com segurança (L3, RN016) | Regimes A/B/C explicitados; B é o principal | Em operação real a escala de D+1 pode mudar e reduzir o ganho |
| P7 | Veículos e motoristas são intercambiáveis; sem restrição de categoria, assento ou acessibilidade | Cadastro e compatibilidade não verificados (RN015) | Declarada como simplificação | Atribuições podem ser inválidas na prática |
| P8 | Adesão de 100% às recomendações | Não há taxa de adesão medida | Resultado é "cenário ideal", nunca eficácia observada | Adesão menor reduz o ganho (e o custo) proporcionalmente |
| P9 | Março (2–31/03) e setembro de 2026 são tratados como regimes distintos e não são agregados | Em 13/06/2026 o preço dinâmico entrou em PF e o preço fixo (viagem longa) foi desligado só para PF. O perfil das corridas muda entre os meses | Cada mês reportado separadamente; diferenças entre meses não são atribuídas a causa | Comparação direta de níveis entre março e setembro é enganosa |
| P10 | Custo por km vazio e margem por corrida são **parâmetros hipotéticos definidos pelos autores**, em grade, não valores da empresa | Custo marginal real e repasse ao motorista não informados (RN022, RN029). Os parâmetros de precificação do sistema não são custo contábil | Ponto de equilíbrio e* apresentado como grade (ver 3). Resultados em R$ só como cenários | Conclusão econômica da H3 depende da grade, não de um valor único |
| P11 | Fuso dos carimbos igual ao horário local (Brasília) | Fuso de origem pendente (RN024) | Declarada | Deslocamento de faixas horárias |
| P12 | Nome da empresa e valores internos não constam no texto | Autorização escrita pendente | Dados pseudonimizados; só agregados publicados; valores internos fora do repositório público | — |

## 2. Limitações do estudo

1. **Baseline estacionário** (P1). A fase descritiva mostra que os livres se movem; não se sabe por quê. O estudo não compara contra a movimentação operacional real. Isso é a principal ameaça à validade.
2. **Sem KM rodado.** Tudo é estimativa de simulação (P3). Nenhum percentual é economia realizada.
3. **Campos de reposicionamento não são medição.** `nU_DR_REAL` está em metros e é cópia da estimativa em ~97% das corridas; `tX_H3INDEX_REPOSICIONAMENTO_REAL` não tem semântica confirmada. O estudo os usa só de forma descritiva (cobertura 33,5% em março e 58,8% em setembro das corridas encerradas) e **não** os interpreta como taxa de reposicionamento.
4. **Demanda observada apenas** (P4). A cobertura é condicional.
5. **Uma região, dois meses.** Sem feriados, sazonalidade longa nem outras modalidades (Prime, PJ, agendadas, viagens estaduais).
6. **Custo e margem paramétricos** (P10). Não há custo marginal validado; o custo gravado pelo sistema e o recalculado diferem em ≈ R$ 0,85 por corrida (R$ 0,43 + R$ 0,42). Parte pode vir do tempo estimado no custo do motorista, mas isso não foi testado.
7. **Seleção sobre ruído.** A seleção de configurações foi feita só na calibração, com finalista congelado antes do teste. Resultados exploratórios (≈ 60 configurações em 14 dias) mostraram falsos ganhos que sumiram no teste.
8. **λ > 0 e blocos maiores de previsão não foram testados** (teto de 12 configurações pré-registrado).
9. **Resultado negativo.** Nenhum algoritmo testado reduziu o KM vazio por corrida mantendo o atendimento. O guloso seletivo praticamente não move ninguém. Isso é resultado, não falha de execução.

## 3. Grade paramétrica do ponto de equilíbrio (definida pelos autores)

Critério: uma corrida extra compensa se a margem dela, antes do km vazio, supera o custo dos km vazios extras. Com custo por km vazio `c_v = r_km + r_min × 60 / v` e `e* = margem / c_v`, comparar com o KM vazio por corrida extra `e` observado em cada cenário.

- Valores **hipotéticos**, em passos redondos, escolhidos pelos autores para cobrir uma faixa ampla (por exemplo r_km de 0,5 a 1,5 R$/km, r_min de 0,15 a 0,45 R$/min, margem de 10 a 30 R$, v de 14 a 20 km/h). **Não** derivados de resposta da empresa.
- Publicar `e*` como tabela cruzando margem e `c_v`, sem indicar qual célula é a "da empresa".
- Os valores internos ficam só em `config/custos_privado.yaml` e em `reports/runs/` (ambos fora do git) e podem ser consultados na defesa, se a empresa autorizar.
- Regra de leitura: se `e` (corrida extra) está acima de `e*` em toda a grade, o cenário não compensa em nenhuma hipótese testada; se abaixo em toda a grade, compensa; se cruza, o resultado depende do custo, e o texto diz isso.

## 4. Perguntas que continuam abertas (não bloqueiam o estudo)

1. Como a coluna `KM Morto` da planilha de custos da empresa é calculada e o que ela inclui (pickup, retorno, reposicionamento, abastecimento)?
2. O que significa status livre em movimento e existe orientação operacional de reposicionamento?
3. Qual é o custo marginal de um km vazio e o repasse ao motorista, para PF, em março e setembro de 2026?
4. Autorização escrita para (a) uso agregado e pseudonimizado dos extratos no TCC e no artigo e (b) citar ou não valores financeiros.

Enquanto não houver resposta, valem as premissas da seção 1. Se vier resposta, registrar aqui com data e remetente, e só então ajustar o C0 e refazer o que for afetado.
