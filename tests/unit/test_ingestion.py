import pytest

from tcc_frota.distance import RouteDistance, estimated_meters, observed_meters
from tcc_frota.ingestion.files import authorize, read_rows
from tcc_frota.ingestion.history import parse_coordinate, reconstruct_history
from tcc_frota.models import Position
from tcc_frota.quality.audit import audit_rows


def test_csv_audit_missing_duplicate_and_empty(tmp_path):
    path = tmp_path / "synthetic.csv"
    path.write_text("id,created\na,2026-01-01\na,\nb,2026-01-02\n", encoding="utf-8")
    rows = list(read_rows(path))
    summary = audit_rows(rows, ("id", "created"), key="id")
    assert summary.rows == 3
    assert summary.duplicate_keys == 1
    assert summary.missing_required["created"] == 1
    assert summary.excluded["missing_required"] == 1
    assert audit_rows(rows, ("absent",)).missing_required["absent"] == 3
    empty = tmp_path / "empty.csv"
    empty.write_bytes(b"")
    with pytest.raises(ValueError, match="vazio"):
        list(read_rows(empty))


def test_excel_multiple_sheets(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")
    workbook = openpyxl.Workbook()
    workbook.active.title = "first"
    workbook.active.append(["id", "value"])
    workbook.active.append(["a", 1])
    other = workbook.create_sheet("second")
    other.append(["id", "value"])
    other.append(["b", 2])
    path = tmp_path / "synthetic.xlsx"
    workbook.save(path)
    assert [row["_sheet"] for row in read_rows(path)] == ["first", "second"]


def test_real_data_gate_requires_two_distinct_authorizations(monkeypatch):
    monkeypatch.delenv("TCC_REAL_DATA_AUTHORIZED", raising=False)
    monkeypatch.delenv("TCC_EXTERNAL_DATA_AUTHORIZED", raising=False)
    with pytest.raises(PermissionError):
        authorize("real")
    monkeypatch.setenv("TCC_REAL_DATA_AUTHORIZED", "YES")
    authorize("real", "local")
    with pytest.raises(PermissionError):
        authorize("real", "external")
    monkeypatch.setenv("TCC_EXTERNAL_DATA_AUTHORIZED", "YES")
    authorize("real", "external")


def test_known_real_extract_cannot_be_mislabeled_synthetic(tmp_path):
    path = tmp_path / "app_solicitacao_hist.csv"
    path.write_text("CD_SOLICITACAO\nsynthetic-x\n", encoding="utf-8")
    with pytest.raises(PermissionError, match="não pode ser declarado"):
        list(read_rows(path, dataset_kind="synthetic"))


def test_history_dedup_creation_and_source_distances():
    rows = [
        {
            "CD_SOLICITACAO": "1",
            "DT_REGISTRO": "2026-01-01T08:00:00+00:00",
            "TX_STATUS": "AguardandoCondutor",
            "DT_INICIO_REALIZADA": "2026-01-01T08:20:00+00:00",
        },
        {
            "CD_SOLICITACAO": "1",
            "DT_REGISTRO": "2026-01-01T09:00:00+00:00",
            "TX_STATUS": "CorridaEncerrada",
            "NU_DISTPERCORRIDA": "1200",
            "NU_DISTANCIA_ACEITE_CHEGUEI": "350",
            "TX_ORIGEM_LAT": "-20,3",
            "TX_ORIGEM_LNG": "-40,2",
        },
        {"CD_SOLICITACAO": "", "DT_REGISTRO": "2026-01-01T09:00:00+00:00"},
    ]
    items, audit = reconstruct_history(rows)
    assert audit.requests == 1 and audit.total_rows == 3
    assert audit.dedup_disagreements == 1
    assert audit.excluded["missing_request_id"] == 1
    assert items[0].created_at is None  # RN023: status final não prova criação
    assert items[0].final_status == "CorridaEncerrada"
    assert items[0].pickup_km_observed == 0.35
    assert items[0].trip_km_observed == 1.2
    assert items[0].origin_lat == -20.3


def test_history_verified_creation_field_and_timestamp_validation():
    row = {"CD_SOLICITACAO": "1", "DT_REGISTRO": "2026-01-01T09:00:00+00:00", "DT_CRIACAO_VERIFICADA": "2026-01-01T08:00:00+00:00"}
    items, _ = reconstruct_history([row], creation_field="DT_CRIACAO_VERIFICADA")
    assert items[0].created_at.hour == 8
    with pytest.raises(ValueError):
        reconstruct_history([row], creation_field="DT_REGISTRO")
    event_rows = [
        {"CD_SOLICITACAO": "1", "DT_REGISTRO": "2026-01-01T08:00:00+00:00", "TX_STATUS": "AguardandoCondutor"},
        {"CD_SOLICITACAO": "1", "DT_REGISTRO": "2026-01-01T09:00:00+00:00", "TX_STATUS": "CorridaEncerrada"},
    ]
    by_event, _ = reconstruct_history(event_rows, creation_status="AguardandoCondutor")
    assert by_event[0].created_at.hour == 8
    bad, audit = reconstruct_history([{**row, "DT_REGISTRO": "2026-01-01T09:00:00"}])
    assert bad == [] and audit.excluded["invalid_status_timestamp"] == 1
    with pytest.raises(ValueError):
        parse_coordinate("91", latitude=True)


def test_unit_and_provenance_separation():
    assert observed_meters("1250", "NU_DISTPERCORRIDA").km == 1.25
    assert observed_meters(None, "NU_DISTANCIA_ACEITE_CHEGUEI").km is None
    assert not estimated_meters(200, "NU_DP").observed
    assert not estimated_meters(200, "NU_DR_REAL").observed
    with pytest.raises(ValueError):
        observed_meters(200, "NU_DP")
    with pytest.raises(ValueError):
        observed_meters(-1, "NU_DISTPERCORRIDA")
    a = Position("a", -20, -40)
    b = Position("b", -20.1, -40)
    route = RouteDistance(lambda _a, _b: 12.5, "offline-test")
    assert route.measure(a, b).km == 12.5
    assert not route.measure(a, b).observed
    with pytest.raises(ValueError):
        RouteDistance(lambda _a, _b: -1, "bad").measure(a, b)
