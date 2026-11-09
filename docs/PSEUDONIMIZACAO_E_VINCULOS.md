# Pseudonimização estável e vínculos entre fontes (08/11/2026)

Estado: **implementado e testado**; piloto de 10/03/2026 regravado com o esquema novo (ver §5). Decisões formais: R-07 e R-08 em `REGISTRO_DECISOES.md`.

## 1. Por que `data/.pseudo_salt` e `data/raw/` sumiram (investigação de 08/11/2026)

| Evidência | Resultado |
|---|---|
| Scripts, testes e configuração do repositório (`rmtree`, `unlink`, `Remove-Item`, `git clean`, `rm -rf`) | Só `saida.py` apaga o `rejeitados.parquet` do próprio lote. Nenhum script remove `data/` ou o sal. `pytest` usa `--basetemp=.pytest-tmp`, fora de `data/` |
| `.claude/settings.json` | `bypassPermissions`; sem hooks de limpeza |
| Lixeira do Windows | **Contém os dois itens**: `raw` e `.pseudo_salt` (origem `data/`), apagados em 06/11/2026 às 21:37 UTC (18:37 local), um minuto antes do sal atual ser criado (mtime 18:38 local). `raw` tem 82 arquivos, 348 MB (`dados_historico56`, `dados_historico56_set`, `dados_mar2026`, `dados_set2026`). Na mesma data foram para a lixeira `docs`, `reports`, `resultados`, `tabelas`, `.codex`, `.ref`, `.pytest*`, `.ruff_cache` (~20:52–20:55 UTC) e a pasta-mãe `tcc-otimizacao-frota` (20:36 UTC) |
| Pasta sincronizada | O repositório está em `OneDrive\Documentos`; `data/` e o sal ficam sincronizados com a nuvem. Não há evidência de que o OneDrive tenha apagado algo |

**Conclusão (nível: executado, causa não provada).** Os itens foram *movidos para a lixeira* (não apagados em definitivo) por uma operação de usuário/shell durante a limpeza de 06/11, não por código do projeto. A lixeira não registra o processo responsável; **a causa exata não é determinável com a evidência disponível**. Consequência: o sal original e `data/raw` **são recuperáveis** (não restaurei nenhum dos dois; ver §6).

## 2. Esquema `hmac-sha256-v1`

- Segredo fora do repositório e fora de pasta sincronizada: `%LOCALAPPDATA%\tcc_frota\segredos\pseudo_secret` (`TCC_SEGREDOS_DIR` substitui), permissão restrita ao usuário (`icacls`, herança removida).
- Cópia de segurança separada: `%USERPROFILE%\.tcc_frota_backup\pseudo_secret.<chave_id>.bak` (conferida pela impressão digital). **Guarde também uma cópia off-line (gerenciador de senhas).**
- `chave_id` = HMAC-SHA256(segredo, rótulo fixo)[:12]: identifica a versão sem expor o segredo. Vai em todo manifesto (`pseudonimizacao.chave_id`), no registro `data/extraido/v1_viagens/PSEUDONIMIZACAO.json` e na assinatura do lote.
- Pseudônimo = HMAC-SHA256(segredo, `entidade␟valor normalizado`)[:20 hex]. Entidades: `motorista`, `condutor`, `placa`, `veiculo_cod`, `passageiro`, `veiculo_condutor` e `cobli_*`. Normalização: espaços, `5.0`→`5`, placa em maiúsculas só com alfanuméricos.
- Guarda: segredo ausente ou diferente do registrado interrompe a extração (`SegredoAusente`/`SegredoIncompativel`); lotes sem versão (legado) bloqueiam a campanha; **nenhum segredo é criado automaticamente**, e `inicializar` recusa quando já existem lotes dependentes. Migração do sal legado preserva o valor (`inicializar --do-legado`).
- Comandos: `python -m tcc_frota.privacidade status|inicializar|backup|restaurar <chave_id>` (nunca imprime o segredo).

### Por que a normalização importava (evidência)
Na Cobli, 67 de 3.000 placas amostradas (2,2%) vêm com espaço à direita. Com o esquema antigo (SHA-256 do texto bruto) a mesma placa geraria dois pseudônimos.

## 3. Famílias de identificadores (evidência de 10/03/2026, contagens de interseção)

| Par | Interseção | Leitura |
|---|---|---|
| motorista (solicitação) × motorista (ES ofertas) × usuário (ES reposicionamento) × motorista (log de status) | 111, 111, 111 de 129 motoristas com corrida | **mesma família**: junção válida |
| motorista (solicitação) × `CD_MOTORISTA` da jornada | **0** de 129 | famílias distintas |
| `CD_MOTORISTA` da jornada × `CD_CONDUTOR` (`APP_VEICULO_CONDUTOR`) | 167 de 168 | a jornada usa o **condutor** |
| `CD_VEICULO` do ODS × placa | 0 | `CD_VEICULO` é código numérico, **não** é placa |
| placa do cadastro (`TX_PLACA`) × placa Cobli | 117 de 117 | ponte ODS↔Cobli possível via `APP_VEICULO.TX_PLACA` |
| placa ES ofertas × placa Cobli | 101 de 117 | consistente (ofertas listam só veículos ofertados) |
| `CD_INTEGRACAO_VEHICLE_ID`/`TX_INTEGRACAO_DEVICE_ID` × ids Cobli | 0 | não servem de ponte |
| Motorista Cobli (`DRIVER_ID`, UUID) × motorista ODS | 0 (família própria; 22% das viagens sem motorista) | não há ponte |

Pendência: o cadastro tem **1.928 placas repetidas** em mais de um `CD_VEICULO` (reuso/histórico); `CD_VEICULO → placa` é função, `placa → CD_VEICULO` não. A placa vem de uma foto atual: pode divergir da placa vigente em março.

## 4. Teste de integração dos vínculos
`tests/integration/test_pseudonimizacao.py`: dois processos separados geram os mesmos pseudônimos; ODS e ES ligam o mesmo motorista; ES e Cobli ligam a mesma placa (inclusive com espaço/caixa distintos); guarda contra segredo ausente/trocado/legado; migração, backup e restauração. `tests/integration/test_extracao_retomavel.py`: segunda execução pula o lote, segredo trocado interrompe antes de gravar, lote corrompido é regravado.

## 5. Arquivos antes e depois da troca
- **Antes (sal anterior):** `data/raw/` (lixeira) e qualquer silver derivado dele. Nenhum artefato congelado (`resultados/`, `reports/tcc_final`) contém pseudônimos (verificado por busca de colunas de identificador): a perda do sal não altera resultado congelado.
- **Depois da troca, mesmo sal (18:38 local):** todo o piloto antigo (sal criado 18:38; lotes de 18:38 a 18:52). Interseções altas entre fontes (§3) confirmam que usam **um único** sal. Foi movido, sem apagar, para `data/extraido/v1_viagens_legado_sal_20261106/` (pseudônimos de 16 hex, sem versão).
- **Decisão sobre o segredo:** o valor do sal de 06/11 foi **mantido** (migrado sem alteração para o local protegido; `chave_id 02f6c9316eb0`) porque era o único com dados dependentes vivos. Os dados foram regravados com a transformação nova em `data/extraido/v1_viagens/`.
- `data/.pseudo_salt` permanece **porque o pipeline v2 (`v2/rules.py::load_salt`) ainda o lê**; ele fica em pasta sincronizada. Recomenda-se removê-lo depois de migrar o v2 (ação sua).

## 6. Recuperação do material na lixeira (não executada)
`raw` (348 MB) e o sal original estão na lixeira. Restaurar `data/raw` é cópia local, sem enviar nada a serviço externo; não o fiz porque não foi pedido e o uso exige o portão. Se quiser o sal original apenas para consulta, copie-o para um nome distinto: restaurá-lo sobre `data/.pseudo_salt` sobrescreveria o arquivo atual.
