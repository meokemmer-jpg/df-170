import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
# [CRUX-MK]
import importlib

m170 = importlib.import_module("170")
parse_factory_id = m170.parse_factory_id
is_target_mission = m170.is_target_mission
mission_signature = m170.mission_signature


def test_parse_factory_id_and_signature():
    mission = parse_factory_id("df-170")
    assert mission.factory_prefix == "df"
    assert mission.mission_number == 170
    assert mission.canonical_id == "df-170"
    assert is_target_mission("df-170") is True
    assert mission_signature("df-170") == "df-170|core-online"


def test_invalid_factory_ids():
    import pytest

    with pytest.raises(ValueError):
        parse_factory_id("xx-170")

    with pytest.raises(ValueError):
        parse_factory_id("df-17x")

    with pytest.raises(ValueError):
        parse_factory_id("df170")
