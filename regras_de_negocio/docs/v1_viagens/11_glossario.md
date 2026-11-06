# 11 — Glossário

| Termo | Significado no repositório |
|---|---|
| **V1 / V1 Viagens / V1 Mobilidade** | A empresa/app de mobilidade urbana (Grande Vitória/ES) |
| **PF** | Pessoa Física: `CD_EMPRESA IS NULL`; só região 1 |
| **PJ Padrão / PJ Customizado** | Cliente corporativo em tabela padrão / com tarifa contratada (`FIN_PARAMETRO_PAGAMENTO.TX_TIPO`) |
| **PJ Fixo** | Fluxo de preço fixo (cotação em `APP_ESTIMATIVA_PRECO_FIXO_PRINCIPAL`) |
| **Prime** | Assinatura de horas com frota dedicada (planos Start/Individual/Essencial/Plus/Familiar/Corporativo) |
| **Prioridade (V1 Prioridade)** | Opção de serviço no app além do "Serviço padrão V1" |
| **Região 1** | Grande Vitória (`CD_REGIAO = 1`) |
| **DV** | Distância da **viagem** com passageiro (`NU_DISTPERCORRIDA`, metros) |
| **DP** | Distância do **pickup** (motorista até o cliente). Realizado = `NU_DISTANCIA_ACEITE_CHEGUEI`; ⚠ `h.NU_DP` é estimativa |
| **DR** | Distância do **retorno** vazio. Só estimativa (`e.NU_DR`); `NU_DR_REAL` ≈ estimativa |
| **ETA** | Tempo estimado: `NU_ETA_TEMPO_SEGUNDOS` = até o cliente; `…_PROXIMA_SEGUNDOS` = "retorno" |
| **Pickup (a) / (b)** | (a) deslocamento `ACaminho→Chegou`; (b) com espera `ACaminho→Iniciada` |
| **Espera cliente** | Cláusula que cobra carro parado aguardando embarque (`DE_VL_ESPERA`) |
| **Minuto parado** | Cláusula que cobra parada após iniciar a viagem (`DE_VL_MINUTOPARADO`) |
| **Bandeirada** | Componente fixo do preço |
| **σ (sigma)** | Fator de equilíbrio operacional do preço (`DE_FATOR_EQUILIBRIO_OPERACIONAL`/`DE_SIGMA`) |
| **P*_A / P*_B** | Preço mínimo pela Formulação A (MC02 R$/h) / B (markup %) |
| **Piso** | R$ 16 — preço mínimo por corrida |
| **Banda de cupom** | Intervalo entre P*_A e o teto (`M_h_max`), folga para desconto |
| **MC 0.1 / 0.2 / 0.3 / MC1** | Margens de contribuição em camadas (viagem → pickup → improdutivo → indireto). **MC02 = MC 0.2** |
| **MC02/h** | MC02 ÷ horas de frota alocada. Alvo: R$ 25–40/h conforme documento |
| **Fat/Hr** | Receita bruta por hora de frota alocada (R$ 62,59 em mar/2026; alvo 91,03) |
| **RB / RL** | Receita bruta / líquida (RL = RB·(1−d)) |
| **MO / GG / MT** | Mão de obra / gastos gerais / manutenção e materiais (DRE da BD) |
| **KM morto** | Km sem passageiro. **Não medido**; definição corporativa pendente (pickup? entre corridas? retorno?) |
| **Frota alocada** | Tempo em que o carro está comprometido: de `CondutorACaminho` até o fim |
| **Hora-carro** | Horas de carro ocupado |
| **Sweep-line** | Algoritmo de contagem de simultaneidade (+1/−1 em ordem cronológica) |
| **Fator de concentração** | Pico ÷ carga; mede quanto a frota dedicada ficaria parada entre picos |
| **Nível de serviço** | % das corridas de hoje que a frota dedicada atenderia |
| **Transbordo** | Demanda Prime que **sai** da frota (corrida Prime em placa de fora) |
| **Cessão** | Capacidade Prime gasta com outra demanda (corrida não-Prime em placa da frota Prime). *"Transbordo reverso" é proibido* |
| **Apto** | Motorista presente e fora de corrida no instante do despacho (a auditoria de 11/09 discute se mede aptidão) |
| **Escala fantasma** | Escalas com ~100% de jornadas sem corrida (operação fora das tabelas analisadas) |
| **Ciclo (Prime)** | Período mensal de franquia (`APP_CICLO_PRIME`) |
| **Franquia** | Minutos por ciclo do plano (`NU_MINUTO_CICLO`) |
| **Titular / dependente** | Usuário do plano Prime / usuários vinculados (0..n) |
| **Simultaneidade** | Titular e dependente do mesmo plano com 2+ carros ao mesmo tempo |
| **Auto-sobreposição** | A mesma pessoa em 2 carros ao mesmo tempo |
| **DiD** | Diferença em diferenças (tratados PF/PJ Padrão × controle PJ Customizado/Prime) |
| **Placebo** | Corte falso de data para testar se grupos andavam juntos (efeito >4 pp invalida) |
| **Same-store** | Ticket calculado nas mesmas células antes/depois (evita viés de mix) |
| **Heavy users** | Clientes PF de uso intenso (cluster 0) |
| **CRM PF** | Estratégia de retenção por segmentos de valor/risco |
| **H3** | Índice hexagonal geoespacial (Uber); usado em API Sigma e análise de bairros (resolução 8) |
| **OSRM** | Motor de roteamento usado opcionalmente para o traçado real |
| **Sigma (API)** | API de rotinas V1 para listar motoristas logados e alterar o preço dinâmico |
| **D+1** | Plano feito no dia D para o dia seguinte (TCC) |
| **RS / RESULT SET** | Cada grade de resultado de uma consulta; vira um CSV pelo banner |
| **Banner** | Linha `-- >>> RESULT SET N -> salvar como: <arq>.csv` |
| **C1…C10** | Consultas numeradas do `diagnostico_novo_preco_v1` |
| **FP&A** | Planejamento e análise financeira (dono dos parâmetros de custo) |
| **VIX Matriz** | Sufixo no nome de autores de commit; contexto institucional não explicado |
