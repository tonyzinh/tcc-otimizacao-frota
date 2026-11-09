import pytest

from tcc_frota.data.initial_position import Matriz, MatrizNaoDefinida, Observacao, construir_sessoes, posicao_inicial


def _o(t, lat=-20.3, lon=-40.3):
    return Observacao(t, lat, lon, "teste")


def test_usa_observacao_anterior_dentro_da_idade_maxima_e_registra_idade():
    p = posicao_inicial((1000.0, 5000.0), [_o(900.0)], max_idade_s=300.0)
    assert p.estado == "conhecida_no_inicio" and p.idade_s == 100.0 and p.desconhecido_s == 0.0


def test_observacao_velha_demais_nao_localiza_o_inicio():
    p = posicao_inicial((1000.0, 5000.0), [_o(100.0), _o(1400.0)], max_idade_s=300.0)
    assert p.estado == "conhecida_apos_inicio" and p.inicio_efetivo_s == 1400.0 and p.desconhecido_s == 400.0


def test_nunca_usa_posicao_futura_para_localizar_instante_anterior():
    p = posicao_inicial((1000.0, 5000.0), [_o(1200.0, -20.5, -40.5)], max_idade_s=3600.0)
    assert p.estado == "conhecida_apos_inicio" and p.inicio_efetivo_s == 1200.0
    assert p.desconhecido_s == 200.0  # [1000, 1200) desconhecido, não preenchido com a posição de 1200


def test_nao_extrapola_posicao_atraves_de_viagem_ou_compromisso():
    p = posicao_inicial((1000.0, 5000.0), [_o(900.0), _o(2000.0)], max_idade_s=3600.0, moveis=((950.0, 990.0),))
    assert p.estado == "conhecida_apos_inicio" and p.inicio_efetivo_s == 2000.0


def test_sem_nenhuma_observacao_a_jornada_fica_desconhecida():
    p = posicao_inicial((1000.0, 5000.0), [], max_idade_s=300.0)
    assert p.estado == "desconhecida" and p.desconhecido_s == 4000.0


def test_matriz_sem_coordenadas_levanta_e_com_coordenadas_e_hipotese():
    with pytest.raises(MatrizNaoDefinida):
        posicao_inicial((0.0, 10.0), [], max_idade_s=1.0, condicao="matriz_configurada")
    p = posicao_inicial(
        (0.0, 10.0), [], max_idade_s=1.0, condicao="matriz_configurada", matriz=Matriz(-20.0, -40.0, "hipotese do proprietario")
    )
    assert p.estado == "hipotese_matriz" and (p.lat, p.lon) == (-20.0, -40.0)


def test_cobertura_perdida_e_quantificada_e_posicao_do_dia_alvo_nao_e_da_vespera():
    sess, rel = construir_sessoes(
        {"A": [(1000.0, 5000.0)], "B": [(0.0, 1000.0)]},
        {"A": [_o(1500.0)], "B": []},
        max_idade_s=300.0,
    )
    assert "A" in sess and "B" not in sess
    assert rel["segundos_desconhecidos"] == 500.0 + 1000.0 and rel["conhecida_pelo_planejador_vespera"] is False
    assert rel["por_estado"] == {"conhecida_apos_inicio": 1, "desconhecida": 1}
