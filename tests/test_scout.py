import pytest

from fpl_picker import scoring
from fpl_picker.scout import fixture_runs, strike_candidates


def test_fixture_runs_ranks_and_lists_opponents(snapshot):
    runs = fixture_runs(snapshot, horizon=3)
    assert len(runs) == len(snapshot["bootstrap"]["teams"])
    eases = [r["ease"] for r in runs]
    assert eases == sorted(eases, reverse=True)  # easiest first
    assert all(r["fixtures"] for r in runs)  # every team has fixtures listed
    assert "(" in runs[0]["fixtures"][0]  # opponent(venue) format


def test_fixture_runs_handles_blanks_and_doubles():
    data = {
        "bootstrap": {
            "events": [{"id": 1, "is_next": True}],
            "teams": [
                {"id": 1, "short_name": "AAA"},
                {"id": 2, "short_name": "BBB"},
                {"id": 3, "short_name": "CCC"},
            ],
            "elements": [],
        },
        "fixtures": [
            # Team 1 plays twice in GW1 (double), team 3 not at all (blank).
            {"event": 1, "team_h": 1, "team_a": 2,
             "team_h_difficulty": 2, "team_a_difficulty": 4},
            {"event": 1, "team_h": 1, "team_a": 2,
             "team_h_difficulty": 2, "team_a_difficulty": 4},
        ],
    }
    runs = {r["team"]: r for r in fixture_runs(data, horizon=1)}
    assert runs["AAA"]["ease"] > runs["BBB"]["ease"]  # easier fixtures
    assert len(runs["AAA"]["fixtures"]) == 2  # double counted
    assert runs["CCC"]["ease"] == 0.0  # blank


def test_strike_candidates_rank_by_volume_and_filters(snapshot):
    import copy

    data = copy.deepcopy(snapshot)
    for e in data["bootstrap"]["elements"]:
        e["minutes"] = 450
        e["expected_goal_involvements_per_90"] = "0.10"
        e["expected_goal_involvements"] = "0.5"
        e["goals_scored"], e["assists"] = 0, 0
        e["selected_by_percent"] = "5.0"
    star = data["bootstrap"]["elements"][0]
    star["expected_goal_involvements_per_90"] = "0.95"
    hidden = data["bootstrap"]["elements"][1]
    hidden["expected_goal_involvements_per_90"] = "0.90"
    hidden["selected_by_percent"] = "60.0"

    players = scoring.score_players(data, horizon=5)
    rows = strike_candidates(data, players, horizon=5, max_ownership=20.0)
    assert rows[0]["player"].id == star["id"]
    assert hidden["id"] not in {r["player"].id for r in rows}  # ownership filter


def test_strike_candidates_skip_low_minutes(snapshot):
    import copy

    data = copy.deepcopy(snapshot)
    for e in data["bootstrap"]["elements"]:
        e["minutes"] = 10
        e["expected_goal_involvements_per_90"] = "1.50"
    players = scoring.score_players(data, horizon=5)
    assert strike_candidates(data, players, horizon=5) == []
