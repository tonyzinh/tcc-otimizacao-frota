# Referências anotadas (busca na web, 28/10/2026)

Status: lista de trabalho. Cada entrada traz o nível de verificação:
- **V** = página de registro (editora, arXiv, RePEc ou Project Euclid) aberta nesta sessão e dados bibliográficos conferidos.
- **V-parcial** = existência e tema confirmados, mas volume, páginas ou números exatos ainda precisam ser conferidos.
- **C** = clássico que conheço, apareceu em busca por título; conferir antes de entregar.

Nenhuma afirmação sobre resultado abaixo vai além do que a página de registro (resumo) diz. **Leia o artigo antes de citar um número.**

## A. Reposicionamento e KM vazio (Capítulos 1, 3 e 9)

| # | Referência | O que mostra | Uso | Nível |
|---|---|---|---|---|
| 1 | Lindstroem, Ropke e Pourmoayed (2026) | Reposicionamento proativo reduz a espera, mas pode aumentar a distância total percorrida. É a ideia mais próxima do seu resultado nulo. | Cap. 3.2 e Cap. 9 (discussão) | V-parcial (conferir periódico e dados) |
| 2 | Kontou, Garikapati e Hou (2020). *Transp. Res. Part C*, v. 121, 102826. DOI 10.1016/j.trc.2020.102826 | Previsão de demanda + espera orientada: redução de deadheading de 53–82% **com estacionamento de curto prazo irrestrito**. | Cap. 3.2 e 3.4 (contraste de premissas) | V |
| 3 | Nair, Bhat, Batur, Pendyala e Lam (2020). *Transp. Res. Part A*, v. 135, p. 289–308. DOI 10.1016/j.tra.2020.03.015 | Infere viagens vazias (deadheading) com dados do RideAustin e modela os locais de embarque. Mostra que o padrão varia por local e hora. | Cap. 2 (definição de deadheading) e Cap. 3.2 | V |
| 4 | Henao e Marshall (2019) | Mede a fração de deadheading em operação real de ride-hailing (40,8% no resumo que li). | Cap. 1 (justificativa: tamanho do problema) | V-parcial (conferir periódico e escopo) |
| 5 | Akbari et al. (2026) | Revisão sobre viagens vazias. | Cap. 2 e 3 (panorama) | V-parcial |
| 6 | Fagnant e Kockelman (2018). Dynamic ride-sharing and fleet sizing for a system of shared autonomous vehicles in Austin, Texas. *Transportation*, v. 45, p. 143–158. DOI 10.1007/s11116-016-9729-z | Simulação baseada em agentes. No caso-base, a distância total pode superar a demandada por causa do reposicionamento vazio entre chamadas. | Cap. 3.2 (o reposicionamento tem custo próprio) | V |
| 7 | Jiao, Tang, Qin, Li, Zhang, Zhu e Ye (2021). Real-world ride-hailing vehicle repositioning using deep reinforcement learning. *Transp. Res. Part C*; arXiv:2103.04555 | Aprendizado por reforço profundo para reposicionamento; ganho em renda por hora em simulação e experimento real (o resumo não traz números). | Cap. 3.2 e trabalhos futuros | V |
| 8 | Miao et al. (2016), Zhang e Pavone (2016), Alonso-Mora et al. (2017) | Despacho com horizonte retrocedente; filas para rebalanceamento; pareamento de alta capacidade. | Cap. 3.2 | **Só título.** Ler antes de citar |

## B. Simulação, previsão e roteamento (Capítulos 2 e 3)

| # | Referência | O que mostra | Uso | Nível |
|---|---|---|---|---|
| 9 | Revisões de simulação e de reposicionamento (DTS 2023; Liu et al. 2022; Lin et al. 2018; Saadi et al. 2017) | Panoramas e métodos de alocação em mobilidade sob demanda. | Cap. 2 | V-parcial: confirmei existência e tema; completar autores e periódicos |
| 10 | Syed et al. (2021); Fakhrmoosavi et al. (2024) | Estudos de ride-hailing/reposicionamento achados na rodada 1. | Cap. 3.2 (se confirmarem relevância) | V-parcial |
| 11 | Krohling (2025) e Pimentel (2025) (dissertações UFES do projeto) | Previsão de trajetórias por célula; VRP com heurística híbrida. | Cap. 3.1 e 3.3 | V (lidas) |
| 12 | Dantzig e Ramser (1959); Ropke e Pisinger (2006); Toth e Vigo (2014) | VRP, ALNS e livro de referência. | Cap. 3.1 | V no Cap. 3 anterior |

## C. Inferência e métodos estatísticos (Capítulo 4)

| # | Referência | Para que serve no TCC | Nível |
|---|---|---|---|
| 13 | Efron, B. (1979). Bootstrap methods: another look at the jackknife. *The Annals of Statistics*, v. 7, n. 1, p. 1–26. DOI 10.1214/aos/1176344552 | Bootstrap por dia | C (título confirmado em busca; página do Project Euclid falhou) |
| 14 | Künsch, H. R. (1989). The jackknife and the bootstrap for general stationary observations. *The Annals of Statistics*, v. 17, n. 3, p. 1217–1241. DOI 10.1214/aos/1176347265 | Justifica reamostrar blocos se houver dependência entre dias | V |
| 15 | Politis, D. N.; Romano, J. P. (1994). The stationary bootstrap. *JASA*, v. 89, n. 428, p. 1303–1313 | Alternativa de bootstrap para séries dependentes | V-parcial (conferir páginas) |
| 16 | Romano, J. P.; Wolf, M. (2005). Exact and approximate stepdown methods for multiple hypothesis testing. *JASA*, v. 100, n. 469, p. 94–108 | Correção por família (Romano–Wolf) | V (RePEc; o número 469 é o de março de 2005, conferir) |
| 17 | Holm, S. (1979). A simple sequentially rejective multiple test procedure. *Scandinavian Journal of Statistics*, v. 6, n. 2, p. 65–70 | Correção de Holm | C |
| 18 | Fieller, E. C. (1954). Some problems in interval estimation. *JRSS B*, v. 16, n. 2, p. 175–185 | Intervalo de razão (e* implícito); seus intervalos ilimitados em 126 de 162 casos têm base aqui | C (**não confirmei**; conferir) |

## D. Pontos de atenção

1. **O mais importante.** Lindstroem et al. (2026) apoia a leitura de que reposicionamento pode reduzir espera sem reduzir distância. Leia o artigo inteiro antes de usá-lo como argumento: é isso que sustenta que o seu nulo não é um acidente do seu simulador.
2. **A lacuna ainda não está provada.** Esta busca não foi sistemática no sentido formal. Para afirmar "não encontrei avaliação com placebo e controle positivo" você precisa registrar bases (Scopus, Web of Science, IEEE Xplore, Google Scholar), termos, período e critérios. Sugestão de string: `("vehicle repositioning" OR "fleet rebalancing" OR "empty vehicle" OR deadheading) AND ("ride-hailing" OR taxi OR "mobility on demand") AND (placebo OR "negative control" OR baseline OR "multiple testing")`. Registre data, número de resultados e motivo de exclusão.
3. **Não achei** (nesta busca) fonte para: simulação de eventos discretos específica para frota controlada, ou metodologia de placebo/controle positivo aplicada a algoritmos de despacho. Se a banca perguntar, a resposta honesta é que a inspiração vem de avaliação causal e de testes de simulador, não de literatura de despacho. Procure em *negative controls* (epidemiologia, avaliação causal) para o Cap. 4.
4. **Pendências de [CONFERIR]:** Miao, Zhang e Pavone, Alonso-Mora; Garcia et al. (nomes e páginas); Krohling (2024 ou 2025); periódicos de Lindstroem, Henao e Marshall, Akbari.
5. **Evitar:** Ma e Wang (2022), retratado; estatísticas do documento "Conhecimento" sem fonte primária.
