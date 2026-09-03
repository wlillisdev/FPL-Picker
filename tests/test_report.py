import json

from fpl_picker import report


def test_accuracy_scoring(tmp_path):
    pred_file = tmp_path / "gw1.json"
    json.dump(
        {
            "gameweek": 1,
            "horizon": 5,
            "players": [
                {"id": 1, "name": "Good", "position": "MID", "price": 8.0, "per_gw": 6.0},
                {"id": 2, "name": "Bad", "position": "FWD", "price": 6.0, "per_gw": 5.0},
                {"id": 3, "name": "Ghost", "position": "DEF", "price": 4.0, "per_gw": 2.0},
            ],
        },
        open(pred_file, "w"),
    )
    data = {
        "history": {
            "1": [{"round": 1, "total_points": 7, "minutes": 90}],
            "2": [{"round": 1, "total_points": 1, "minutes": 90}],
            # player 3 has no history -> actual 0
        }
    }
    actuals = report.actual_points_by_gw(data)
    result = report.score_gameweek(str(pred_file), actuals)
    assert result["gw"] == 1
    assert result["n"] == 3
    # errors: |6-7|=1, |5-1|=4, |2-0|=2 -> MAE 7/3
    assert abs(result["mae"] - 7 / 3) < 1e-9
    assert result["baseline_mae"] > 0
    assert result["top10"][0][0] == "Good"


def test_unplayed_gameweek_returns_none(tmp_path):
    pred_file = tmp_path / "gw9.json"
    json.dump(
        {"gameweek": 9, "horizon": 5,
         "players": [{"id": 1, "name": "X", "position": "MID", "price": 5.0, "per_gw": 3.0}]},
        open(pred_file, "w"),
    )
    assert report.score_gameweek(str(pred_file), {}) is None
