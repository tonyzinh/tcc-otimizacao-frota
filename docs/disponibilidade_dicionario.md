# Dicionário de entrada da disponibilidade

Os nomes abaixo são contratos mínimos de leitura. Presença de coluna não confirma semântica operacional. A cobertura observada e exclusões ficam no relatório local ignorado `reports/runs/availability_diagnostic.jsonl`.

| Dataset | Chave ou vínculo inicial | Tempos relevantes | Uso nesta versão |
|---|---|---|---|
| `corridas_v1` | `CD_SOLICITACAO`, `CD_VEICULO` | `DT_INICIO_REALIZADA`, `DT_FIM_REALIZADA` | Ocupação por corrida encerrada; `DT_REGISTRO` não é criação assumida |
| `eventos_status_motoristas` | `CD_LOG_STATUS_MOTORISTA`, `CD_JORNADA_MOTORISTA`, `CD_VEICULO` | `inicio_evento`, `fim_evento` | Online candidato e indisponibilidade, somente intervalo e relação qualificados |
| `jornadas_motoristas` | `CD_JORNADA_MOTORISTA` | Estimados e realizados | Diagnóstico; vínculo temporal ainda pendente |
| `jornadas_corridas` | `CD_JORNADA_MOTORISTA`, `CD_SOLICITACAO` | Realizados | Cobertura de chave, sem multiplicar corridas |
| `reposicionamentos` | `CD_REPOSICIONAMENTO_MOTORISTA`, `CD_MOTORISTA` | `DT_REGISTRO`, `DT_ACEITE`, `DT_RECUSA`, `DT_FIM` | Diagnóstico; ocupação pendente de semântica e vínculo |
| `cobli_eventos` | `VEHICLE_ID`, `placa` | `START_ADDRESS_DATETIME`, `END_ADDRESS_DATETIME` | Diagnóstico de cobertura; `DRIVER_ID` não une diretamente ao motorista V1 |
| `veiculos` | `CD_VEICULO`, `placa` | `DT_REGISTRO`, `DT_DESATIVACAO` | Diagnóstico; cadastro atual não define elegibilidade histórica |
| `historico_veiculos` | `CD_HISTORICO_VEICULO`, `placa` | `DT_REGISTRO`, `DT_PREVISAO_TERMINO` | Diagnóstico; duração de mudança de estado pendente |
| `agendamentos` | `ID_AGENDAMENTO`, `CD_SOLICITACAO` | `DT_REGISTRO`, `DT_AGENDAMENTO`, `DT_DISTRIBUICAO` | Diagnóstico; uso em D+1 exige prova de conhecimento no corte |

As comparações de chaves feitas pelo comando `relationships` são somente interseções de identificadores. Cobertura de chave não demonstra correspondência temporal, exclusividade da placa ou aptidão do veículo.
