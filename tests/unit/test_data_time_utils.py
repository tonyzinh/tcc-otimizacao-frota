from datetime import datetime

import pandas as pd
import pytest

from tcc_frota.data.time_utils import dia_local_para_janela_utc, para_local


def test_cobli_utc_vira_local_menos_3h():
    assert para_local(datetime(2026, 3, 10, 3, 30), "cobli") == pd.Timestamp("2026-03-10 00:30")


def test_es_com_offset_vira_local_sem_perder_o_instante():
    assert para_local("2026-03-10T00:30:00-03:00", "es") == pd.Timestamp("2026-03-10 00:30")
    assert para_local("2026-03-10T03:30:00+00:00", "es") == pd.Timestamp("2026-03-10 00:30")


def test_ods_e_mantido_e_fuso_inesperado_e_rejeitado():
    assert para_local(datetime(2026, 3, 10, 8), "ods") == pd.Timestamp("2026-03-10 08:00")
    with pytest.raises(ValueError):
        para_local("2026-03-10T08:00:00-03:00", "ods")
    with pytest.raises(ValueError):
        para_local(datetime(2026, 3, 10, 8), "es")


def test_ausente_continua_ausente():
    assert pd.isna(para_local(None, "cobli"))


def test_janela_utc_do_dia_local_comeca_as_03h():
    ini, fim = dia_local_para_janela_utc("2026-03-10")
    assert ini == datetime(2026, 3, 10, 3) and fim == datetime(2026, 3, 11, 3)


def test_conhecimento_sob_hipotese_soma_atraso_e_nao_inventa_quando_ausente():
    from tcc_frota.data.time_utils import conhecido_sob_hipotese

    assert conhecido_sob_hipotese(pd.Timestamp("2026-03-10 08:00:00"), 60) == pd.Timestamp("2026-03-10 08:01:00")
    assert pd.isna(conhecido_sob_hipotese(None, 60))


def test_idade_da_posicao_cresce_com_o_tempo():
    from tcc_frota.data.time_utils import idade_posicao_s

    assert idade_posicao_s("2026-03-10 08:00:00", "2026-03-10 08:05:00") == 300.0
    assert idade_posicao_s(None, "2026-03-10 08:05:00") != idade_posicao_s(None, "2026-03-10 08:05:00")  # NaN
