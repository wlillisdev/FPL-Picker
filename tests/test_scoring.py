from fpl_picker import scoring


def test_availability_flags():
    assert scoring.availability({"status": "a"}) == 1.0
    assert scoring.availability({"status": "i"}) == 0.0
    assert scoring.availability({"status": "s"}) == 0.0
    assert (
        scoring.availability({"status": "d", "chance_of_playing_next_round": 75})
        == 0.75
    )


def test_single_match_form_is_shrunk():
    # After GW1, form == ppg == the one match's score, and even ep_next is
    # form-derived. A 13-point opener from a 6.0m player must not dominate.
    one_hauler = {
        "form": "13.0", "points_per_game": "13.0", "ep_next": "4.0",
        "minutes": 90, "now_cost": 60,
    }
    unshrunk = scoring.base_points_per_gw(one_hauler)
    shrunk = scoring.base_points_per_gw(one_hauler, n_played=1)
    assert shrunk < unshrunk
    assert shrunk < 4.5  # anchored near the 6.0m price prior (~2.6)
    # With a real track record the anchor fades and form dominates again.
    assert scoring.base_points_per_gw(one_hauler, n_played=20) > 8.0


def test_price_prior_ranks_premium_over_one_week_wonder():
    premium_quiet = {
        "form": "4.0", "points_per_game": "4.0", "ep_next": "5.0",
        "minutes": 90, "now_cost": 155,
    }
    cheap_hauler = {
        "form": "13.0", "points_per_game": "13.0", "ep_next": "7.0",
        "minutes": 90, "now_cost": 60,
    }
    assert scoring.base_points_per_gw(
        premium_quiet, n_played=1
    ) > scoring.base_points_per_gw(cheap_hauler, n_played=1)


def test_unused_player_scaled_below_regular(snapshot):
    import copy

    data = copy.deepcopy(snapshot)
    # Two finished matches for team 1; two same-priced team-1 players, one
    # ever-present and one unused.
    for fx in data["fixtures"][:4]:
        if fx["event"] <= 2:
            fx["finished"] = True
            fx["team_h_score"], fx["team_a_score"] = 1, 1
    e1, e2 = data["bootstrap"]["elements"][0], data["bootstrap"]["elements"][1]
    for e in (e1, e2):
        e.update(team=1, now_cost=45, form="2.0", points_per_game="2.0",
                 ep_next="2.0", status="a")
    data["history"] = {
        str(e1["id"]): [{"minutes": 90}, {"minutes": 90}],
        str(e2["id"]): [],
    }
    players = {p.id: p for p in scoring.score_players(data, horizon=3)}
    regular, unused = players[e1["id"]], players[e2["id"]]
    assert unused.score < regular.score * 0.6


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


def test_apply_overrides(snapshot):
    players = scoring.score_players(snapshot, horizon=5)
    target = players[0]
    original = target.score
    unmatched = scoring.apply_overrides(
        players, {target.name.upper(): 0.5, "NoSuchPlayer": 1.2}
    )
    assert unmatched == ["NoSuchPlayer"]
    assert target.score == round(original * 0.5, 2)
    scores = [p.score for p in players]
    assert scores == sorted(scores, reverse=True)  # re-sorted after applying


def test_score_players_sorted_and_priced(snapshot):
    players = scoring.score_players(snapshot, horizon=5)
    assert len(players) == 90
    scores = [p.score for p in players]
    assert scores == sorted(scores, reverse=True)
    assert all(3.5 <= p.price <= 15.0 for p in players)
    injured = [p for p in players if p.status == "i"]
    assert all(p.score == 0.0 for p in injured)
