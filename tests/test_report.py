import json

from fpl_picker import report


def write_predictions(path, players, gameweek=1):
    json.dump(
        {"gameweek": gameweek, "horizon": 5, "players": players},
        open(path, "w"),
    )


def test_pools_separate_players_who_did_not_play(tmp_path):
    """The whole point of the rewrite: non-players must not flatter the MAE.

    Ghost never features. Under the old single-pool report he counted as
    "predicted 2.0, actual 0" and pulled the average toward zero along with
    several hundred others like him. He now appears only in the `all` pool.
    """
    pred_file = tmp_path / "gw1.json"
    write_predictions(
        pred_file,
        [
            {"id": 1, "name": "Starter", "position": "MID", "price": 8.0,
             "per_gw": 6.0, "ppg": 5.0, "form": 6.0, "ep_next": 5.5},
            {"id": 2, "name": "Cameo", "position": "FWD", "price": 6.0,
             "per_gw": 5.0, "ppg": 4.0, "form": 3.0, "ep_next": 4.0},
            {"id": 3, "name": "Ghost", "position": "DEF", "price": 4.0,
             "per_gw": 2.0, "ppg": 0.0, "form": 0.0, "ep_next": 0.0},
        ],
    )
    data = {
        "history": {
            "1": [{"round": 1, "total_points": 7, "minutes": 90}],
            "2": [{"round": 1, "total_points": 1, "minutes": 20}],
            # player 3 has no row at all -> did not feature
        }
    }
    actuals = report.actual_rows_by_gw(data)
    result = report.score_gameweek(str(pred_file), actuals)

    assert result["gw"] == 1
    assert result["pools"]["all"]["n"] == 3
    assert result["pools"]["played"]["n"] == 2  # Ghost excluded
    assert result["pools"]["starters"]["n"] == 1  # only the 90-minute player

    # |6-7| = 1 over one starter.
    assert abs(result["pools"]["starters"]["mae"] - 1.0) < 1e-9
    # played: (|6-7| + |5-1|) / 2 = 2.5 — materially worse than the all-pool
    # average, which is the honest direction.
    assert abs(result["pools"]["played"]["mae"] - 2.5) < 1e-9
    assert result["pools"]["all"]["mae"] < result["pools"]["played"]["mae"]


def test_baselines_are_scored_not_a_price_regression(tmp_path):
    """Each pool is graded against baselines a real manager would use."""
    pred_file = tmp_path / "gw2.json"
    write_predictions(
        pred_file,
        [
            {"id": 1, "name": "A", "position": "MID", "price": 8.0,
             "per_gw": 6.5, "ppg": 2.0, "form": 2.0, "ep_next": 2.0},
        ],
        gameweek=2,
    )
    data = {"history": {"1": [{"round": 2, "total_points": 7, "minutes": 90}]}}
    result = report.score_gameweek(
        str(pred_file), report.actual_rows_by_gw(data)
    )

    base = result["pools"]["starters"]["baselines"]
    assert set(base) == {"season PPG", "last-5 form", "FPL ep_next"}
    # Our 6.5 is closer to the actual 7 than any baseline's 2.0, so we win.
    assert result["pools"]["starters"]["mae"] < min(base.values())
    assert result["pools"]["starters"]["rmse"] is not None


def test_rmse_punishes_a_missed_haul_harder_than_mae(tmp_path):
    """RMSE exists here because MAE hides whether the model finds hauls."""
    pred_file = tmp_path / "gw3.json"
    write_predictions(
        pred_file,
        [
            {"id": 1, "name": "Hauler", "position": "FWD", "price": 9.0,
             "per_gw": 4.0, "ppg": 4.0, "form": 4.0, "ep_next": 4.0},
        ],
        gameweek=3,
    )
    data = {"history": {"1": [{"round": 3, "total_points": 16, "minutes": 90}]}}
    pool = report.score_gameweek(
        str(pred_file), report.actual_rows_by_gw(data)
    )["pools"]["starters"]
    assert pool["rmse"] >= pool["mae"]


def test_minutes_are_summed_across_a_double_gameweek(tmp_path):
    pred_file = tmp_path / "gw4.json"
    write_predictions(
        pred_file,
        [
            {"id": 1, "name": "Doubler", "position": "MID", "price": 7.0,
             "per_gw": 8.0, "ppg": 4.0, "form": 4.0, "ep_next": 4.0},
        ],
        gameweek=4,
    )
    data = {
        "history": {
            "1": [
                {"round": 4, "total_points": 5, "minutes": 45},
                {"round": 4, "total_points": 6, "minutes": 45},
            ]
        }
    }
    result = report.score_gameweek(
        str(pred_file), report.actual_rows_by_gw(data)
    )
    # 90 minutes in total across the two fixtures, so he is a starter, and
    # the 11 points are aggregated rather than counted once.
    assert result["pools"]["starters"]["n"] == 1
    assert abs(result["pools"]["starters"]["mae"] - 3.0) < 1e-9


def test_unplayed_gameweek_returns_none(tmp_path):
    pred_file = tmp_path / "gw9.json"
    write_predictions(
        pred_file,
        [{"id": 1, "name": "X", "position": "MID", "price": 5.0,
          "per_gw": 3.0, "ppg": 0.0, "form": 0.0, "ep_next": 0.0}],
        gameweek=9,
    )
    assert report.score_gameweek(str(pred_file), {}) is None
