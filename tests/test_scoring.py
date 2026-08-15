from fpl_picker import scoring


def test_availability_flags():
    assert scoring.availability({"status": "a"}) == 1.0
    assert scoring.availability({"status": "i"}) == 0.0
    assert scoring.availability({"status": "s"}) == 0.0
    assert (
        scoring.availability({"status": "d", "chance_of_playing_next_round": 75})
        == 0.75
    )


def test_base_points_blend_renormalizes_missing_components():
    # Early-season player: no form/ppg yet, only FPL's estimate carries.
    early = {"form": "0.0", "points_per_game": "0.0", "ep_next": "4.0", "minutes": 0}
    assert scoring.base_points_per_gw(early) == 4.0
    # A player with no signals at all scores zero.
    assert scoring.base_points_per_gw({"minutes": 0}) == 0.0


def test_fixture_multipliers_handle_blanks_and_doubles():
    fixtures = [
        {"event": 1, "team_h": 1, "team_a": 2, "team_h_difficulty": 2, "team_a_difficulty": 4},
        # double gameweek 2 for team 1, blank for team 2
        {"event": 2, "team_h": 1, "team_a": 3, "team_h_difficulty": 3, "team_a_difficulty": 3},
        {"event": 2, "team_h": 4, "team_a": 1, "team_h_difficulty": 3, "team_a_difficulty": 3},
    ]
    team1 = scoring.fixture_multipliers(fixtures, 1, 1, 3)
    assert team1[0] > 1.0  # easy fixture boosts
    assert team1[1] == 2.0  # double gameweek counts twice
    assert team1[2] == 0.0  # blank gameweek counts zero
    team2 = scoring.fixture_multipliers(fixtures, 2, 1, 3)
    assert team2[0] < 1.0  # hard fixture penalizes
    assert team2[1] == 0.0


def test_score_players_sorted_and_priced(snapshot):
    players = scoring.score_players(snapshot, horizon=5)
    assert len(players) == 90
    scores = [p.score for p in players]
    assert scores == sorted(scores, reverse=True)
    assert all(3.5 <= p.price <= 15.0 for p in players)
    injured = [p for p in players if p.status == "i"]
    assert all(p.score == 0.0 for p in injured)
