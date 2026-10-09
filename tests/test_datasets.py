import pytest

from evren_mcp.datasets import default_project_id, list_datasets, search_universe
from evren_mcp.errors import EvrenError
from tests.fakes import envelope

DS = "00000000-0000-4000-8000-000000000008"
VER = "00000000-0000-4000-8000-000000000002"


def test_list_datasets_with_versions(fake, platform):
    fake.on(
        "GET",
        "/datasets",
        (
            200,
            {
                "items": [
                    {
                        "id": DS,
                        "name": "visdrone-250",
                        "visibility": "private",
                        "item_count": 249,
                        "annotation_count": 15141,
                    }
                ]
            },
        ),
    )
    fake.on(
        "GET",
        f"/datasets/{DS}/versions",
        (
            200,
            envelope(
                [
                    {
                        "id": VER,
                        "version_tag": "v1",
                        "is_frozen": True,
                        "item_count": 249,
                        "split_config": {"train": 172},
                    }
                ]
            ),
        ),
    )
    out = list_datasets(platform)
    assert out[0]["ad"] == "visdrone-250"
    assert out[0]["surumler"][0] == {
        "id": VER,
        "etiket": "v1",
        "donmus": True,
        "oge": 249,
        "bolme": {"train": 172},
    }


def test_search_universe_accepts_results_key(fake, platform):
    fake.on(
        "GET",
        "/universe/search",
        (
            200,
            envelope(
                {"results": [{"name": "Drone", "slug": "drone", "owner_username": "u1", "stars_count": 1}]}
            ),
        ),
    )
    out = search_universe(platform, "drone", "model")
    assert out[0]["ad"] == "Drone" and out[0]["sahip"] == "u1"
    assert fake.calls("GET", "/universe/search")[0].url.params["type"] == "model"


def test_search_universe_rejects_unknown_kind(platform):
    with pytest.raises(EvrenError):
        search_universe(platform, "x", "kullanici")


def test_default_project_from_settings_or_first(fake, platform, fast_settings):
    fake.on("GET", "/projects", (200, envelope([{"id": "00000000-0000-4000-8000-000000000003"}])))
    assert default_project_id(platform, fast_settings) == "00000000-0000-4000-8000-000000000003"


def test_no_project_is_explained(fake, platform, fast_settings):
    fake.on("GET", "/projects", (200, envelope([])))
    with pytest.raises(EvrenError, match="proje"):
        default_project_id(platform, fast_settings)
