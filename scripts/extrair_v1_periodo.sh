#!/usr/bin/env bash
# Extração retomável por entidade e por dia (idempotente: lote pronto é pulado). Uso:
#   TCC_REAL_DATA_AUTHORIZED=YES scripts/extrair_v1_periodo.sh 2026-03-10 2026-03-10 [entidades ods...] 
# Exige o segredo protegido (python -m tcc_frota.data.privacy status). Não gera segredo.
set -u
INI="$1"; FIM="$2"; shift 2
PY=".venv/Scripts/python.exe"
ODS=(${ODS_ENT:-solicitacao status_solicitacao veiculo compromissos_externos telemetria_cobli jornada_motorista log_status_motorista reposicionamento})
ES=(${ES_ENT:-posicao_ofertas sumario_ofertas reposicionamento_sugerido})
export PYTHONPATH=src PYTHONUNBUFFERED=1
for e in "${ODS[@]}"; do echo "== ods/$e $INI..$FIM"; $PY -m tcc_frota.data.extraction --fonte ods --entidade "$e" --inicio "$INI" --fim "$FIM" --bloco-dias "${BLOCO_DIAS:-7}" || echo "FALHA ods/$e"; done
for e in "${ES[@]}"; do echo "== es/$e $INI..$FIM"; $PY -m tcc_frota.data.extraction --fonte es --entidade "$e" --inicio "$INI" --fim "$FIM" || echo "FALHA es/$e"; done
echo FIM
