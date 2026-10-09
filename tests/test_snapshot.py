import json

import pytest

from fpl_picker import api


def test_build_snapshot_from_browser_files(tmp_path, snapshot):
    bootstrap_file = tmp_path / "bootstrap.json"
    fixtures_file = tmp_path / "fixtures.json"
    bootstrap_file.write_text(json.dumps(snapshot["bootstrap"]))
    fixtures_file.write_text(json.dumps(snapshot["fixtures"]))

    data = api.build_snapshot(str(bootstrap_file), str(fixtures_file))
    assert data["bootstrap"]["elements"] == snapshot["bootstrap"]["elements"]
    assert data["fixtures"] == snapshot["fixtures"]
    assert "history" not in data


def test_build_snapshot_rejects_wrong_files(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"not": "bootstrap"}))
    fixtures = tmp_path / "fx.json"
    fixtures.write_text(json.dumps([]))

    with pytest.raises(ValueError, match="bootstrap-static"):
        api.build_snapshot(str(bad), str(fixtures))

    good = tmp_path / "bs.json"
    good.write_text(json.dumps({"elements": [], "teams": [], "events": []}))
    not_a_list = tmp_path / "nl.json"
    not_a_list.write_text(json.dumps({"oops": True}))
    with pytest.raises(ValueError, match="fixtures"):
        api.build_snapshot(str(good), str(not_a_list))
