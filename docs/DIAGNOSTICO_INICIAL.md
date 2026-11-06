# Diagnóstico inicial (06/11/2026)

Documento **mutável**: registra o que foi examinado nesta data. Não é regra; as regras estão em `CLAUDE.md` e `.claude/rules/`. Atualize ou substitua por um diagnóstico datado novo quando o estado mudar.

## 1. Como foi feito

Lidos: instruções existentes (`CLAUDE.md`, `AGENTS.md`, quatro regras, três skills, `settings.json`), memória do projeto, `VERSOES_E_EXPERIMENTOS`, `ESCOPO_FECHADO`, `V2_PREREGISTRO` (início), `TCC_REFORMULACAO` (início), `TCC_PARECER_ORIENTADOR`, `limitacoes`, `RELATORIO_V2` (início), cabeçalho da auditoria de 25/10, resumo do artigo, `PENDENCIAS.md` do artigo, `config/experiment.yaml`, docstrings e trechos de `v2/sim.py`, `v2/policy.py`, `v2/fleet.py`. **Não executado:** `pytest` não foi rodado depois da criação destas instruções; nenhum experimento foi reexecutado; nenhum dado real foi aberto.

## 2. Entendimento atual do projeto

- **Pergunta (vigente no código e no artigo):** um plano de reposicionamento D+1, feito com informação anterior ao corte, reduz o KM vazio por corrida atendida sem reduzir o atendimento? Dados reais de março e setembro/2026, Grande Vitória, janela 04–11 h, simulação de eventos discretos.
- **Resultado registrado (não revalidado hoje):** nenhum planejador que de fato moveu a frota reduziu o KM vazio por corrida; a extensão v2 (28/10) confirma com baselines B0–B4, oráculo de demanda, placebo e controle positivo sintético; a auditoria de 25/10 julgou o nulo estatisticamente robusto, mas não as afirmações além dele (troca de km por atendimento, "13 algoritmos", "pré-registrado").
- **Reformulação em curso:** de "algoritmo que reduz KM" para "protocolo de avaliação + regra de decisão NB(e\*)" (`TCC_REFORMULACAO.md`).
- **Pedido novo (06/11):** reconstruir o guloso com formulação e dados melhores, possivelmente com novas fontes de dados. Escopo ainda não aprovado em detalhe (ver R-01 e R-02).
- **Estrutura de código:** núcleo local Python; `v2/` = rodada final, `v3/` = extensão, `algoritmos/` = bateria e seletivo. Databricks, frontend e Streamlit foram removidos em 06/11.

## 3. Divergências (texto × código × evidência)

| # | Divergência | Versões e evidência | Situação |
|---|---|---|---|
| D1 | Quem é a frota | Pedido de 06/11: "frota própria". `TCC_REFORMULACAO` §1 (decisão D-A): empresa controla e paga o KM; motorista segue com conformidade c. Parecer A3: documentos e dados falam de motoristas que aceitam corridas. Dados brutos **sem** campo CLT/PJ | Aberta; premissa não confirmada com a empresa |
| D2 | "Operação manual" | O baseline é despacho ao mais próximo com raio/fila/paciência calibrados (`v2/sim.py`; `limitacoes.md` §8), não reconstrução da operação manual | Rotular como baseline simplificado |
| D3 | Deslocamento instantâneo | `move_mode="fim_do_dia"` (regime B primário) move o motorista entre sessões em tempo zero, somando KM (`v2/sim.py`, evento `sess_start`) | Premissa a declarar no texto; não é bug provado |
| D4 | Posição dos ociosos | Ociosos ficam parados no simulador; na realidade circulam (`limitacoes.md` §11) | Limitação declarada |
| D5 | Ganho esperado × simulado | Auditoria 25/10: ganho esperado do planejador 6–60× o simulado; WAPE da previsão ≈ 0,9–1,0, não melhor que prever zero | Problema de formulação; central para o guloso |
| D6 | Validação do simulador | 28/10 (memória; `resultados/validacao_simulador/` **ausente** do disco): subestimação do pickup vem do despacho; Δ% inflado ~2 pp (+9,9→+8,0 mar; +7,8→+6,0 set); sem mudança de sinal | Evidência perdida do disco; reconstruir via `scripts/validar_simulador.py` com dado autorizado |
| D7 | F1 × H1′ | F1 mostra NB>0 com IC positivo em e\*=20 (3 linhas) e 30 (9); H1′ foi dada como refutada pela F4 (parecer A5) | Explicar contabilização de cada família |
| D8 | Reformulação × artigo | `TCC_REFORMULACAO` diz "não aplicada ao artigo"; o resumo já cita NB(e\*), placebo, oráculo e contribuição metodológica | Verificar o texto completo do artigo |
| D9 | "Última tentativa" × reconstrução | Memória: o proprietário declarou o seletivo C2 a última tentativa (16/10). Pedido de 06/11 pede reconstrução do guloso | Pedido mais recente prevalece; confirmar (R-01) |
| D10 | Origem do parecer | `TCC_PARECER_ORIENTADOR.md` se descreve como "parecer de orientação"; a autoria (orientador humano ou assistente) não é verificável pelo repositório | Não citar como posição do orientador sem confirmação |
| D11 | Instruções × arquivos | `CLAUDE.md`/`AGENTS.md`/regras/skills antigos citavam matriz RN, `CONTEXTO_PROJETO`, `ESTADO_PROJETO`, `DECISOES_TECNICAS` e `.codex/workflows/*`, hoje ausentes | Instruções reescritas; skills ainda apontam para ausentes |
| D12 | Caches de código | `gold-replay` exige cache da Gold; `gold-export` (único gerador) foi removido em 06/11 | Experimento legado (DT011–012) não reproduzível por este código |
| D13 | Documentos que afirmam Databricks | `limitacoes.md` §17, `AUDITORIA_BATERIA.md`, `GUIA_COMPLETO` e outros ainda descrevem execução no workspace, hoje removida | Histórico; marcar na próxima revisão |

## 4. Lacunas de dados que impedem decisões

1. **Matriz de regras RN e decisões DT ausentes**: status (CONFIRMADA/PROPOSTA/PENDENTE) de 45+ códigos citados não é verificável.
2. `dT_REGISTRO` é *proxy* do instante de criação; semântica do enum de estado do motorista é inferida (DT010).
3. Escala/turno conhecido na véspera (premissa do regime B): não confirmada. Posição inicial da sessão está em média a 3,5 km (mar) e 5,6 km (set) da última posição de D.
4. Política real de despacho e de posicionamento manual: não documentada; sem ela o baseline não representa a operação.
5. Circulação e retorno: não observados (KM de retorno não medido). Só pickup e reposicionamento são medidos/estimados.
6. Custo por km e margem por corrida; logo e\* continua parâmetro de política sem valor de referência.
7. Rede viária: Haversine × fator; OSM (fase 5) exigiria autorização de download.
8. Terceiro mês independente de teste (fase 6) inexistente; poder de 32–58% para ΔN = 1% com 15–16 dias.
9. Demanda suprimida e agendadas fora do universo; vínculo motorista × veículo e CLT/PJ sem campo.
10. "Novas fontes de dados" mencionadas no pedido: **não identificadas** no repositório.

## 5. Materiais não acessíveis ou não lidos

PDF original do TCC (fora do repositório); normas institucionais, orientações do professor e limite de páginas confirmado; `docs/REGRAS_NEGOCIO_TCC.md`, `CONTEXTO_PROJETO.md`, `ESTADO_PROJETO.md`, `DECISOES_TECNICAS.md`, `PLANO_IMPLEMENTACAO.md`, `dicionario_dados.md`, `validacao_regras.md`, `PERGUNTAS_EMPRESA.md`, `NOTA_EVOLUCAO_VERSOES.md`, `.codex/`, `.ref/`, `reports/runs/`, `reports/thesis_final/`, `resultados/validacao_simulador/`; `data/raw` (portão e privacidade; não aberto); seções 1–6 do artigo e `main.pdf` (lidos só o resumo e `PENDENCIAS.md`); código dos algoritmos além de `v2/policy.py`, `v2/sim.py`, `v2/fleet.py`.

**Incidente:** em 06/11/2026, durante a limpeza do repositório, diretórios sumiram do disco sem causa identificada (tracked foram restaurados com `git restore`). Arquivos ignorados pelo git continuam perdidos, a menos que recuperados da lixeira ou do histórico de versões do OneDrive. Backup das instruções antigas fora do repositório: pasta de rascunho da sessão (`backup_instrucoes_2026-11-06`).

## 6. Cinco próximas ações

1. **Recuperar** os documentos ausentes (lixeira/versões do OneDrive) e fazer cópia fora do `.gitignore` de `CLAUDE.md`, `.claude/`, `AGENTS.md`; só então confiar nos códigos RN/DT.
2. **Decidir com o proprietário**: premissa de frota/custo (D1), escala conhecida (regime B), valor de referência de e\* e o escopo aprovado da reconstrução do guloso (R-01, R-02).
3. **Auditar a formulação antes de codificar:** aplicar o checklist de `otimizacao-de-frota.md` a `v2/policy.py` (somente leitura), explicar o fator 6–60× e nomear o mecanismo de economia plausível (D5).
4. **Dicionário de dados** com ocorrência × disponibilidade para os campos usados, incluindo qualquer fonte nova; separar previsão de demanda, de oferta e estado observado.
5. **Tratar o simulador** (D3, D4, D6): declarar ou corrigir deslocamento em tempo zero e ociosos parados; reconstruir a validação perdida; só depois congelar o protocolo (treino/validação/teste independente, sementes, critérios) da nova campanha.
