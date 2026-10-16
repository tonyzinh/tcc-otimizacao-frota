# Auditoria antes do guloso seletivo (Fase A)

**16/10/2026, código `1c0ad3e` (árvore limpa).** Leitura somente. Complementa [AUDITORIA_BATERIA.md](AUDITORIA_BATERIA.md), escrita poucas horas antes sobre o mesmo código; aqui entra só o que muda para esta tarefa.

## 1. O que já existe e será reaproveitado

| Peça | Onde | Situação |
|---|---|---|
| Simulador de eventos discretos (fila, paciência, raio, compromissos, reposicionamento no fim de D ou no início do turno) | `src/tcc_frota/v2/sim.py` | Determinístico; uma simulação de dia × janela 04–11h leva ~16 ms. |
| Baseline C0 | `simulate(..., moves=None)` | Motorista livre mais próximo, sem reposicionar. |
| Guloso de valor marginal S = ΔV − α·d (C1), proporcional, limiar | `src/tcc_frota/v2/policy.py` | Referências do artigo; C1 = α = 0,2, ρ = 2,5 km, limite 3 km. |
| Regimes A/B/C | `src/tcc_frota/v2/fleet.py` | B principal; A robustez; C não usado. |
| Estatística pareada (bootstrap de dias, permutação), Holm e IC de Bonferroni | `v2/stats.py`, `algoritmos/estatistica.py` | Reaproveitada. |
| **Interface de planejador** | `src/tcc_frota/algoritmos/base.py` (`Planner.plan(contexto) -> {motorista: (lat, lng, km)}`) | Já criada na bateria (DT017), com regressão. |
| Avaliador diário, calibração, congelamento e teste | `algoritmos/bateria.py`, `algoritmos/protocolo.py` | Reaproveitados. |
| Pseudodias históricos sem D+1 (dias de treino do mesmo dia da semana, anteriores a D) | `bateria.scenario_days`, `build_scenarios` | Base para os cenários de 4.3. |

**Regressão (reexecutada nesta fase):** a interface reproduz o `final-run 20261016T013428Z` dia a dia (372 linhas, regimes A e B, testes de março e setembro), e o simulador recalibrado é igual ao congelado. Na tabela de teste da bateria, o guloso α = 0,2 em março dá +9,88% [+8,36; +11,48] de KM vazio total por corrida, o mesmo valor do artigo. Log: `resultados/seletivo/regressao.json`.

**Bateria anterior (DT017, `docs/BATERIA_ALGORITMOS.md`):** 13 algoritmos, nenhum reduziu o KM vazio por corrida. As famílias avaliadas no simulador sobre pseudodias já convergiam para "não mover". O guloso seletivo é a última tentativa registrada, como pede a tarefa.

## 2. Dados e parâmetros

- Extratos em `data/raw/` (não tocados), Silver e Gold locais reconstruídas em ~30 s. Calibração do simulador: março com raio de 4,5 km, paciência de 180 s, fator rua/reta de 1,301 e 16,08 km/h; setembro com 4,0 km, 120 s, 1,384 e 16,57 km/h.
- Previsão D+1 (média do mesmo dia da semana, 56 dias, sem Carnaval). WAPE zona-hora de 0,967 na calibração de março; WAPE do total da janela no teste de setembro de 21,3% (`reports/tcc_final/tab07_erros_previsao.csv`). Os números do PDF conferem.
- Campos `nU_DR_REAL` e `tX_H3INDEX_REPOSICIONAMENTO_REAL` já estão na Silver como `nu_dr_real_pendente` e `fl_h3_repos_real_pendente` (semântica não confirmada; só descritivo na Fase E).
- Snapshots da frota (a cada 10 min, estado 1 = livre) em `gold.frota_snapshot`, com motorista pseudonimizado. Não serão cruzados com as corridas.

## 3. Testes

`pytest`: 162 aprovados, 1 pulado (preexistente).

## 4. Dúvidas bloqueantes

Nenhuma.

## 5. Decisões de preferência (registradas)

1. **Evidência exploratória ausente.** `referencia_exploratoria/sel.py` e `sel_hold.py` não existem no repositório. Os números do pedido (−1,1% em amostra; +2,6% nos dias 16–31) ficam como orientação não citável e não reproduzida.
2. **Saídas em `resultados/seletivo/`**, para não sobrescrever os arquivos da bateria (`resultados/finalistas_*.csv`). O registro de configurações continua único (`resultados/registro_configuracoes.csv`).
3. **Cenários de 4.3.** Os dias do mesmo dia da semana nos 56 dias anteriores ao corte (excluído o dia D, incompleto às 20h) são divididos por recência: a metade mais recente gera os cenários de **seleção** e a mais antiga os de **validação** (conjuntos de dias disjuntos). Cada cenário = um dia sorteado com reposição dentro da metade + reamostragem *bootstrap* dos pedidos desse dia, com semente fixa por cenário. O mesmo cenário é simulado com e sem cada movimento (variáveis aleatórias comuns). A frota é a do regime (escala e posição de partida; horário previsto), sem compromissos, que não são conhecidos no corte.
4. **Grade de 12 configurações:** H ∈ {2; 3; 4} km × K ∈ {8; 16} × τ ∈ {1; 2}, com λ = 0. A restrição "corridas esperadas ≥ baseline esperado" vale nos dois conjuntos. Com λ = 0, a perda de corridas fica só como restrição; um λ > 0 fixo exigiria 24 configurações e passaria do teto de 12, então fica registrado como **não testado**.
5. **Pré-filtro:** pares motorista → centróide a até H km com ΔV > 0 no proxy do guloso atual (ρ = 2,5 km), em ordem de ΔV; no máximo M = 30 por iteração; cache de simulações por plano e cenário.
6. **C1 = guloso de valor marginal α = 0,2** (intermediário do artigo). Holm entre C1, C2 e C3 (quando houver C3), por mês.
7. **4.4 (sensibilidade):** três variantes rodam só na calibração, com os demais parâmetros do finalista C2. C3 existe somente se alguma variante vencer C2 pela mesma regra. As três contam no registro como configurações à parte.
8. **Custos (Fase D)** ficam em `config/custos_privado.yaml`, que passa a ser ignorado pelo Git. Tabelas publicadas usam só uma grade paramétrica genérica; a tabela com os valores da empresa fica em `reports/runs/seletivo/` (ignorado).
