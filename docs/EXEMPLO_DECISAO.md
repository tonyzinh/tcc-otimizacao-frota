# Calculadora de decisão NB(e\*): exemplo resolvido

Código: `src/tcc_frota/v3/decisao.py`; linha de comando: `scripts/v3_decisao.py`; testes: `tests/unit/test_v3_decisao.py`.
Regra proposta pelo autor (não é política da empresa): com NB(e\*) = ΔN/dia − Δ(B+R)/dia / e\* e o IC de decisão (a mais larga das oito variantes de bootstrap por dia da Fase 1):

| Condição | Decisão |
|---|---|
| limite inferior do IC > 0 | **adotar** |
| limite superior do IC < 0 | **não adotar** |
| IC contém 0 | **inconclusivo** (o `mde_nb` informa o menor efeito detectável com 80% de poder) |

Entrada: e\* (km vazio extra aceito por corrida adicional atendida; política da empresa, hoje sem valor de referência, D-C) e, por dia, corridas atendidas e KM vazio do plano e do baseline. Não corrige múltiplos testes: use uma linha por decisão. Só lê agregados diários.

## Uso

```bash
python scripts/v3_decisao.py --csv reports/tcc_v2/fase4_dias.csv --periodo set2026 --cenario proporcional \
  --grupo "origem|B0|rho1|c1" --par "origem|B0|rho1" --e-star 30
```

Em Python: `decidir(e_star, plano, baseline)` com `DiasAgregados(datas, atendidas, km_vazio)` de cada braço (mesmas datas, mesma ordem, ao menos 8 dias).

## Exemplo 1: dados reais (setembro de 2026, proporcional contra o baseline B0, contabilização `origem`, ρ = 1, c = 1; 15 dias)

ΔN = +0,27 corridas/dia e Δ(B+R) = +24,13 km/dia [`fase4_dias.csv`]. A decisão depende de e\*:

| e\* (km por corrida extra) | NB (corridas/dia) | IC de decisão | MDE de NB | Decisão |
|---|---|---|---|---|
| 5 | −4,56 | [−5,45; −3,46] | 1,44 | **não adotar** |
| 30 | −0,54 | [−1,16; 0,06] | 0,88 | **inconclusivo** |
| 100 | +0,03 | [−0,64; 0,68] | 0,95 | **inconclusivo** |

O resultado em e\* = 30 reproduz a linha correspondente de `fase4_F4_origem_nb.csv` (NB −0,5377; IC [−1,1626; 0,0606]); há teste automático para isso. Leitura: se a empresa só aceita pagar até 5 km de KM vazio por corrida extra, o plano piora; a partir de e\* alto o benefício fica indistinguível de zero com 15 dias.

## Exemplo 2: controle positivo sintético (mundo "fora do raio", guloso α = 0,1; 16 dias)

ΔN = +48,44 corridas/dia e Δ(B+R) = +36,62 km/dia [`fase2_controle_dias.csv`].

| e\* | NB | IC de decisão | MDE de NB | Decisão |
|---|---|---|---|---|
| 5 | +41,11 | [37,16; 45,04] | 5,68 | **adotar** |
| 30 | +47,22 | [42,89; 51,56] | 6,25 | **adotar** |

Concorda com `fase2_controle_positivo_fora_do_raio_nb.csv` (NB(30) = 47,22; IC inferior = 42,89).

## Exemplo 3: controle neutro sintético (mundo "alcançável", regra de limiar; 16 dias)

ΔN = 0 e Δ(B+R) = +17,45 km/dia: o plano só acrescenta KM, então NB(5) = −0,58 com IC [−0,64; −0,51] e a decisão é **não adotar** (idem em e\* = 30, NB = −0,59).

## Limites
* O IC não é corrigido para múltiplos testes e o MDE vale para o desenho de 15–16 dias; com menos dias o resultado tende a "inconclusivo".
* Os exemplos 2 e 3 vêm de um mundo sintético; só o exemplo 1 usa dados reais agregados.
* A decisão herda a contabilização do CSV de entrada: use a coluna `empty_km` da contabilização `origem` (D-B) para a análise principal.
