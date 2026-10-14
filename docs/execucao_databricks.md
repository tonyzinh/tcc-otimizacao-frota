# Execução com Parquet autorizado no Databricks

**Estado:** os notebooks `00_perfil_parquet.py` e `01_auditoria.py` leem e auditam o Parquet em um Unity Catalog Volume. Ainda não há pipeline real Bronze/Silver/Gold, previsão, alocação ou simulação. Os antigos notebooks sintéticos foram retirados da sequência Databricks. Nenhum notebook desta versão foi executado em um workspace.

1. Clone o repositório como Git folder no workspace. Abra os notebooks em compute Python Serverless. Informe `project_root` com o caminho absoluto do Git folder, por exemplo `/Workspace/Users/<usuario>/tcc-otimizacao-frota`.
2. O arquivo local `data/app_solicitacao_hist.parquet` está ignorado pelo Git. Como há autorização informada para este uso, coloque-o em um Unity Catalog Volume pelo procedimento aprovado na sua instituição. O projeto não faz upload automático. O caminho local do Windows **não** funciona dentro do Databricks.
3. Informe `parquet_path` como `/Volumes/<catalog>/<schema>/<volume>/app_solicitacao_hist.parquet`. Confirme `real_data_authorized=true` somente no workspace autorizado.
4. Execute `00_perfil_parquet.py` para conferir o esquema; `count_rows=false` evita a contagem inicial. Depois execute `01_auditoria.py` para obter apenas contagens agregadas de IDs, campos preenchidos e classes de status. Nenhum dos dois mostra linhas, placas ou identificadores.

A auditoria local do arquivo fornecido identificou 837.648 linhas, 128 colunas e 837.648 IDs de solicitação distintos. Há 404.623 linhas com status `CorridaEncerrada`. Essas contagens descrevem **este export**, não comprovam a deduplicação do histórico de origem (RN003). `DT_REGISTRO` é timestamp sem fuso no esquema e sua semântica de criação permanece pendente (RN023/RN024). O extrato sozinho não estabelece disponibilidade temporal, localização inicial nem compromissos da frota (RN015/RN016/RN026).

**Próximo gate:** confirmar origem e significado do timestamp do pedido, fuso, regras de extração, modalidades e fonte de disponibilidade. Até lá, não construir demanda D+1 por hora, replay real nem KPI corporativo de KM morto com esse Parquet. Pickup registrado, distância estimada e reposicionamento devem permanecer separados (RN007/RN008/RN031).

Referências da plataforma: [leitura de Parquet](https://docs.databricks.com/aws/en/query/formats/parquet), [arquivos em Volumes](https://docs.databricks.com/aws/en/volumes) e [limites da Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations).
