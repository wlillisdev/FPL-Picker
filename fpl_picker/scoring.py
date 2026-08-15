"""Expected-points model for FPL players.

Projects each player's expected points over the next few gameweeks by blending
recent form, season points per game, FPL's own next-round estimate, and
underlying attacking numbers — then adjusting for availability and fixture
difficulty.
"""

from dataclasses import dataclass, field

POSITIONS = {1: "GK", 2: "DEF", 3: "MID", 4: "FWD"}

# How much an easier/harder fixture swings a single gameweek's projection.
# Difficulty runs 2 (easiest) to 5 (hardest); 3 is neutral.
FIXTURE_SWING = 0.08
# Future gameweeks are discounted so near fixtures dominate the pick.
DECAY = 0.85


@dataclass
class Player:
    id: int
    name: str
    team_id: int
    team: str
    position: str
    price: float  # in £m
    score: float  # projected points over the horizon
    per_gw: float  # projected points for a single neutral gameweek
    status: str
    news: str = ""
    stats: dict = field(default_factory=dict)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def availability(element):
    """Probability (0-1) that the player is available to play."""
    status = element.get("status", "a")
    if status in ("i", "s", "u", "n"):  # injured, suspended, unavailable, not in squad
        return 0.0
    chance = element.get("chance_of_playing_next_round")
    if status == "d" and chance is not None:  # doubtful
        return chance / 100.0
    return 1.0


def base_points_per_gw(element):
    """Blend the available per-gameweek point signals for one player.

    Components with no data yet (e.g. form/ppg at season start) drop out and
    the remaining weights are renormalized, so the model degrades gracefully
    in early gameweeks when FPL's ``ep_next`` and underlying per-90 numbers
    carry the estimate.
    """
    form = _to_float(element.get("form"))
    ppg = _to_float(element.get("points_per_game"))
    ep_next = _to_float(element.get("ep_next"))
    xgi90 = _to_float(element.get("expected_goal_involvements_per_90"))
    minutes = element.get("minutes", 0) or 0

    # Rough points-per-GW implied by underlying attacking involvement: a goal
    # or assist is worth ~5 points on average across positions, plus ~2 for
    # appearance. Only meaningful once the player has real minutes.
    ximplied = xgi90 * 5.0 + 2.0 if minutes >= 270 else 0.0

    components = [
        (form, 0.35),
        (ppg, 0.25),
        (ep_next, 0.25),
        (ximplied, 0.15),
    ]
    live = [(v, w) for v, w in components if v > 0]
    if not live:
        return 0.0
    total_weight = sum(w for _, w in live)
    return sum(v * w for v, w in live) / total_weight


def fixture_multipliers(fixtures, team_id, from_event, horizon):
    """Per-gameweek fixture multiplier for a team over the horizon.

    Returns a list of ``horizon`` floats, one per gameweek starting at
    ``from_event``. A gameweek's value sums a difficulty-adjusted multiplier
    for each fixture the team plays in it — so double gameweeks score ~2x and
    blank gameweeks score 0.
    """
    events = {}
    for fx in fixtures:
        event = fx.get("event")
        if event is None or not (from_event <= event < from_event + horizon):
            continue
        if fx.get("team_h") == team_id:
            difficulty = fx.get("team_h_difficulty", 3)
        elif fx.get("team_a") == team_id:
            difficulty = fx.get("team_a_difficulty", 3)
        else:
            continue
        multiplier = 1.0 + (3 - (difficulty or 3)) * FIXTURE_SWING
        events[event] = events.get(event, 0.0) + max(multiplier, 0.0)
    return [events.get(from_event + k, 0.0) for k in range(horizon)]


def score_players(data, horizon=5):
    """Score every player in an API snapshot.

    Returns a list of :class:`Player` sorted by projected score (descending).
    """
    bootstrap = data["bootstrap"]
    fixtures = data["fixtures"]
    from .api import next_event_id

    start_event = next_event_id(bootstrap)
    teams = {t["id"]: t for t in bootstrap["teams"]}
    team_fixture_cache = {}

    players = []
    for element in bootstrap["elements"]:
        position = POSITIONS.get(element["element_type"])
        if position is None:  # skip managers/other element types
            continue
        team_id = element["team"]
        if team_id not in team_fixture_cache:
            team_fixture_cache[team_id] = fixture_multipliers(
                fixtures, team_id, start_event, horizon
            )
        multipliers = team_fixture_cache[team_id]

        per_gw = base_points_per_gw(element) * availability(element)
        score = sum(
            per_gw * mult * (DECAY**k) for k, mult in enumerate(multipliers)
        )

        players.append(
            Player(
                id=element["id"],
                name=element["web_name"],
                team_id=team_id,
                team=teams[team_id]["short_name"],
                position=position,
                price=element["now_cost"] / 10.0,
                score=round(score, 2),
                per_gw=round(per_gw, 2),
                status=element.get("status", "a"),
                news=element.get("news", "") or "",
                stats={
                    "form": element.get("form"),
                    "ppg": element.get("points_per_game"),
                    "ep_next": element.get("ep_next"),
                    "selected_by": element.get("selected_by_percent"),
                    "total_points": element.get("total_points"),
                },
            )
        )

    players.sort(key=lambda p: p.score, reverse=True)
    return players
