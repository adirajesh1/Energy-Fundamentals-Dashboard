from gas_forecast.data.regions import (
    region_label,
    region_slug,
    supported_storage_regions,
)


def test_canonical_regions_and_labels_match_eia_storage_geography():
    assert supported_storage_regions() == ["R48", "R31", "R32", "R33", "R34", "R35"]
    assert region_label("R33") == "South Central"
    assert region_label("R34") == "Mountain"
    assert region_label("R35") == "Pacific"
    assert region_slug("R33") == "south_central"


def test_legacy_aliases_are_opt_in():
    assert "R01" not in supported_storage_regions()
    assert "R01" in supported_storage_regions(include_legacy=True)
