#!/usr/bin/env bash
# Fluxo Elasticsearch (sistema distinto do ODS). Mesma prioridade; lotes prontos são pulados; falhas repetem até 3 vezes.
set -u
cd "$(dirname "$0")/.."
es() { ODS_ENT=" " ES_ENT="$1" scripts/extrair_v1_periodo.sh "$2" "$3"; }
for t in 1 2 3; do
  {
    es "posicao_ofertas" 2026-03-07 2026-03-13
    es "posicao_ofertas sumario_ofertas reposicionamento_sugerido" 2026-02-01 2026-03-31
    es "posicao_ofertas" 2025-12-07 2026-01-31
    es "posicao_ofertas sumario_ofertas reposicionamento_sugerido" 2026-09-16 2026-10-25
    es "posicao_ofertas" 2026-08-19 2026-09-15
  } 2>&1 | tee -a /tmp/camp_es_t$t.log | grep -q "FALHA" || break
  echo "tentativa $t com FALHA; repetindo"
done
echo CAMPANHA-ES-FIM
