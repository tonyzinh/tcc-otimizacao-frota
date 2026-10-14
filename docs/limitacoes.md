# Limitações e ameaças à validade

1. **Constructo de KM morto:** a definição corporativa e as parcelas do KPI seguem pendentes (DT003/RN010). Haversine é linha reta, não odômetro ou rota viária.
2. **Dados:** só houve execução sintética. Os CSVs reais locais não foram auditados além de cabeçalhos; criação do pedido, fuso, cobertura, dedup, GPS histórico e jornada permanecem sem confirmação.
3. **Baseline:** despacho mais próximo sem reposicionamento é uma simplificação, não política observada da empresa.
4. **Disponibilidade:** intervalos sintéticos e compromissos são conhecidos por construção; vínculos motorista–jornada, pausas e posição real não foram reconstruídos.
5. **Contrafactual:** demanda, comportamento humano, tráfego e adesão real não respondem à intervenção. O replay não demonstra economia financeira nem implantação.
6. **Previsão:** média por zona/hora/dia da semana é explicável, mas pode errar em eventos, feriados e sazonalidade; não usa eventos externos.
7. **Segmentação:** três zonas fixas simplificam o exemplo. A grade temporalmente correta existe no núcleo, mas escolha de malha real depende de dispersão, cobertura e privacidade.
8. **Databricks:** notebook/Delta/Unity Catalog não executados em Free Edition nesta entrega; permissões e limites efetivos devem ser verificados no workspace.
9. **Sensibilidade:** há variação sintética de frota, demanda, distribuição inicial, cobertura, limite de movimento e adesão. Velocidade/tráfego, custo marginal, granularidade espacial e disponibilidade real ainda pedem estudo separado.

Essas limitações restringem toda conclusão a comportamento do modelo no cenário descrito. Um resultado nulo ou adverso deve ser mantido.
