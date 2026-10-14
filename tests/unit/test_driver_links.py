import pytest

from tcc_frota.quality.driver_links import validate_driver_links


def test_no_automatic_driver_id_join_rn016():
    audit = validate_driver_links({"1", "2"}, {"1", "3"})
    assert not audit.validated and audit.matched == 0
    assert audit.unmatched_journey == 2 and audit.unmatched_status == 2


def test_only_verified_one_to_one_mapping_is_accepted():
    audit = validate_driver_links({"1", "2"}, {"x", "y"}, {"1": "x"})
    assert audit.validated and audit.matched == 1
    with pytest.raises(ValueError):
        validate_driver_links({"1", "2"}, {"x"}, {"1": "x", "2": "x"})
