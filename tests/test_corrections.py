"""Tests for the minutes gate, DefCon layer, Understat parsing/merging, and
the captaincy algorithm."""

import pytest

from fpl_picker import understat
from fpl_picker.openfpl import expected_defcon, xmins_factor
from fpl_picker.scoring import Player
from fpl_picker.strategy import pick_captain


# --- minutes gate ---

def test_xmins_nailed_starter():
    rows = [{"minutes": 90}] * 5
    assert xmins_factor(rows) == 1.0


def test_xmins_rotation_and_benchwarmer():
    rows = [{"minutes": 90}, {"minutes": 0}, {"minutes": 90}, {"minutes": 0}, {"minutes": 20}]
    factor = xmins_factor(rows)
    assert 0.3 < factor < 0.6
    assert xmins_factor([{"minutes": 0}] * 5) == 0.05  # floored, not erased


def test_xmins_no_history_neutral():
    assert xmins_factor([]) == 1.0


# --- DefCon layer ---

def test_defcon_from_api_field():
    rows = [{"minutes": 90, "defensive_contribution": 2}] * 3 + [
        {"minutes": 90, "defensive_contribution": 0}
    ]
    assert expected_defcon(rows, "DEF") == pytest.approx(1.5)


def test_defcon_single_match_is_shrunk():
    # A perfect DefCon record over ONE match must not project full credit.
    one = [{"minutes": 90, "defensive_contribution": 2}]
    assert expected_defcon(one, "DEF") == pytest.approx(2.0 / 3.0)


def test_defcon_reconstructed_from_raw_stats():
    # DEF threshold 10 CBIT: hits in 2 of 4 started matches -> 1.0 exp pts.
    rows = [
        {"minutes": 90, "clearances_blocks_interceptions": 12},
        {"minutes": 90, "clearances_blocks_interceptions": 11},
        {"minutes": 90, "clearances_blocks_interceptions": 4},
        {"minutes": 90, "clearances_blocks_interceptions": 6},
        {"minutes": 30, "clearances_blocks_interceptions": 12},  # not started
    ]
    assert expected_defcon(rows, "DEF") == pytest.approx(1.0)
    # MID threshold 12 includes tackles + recoveries; single match -> shrunk.
    mid_rows = [
        {"minutes": 90, "clearances_blocks_interceptions": 4, "tackles": 4,
         "recoveries": 5},
    ]
    assert expected_defcon(mid_rows, "MID") == pytest.approx(2.0 / 3.0)


def test_defcon_absent_data_is_zero():
    assert expected_defcon([{"minutes": 90}], "DEF") == 0.0
    assert expected_defcon([{"minutes": 90, "defensive_contribution": 2}], "GK") == 0.0


# --- Understat ---

def test_decode_blob_roundtrip():
    payload = {"a": [1, 2], "name": "Bruno Fernandes"}
    import json

    encoded = "".join(f"\\x{ord(c):02x}" if ord(c) < 128 else c for c in json.dumps(payload))
    page = f"<script>var testData = JSON.parse('{encoded}');</script>"
    assert understat.decode_blob(page, "testData") == payload


def test_team_and_player_matching():
    fpl_teams = [
        {"id": 1, "name": "Manchester City", "short_name": "MCI"},
        {"id": 2, "name": "Arsenal", "short_name": "ARS"},
    ]
    assert understat.match_team("Manchester City", fpl_teams) == 1
    assert understat.match_team("Arsenal", fpl_teams) == 2

    elements = [
        {"id": 5, "team": 2, "first_name": "Gabriel", "second_name": "Magalhães",
         "web_name": "Gabriel"},
        {"id": 6, "team": 2, "first_name": "Bukayo", "second_name": "Saka",
         "web_name": "Saka"},
    ]
    us_player = {"name": "Bukayo Saka", "team": "Arsenal"}
    assert understat.match_player(us_player, elements, 2) == 6


def test_merge_into_snapshot():
    data = {
        "bootstrap": {
            "teams": [{"id": 2, "name": "Arsenal", "short_name": "ARS"}],
            "elements": [
                {"id": 6, "team": 2, "first_name": "Bukayo",
                 "second_name": "Saka", "web_name": "Saka"},
            ],
        },
        "history": {"6": [{"kickoff_time": "2026-08-22T14:00:00Z", "minutes": 90}]},
    }
    us = {
        "teams": {"Arsenal": [{"date": "2026-08-22", "us_xg": 2.1}]},
        "players": {
            "99": {"name": "Bukayo Saka", "team": "Arsenal",
                   "matches": [{"date": "2026-08-22", "us_shots": 4,
                                "us_key_passes": 3, "us_xgchain": 0.9,
                                "us_xgbuildup": 0.4}]},
        },
    }
    matched, total = understat.merge_into_snapshot(data, us)
    assert (matched, total) == (1, 1)
    assert data["history"]["6"][0]["us_shots"] == 4
    assert data["understat_teams"]["2"][0]["us_xg"] == 2.1


# --- captaincy ---

def make_player(pid, name, score, price, owned, team_id=1):
    return Player(
        id=pid, name=name, team_id=team_id, team="T", position="MID",
        price=price, score=score, per_gw=score / 5, status="a",
        stats={"selected_by": str(owned)},
    )


@pytest.fixture
def xi_data():
    bootstrap = {
        "events": [{"id": 1, "is_next": True}],
        "teams": [{"id": i} for i in range(1, 21)],
        "elements": [],
    }
    fixtures = [{"event": 1, "team_h": 1, "team_a": 2}]
    return {"bootstrap": bootstrap, "fixtures": fixtures}


def test_neutral_keeps_high_eo_default(xi_data):
    default = make_player(1, "Haaland", 21.0, 15.5, 75.0)
    rival = make_player(2, "MidPunt", 21.5, 7.0, 8.0, team_id=3)  # no fixture boost (no fixture)
    advice = pick_captain([default, rival], xi_data, mode="neutral")
    assert advice.captain.id == 1  # small gap + no fixture trigger -> default


def test_neutral_deviates_when_projection_gap_is_big(xi_data):
    default = make_player(1, "Haaland", 15.0, 15.5, 75.0)
    better = make_player(2, "Bruno", 19.0, 12.0, 40.0)
    advice = pick_captain([default, better], xi_data, mode="neutral")
    assert advice.captain.id == 2


def test_protect_shadows_the_field(xi_data):
    default = make_player(1, "Haaland", 20.0, 15.5, 75.0)
    slightly_better = make_player(2, "Bruno", 21.0, 12.0, 40.0)
    advice = pick_captain([default, slightly_better], xi_data, mode="protect")
    assert advice.captain.id == 1


def test_chase_takes_the_differential(xi_data):
    default = make_player(1, "Haaland", 21.0, 15.5, 75.0)
    diff = make_player(2, "Punt", 20.0, 7.5, 10.0)
    advice = pick_captain([default, diff], xi_data, mode="chase")
    assert advice.captain.id == 2
