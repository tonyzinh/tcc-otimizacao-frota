from tcc_frota.availability.relationships import relationship_coverage


def test_key_overlap_is_reported_without_claiming_temporal_link(tmp_path):
    (tmp_path / "EVENTOS_STATUS_MOTORISTAS.csv").write_text("CD_JORNADA_MOTORISTA\na\nb\n", encoding="utf-8")
    (tmp_path / "JORNADAS_MOTORISTAS.csv").write_text("CD_JORNADA_MOTORISTA\na\nc\n", encoding="utf-8")
    results = relationship_coverage(tmp_path)
    match = results[0]
    assert (match["left_distinct"], match["overlap_distinct"], match["left_only_distinct"]) == (2, 1, 1)
    assert "não verificadas" in match["interpretation"]
    assert all(result["status"] == "FONTE_AUSENTE" for result in results[1:])
