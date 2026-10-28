from datetime import UTC, date, datetime

import pytest

from tcc_frota.demand.forecast import forecast_hour
from tcc_frota.models import Position, Request
from tcc_frota.spatial.grid import fit_grid

UTC = UTC
A = Position("a", -20.30, -40.30)
B = Position("b", -20.31, -40.29)


def test_future_requests_cannot_change_d1_forecast_or_grid():
    past = [Request("past", datetime(2026, 1, 1, 8, tzinfo=UTC), A, B, 10)]
    future = [Request("future", datetime(2026, 1, 2, 8, tzinfo=UTC), B, A, 10)]
    cutoff = datetime(2026, 1, 1, 20, tzinfo=UTC)
    base = forecast_hour(past, ("a", "b"), date(2026, 1, 2), 8, cutoff)
    with_future = forecast_hour(past + future, ("a", "b"), date(2026, 1, 2), 8, cutoff)
    assert base == with_future
    assert fit_grid(past, cutoff, min_samples=1) == fit_grid(past + future, cutoff, min_samples=1)


def test_forecast_zero_and_invalid_cutoff():
    cutoff = datetime(2026, 1, 1, 20, tzinfo=UTC)
    result = forecast_hour([], ("a",), date(2026, 1, 2), 8, cutoff)
    assert result.expected_by_zone == {"a": 0.0}
    with pytest.raises(ValueError):
        forecast_hour([], ("a",), date(2026, 1, 1), 8, cutoff)
    with pytest.raises(ValueError):
        forecast_hour([], ("a",), date(2026, 1, 2), 8, datetime(2026, 1, 1, 20))
