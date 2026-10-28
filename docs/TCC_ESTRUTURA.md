# Estrutura proposta do TCC (28/10/2026)

Proposta, não aplicada ao artigo. Arquivos de evidência em `reports/tcc_v2/` (RELATORIO_V2.md resume todos). Texto-base do problema, hipóteses e objetivos: `docs/TCC_REFORMULACAO.md`.

## 1 Introdução
Problema (km sem passageiro, custo e emissões; **a empresa controla a frota e arca com o custo do KM vazio, e o motorista segue a recomendação com taxa de conformidade c: D-A**), pergunta falseável, hipóteses H1′–H4′, objetivos, contribuição (protocolo + diagnóstico + regra NB(e\*)) e organização. Dizer cedo que o resultado principal é um nulo bem testado e que ele é **condicional** à contabilização do regime B (os dois braços começam na última posição de D, confirmada em D-B) e a e\* sem valor de referência (D-C).
**Alimentam:** nenhuma tabela; um quadro-resumo de `fase1_inferencia_linhas.csv` (0 reduções em 162, 98 aumentos) e do controle positivo.

## 2 Fundamentação teórica
Problema de reposicionamento de frota (ride-hailing), KM morto/deadheading, previsão de demanda espaço-temporal, simulação de eventos discretos, inferência para amostras pequenas (bootstrap por blocos, Romano–Wolf/Holm, poder), benefício líquido e análise de custo marginal.
**Alimentam:** nenhum resultado; definição formal de NB(e\*) e das cinco políticas de deriva.

## 3 Trabalhos relacionados
Reposicionamento proativo e dados de táxi/ride-hailing. Incluir a **discrepância** com a literatura que reporta 53–82% menos deadheading sob estacionamento de curto prazo ilimitado e informação futura: nosso resultado parte de premissas diferentes (motorista continua despachável, paga a deriva e o reposicionamento, sem informação futura exceto no oráculo). **Não afirmar a causa**; indicar o teste que a decidiria (baseline que conta só o km com passageiro e estaciona sem custo).
**Alimentam:** `fase3_oraculo_v1_linhas.csv` (oráculo não reduz) como ponto de contato com a premissa de informação futura.

## 4 Metodologia
Dados (março e setembro de 2026, Grande Vitória; dados agregados, local, LGPD), simulador (regimes A/B/C, `fim_do_dia`, calibração, assinatura SHA-256), contabilização do KM vazio (principal: `origem`, os dois braços começam na última posição de D, confirmada em D-B; v1 bruta; "pagar nos dois" como artefato), quem arca com o custo (empresa, D-A), baselines B0–B4, ρ e conformidade, placebo, controle positivo/negativos, inferência (unidade = dia, 8 variantes de bootstrap, IC mais largo, famílias F1–F4, MDE), protocolo registrado no Git e desvios D1–D13.
**Alimentam:** `V2_PREREGISTRO.md` §12, `V2_CONTABILIZACAO.md`, `fase1_reproducao_v1.csv`, `fase1_ic_variantes.csv`.

## 5 Caracterização do problema
Estatísticas descritivas da operação (demanda por hora e zona, deslocamento noturno mediano 0,7 km e médio 3,5/5,6 km por motorista-dia, aceite vs. perdas, dispersão diária das diferenças), e quanto de KM vazio o baseline realista já gasta (B1 ≈ 875 e B3 ≈ 1 700 km/dia num dia de teste, vs. coleta ≈ 313 km).
**Alimentam:** `fase1_dispersao_*.csv`, `fase4_dias.csv`, `V2_CONTABILIZACAO.md`.

## 6 Proposta
Protocolo de avaliação (checklist: mesmos pedidos/frota/janela/distância, baseline realista, placebo, controle positivo, correção de múltiplos testes, poder) e regra de decisão por NB(e\*): "adotar apenas se o IC inferior de NB(e\*) > 0 para o e\* da operação". Os dez planejadores aparecem como instâncias, não como contribuição.
**Alimentam:** `fase1_nb.csv`, `fase1_nb_curva.csv` (figura: NB × e\*), figura do mapa de calor `fase4_mapa_calor_rho_conformidade.pdf`.

## 7 Resultados
7.1 Inferência (F1): `fase1_inferencia_linhas.csv`, `fase1_comparacao_v1_v2.csv`; tabela `tex/fase1_comparacao.tex`. 7.2 Poder e falsos positivos: `fase2_curva_poder.csv/.pdf`, `fase2_falsos_positivos.csv`. 7.3 **Controle positivo e negativos**: `fase2_controle_*` (fora do raio: ΔN +165% a +226% e NB(30) com IC inferior > 0 em sete variantes; alcançável: sem ganho, KM/corrida sobe em até 46,9%; N1/N2 com Δ = 0). 7.4 Oráculo e escada de ruído: `fase3_*`. 7.5 Baselines e placebo (F4): `fase4_F4_origem_*`, `fase4_placebo_*`, `fase4_plano_vs_placebo_*`; tabela `tex/fase4_baselines.tex`. 7.6 Grade ρ × conformidade: `fase4_grade_rho_conformidade*.csv`. 7.7 Contabilizações alternativas (artefato): `fase4_F4_pagar_nos_dois_*`.
**Regra de redação:** nunca citar a economia de "pagar nos dois braços" como resultado.

## 8 Discussão
Por que o reposicionamento não compensa: (i) o custo do movimento entra no numerador por construção e a economia máxima é uma coleta por motorista em `fim_do_dia` (visto no controle "alcançável"); (ii) o baseline realista já tem deriva; (iii) o placebo aleatório custa o mesmo que o plano; (iv) o oráculo melhora ΔN mas não KM/corrida. Quando compensaria: e\* ≥ 50 em alguns casos (F4: 2 e 5 de 100 linhas em e\* = 50 e 100), cenário "fora do raio" (gargalo de alcance), previsão e escala conhecidas. Discussão da discrepância com a literatura e das limitações (M4, setembro, B4, Bk, m1/m2).
**Alimentam:** `fase4_grade_rho_conformidade_nb.csv`, `fase2_controle_*_nb.csv`, `fase3_oraculo_vs_previsto_v1_linhas.csv`.

## 9 Considerações finais e trabalhos futuros
Resposta à pergunta (H1′ refutada para e\* ≤ 30; H4′ não refutada), contribuição metodológica, e futuro: distâncias viárias (Fase 5), terceiro período independente, planejador que conheça Bk, estacionamento de curto prazo, e\* fornecido pela empresa, controle negativo com muitas zonas (ver banca, pergunta 12).

## Ética e LGPD (seção própria ou apêndice)
Dados só agregados e processados localmente sob autorização de 14/10/2026 (restrita a processamento local); nenhum ID, coordenada individual ou bruto versionado (`reports/runs/` é ignorado); sal e flags de autorização não contornados; nada enviado ao Databricks Free Edition. O controle positivo/negativos é 100% sintético.
