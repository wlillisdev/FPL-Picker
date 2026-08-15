"""Synthetic FPL API snapshot for offline tests."""

import random

import pytest

POSITION_COUNTS = {1: 12, 2: 30, 3: 30, 4: 18}  # element_type -> pool size
NUM_TEAMS = 10


def make_snapshot(seed=42):
    rng = random.Random(seed)
    teams = [
        {"id": t, "name": f"Team {t}", "short_name": f"T{t:02d}"}
        for t in range(1, NUM_TEAMS + 1)
    ]
    events = [
        {"id": gw, "is_next": gw == 1, "is_current": False} for gw in range(1, 39)
    ]

    elements = []
    pid = 0
    for element_type, count in POSITION_COUNTS.items():
        for _ in range(count):
            pid += 1
            form = round(rng.uniform(0.0, 8.0), 1)
            ppg = round(rng.uniform(1.0, 7.0), 1)
            elements.append(
                {
                    "id": pid,
                    "web_name": f"Player{pid}",
                    "team": (pid % NUM_TEAMS) + 1,
                    "element_type": element_type,
                    "now_cost": rng.randrange(40, 145, 5),
                    "form": str(form),
                    "points_per_game": str(ppg),
                    "ep_next": str(round((form + ppg) / 2, 1)),
                    "expected_goal_involvements_per_90": str(
                        round(rng.uniform(0.0, 1.0), 2)
                    ),
                    "minutes": rng.choice([0, 500, 1500, 3000]),
                    "status": rng.choice(["a"] * 8 + ["d", "i"]),
                    "chance_of_playing_next_round": 50,
                    "news": "",
                    "selected_by_percent": "10.0",
                    "total_points": int(ppg * 30),
                }
            )

    fixtures = []
    for gw in range(1, 7):
        order = list(range(1, NUM_TEAMS + 1))
        rng.shuffle(order)
        for i in range(0, NUM_TEAMS, 2):
            fixtures.append(
                {
                    "event": gw,
                    "team_h": order[i],
                    "team_a": order[i + 1],
                    "team_h_difficulty": rng.randint(2, 5),
                    "team_a_difficulty": rng.randint(2, 5),
                }
            )

    return {
        "bootstrap": {"events": events, "teams": teams, "elements": elements},
        "fixtures": fixtures,
    }


@pytest.fixture(scope="session")
def snapshot():
    return make_snapshot()
