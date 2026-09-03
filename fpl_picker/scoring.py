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
    # Projected points for the NEXT gameweek only (fixture-specific; 0 for a
    # blank). Squad/transfer decisions use the horizon `score`; lineup,
    # bench order, and captaincy use this.
    next_score: float = 0.0


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


def base_points_per_gw(element, n_played=None):
    """Blend the available per-gameweek point signals for one player.

    Components with no data yet (e.g. form/ppg at season start) drop out and
    the remaining weights are renormalized. Early in a season form and ppg
    are averages over one or two matches — a single haul must not read as
    season-long form — so when ``n_played`` (matches with minutes) is known,
    their weights are shrunk by n/(n+4) and FPL's ``ep_next`` estimate
    carries the blend until real track records exist.
    """
    form = _to_float(element.get("form"))
    ppg = _to_float(element.get("points_per_game"))
    ep_next = _to_float(element.get("ep_next"))
    xgi90 = _to_float(element.get("expected_goal_involvements_per_90"))
    minutes = element.get("minutes", 0) or 0

    credibility = 1.0 if n_played is None else n_played / (n_played + 4.0)

    # Rough points-per-GW implied by underlying attacking involvement: a goal
    # or assist is worth ~5 points on average across positions, plus ~2 for
    # appearance. Only meaningful once the player has real minutes.
    ximplied = xgi90 * 5.0 + 2.0 if minutes >= 270 else 0.0

    components = [
        (form, 0.35 * credibility),
        (ppg, 0.25 * credibility),
        (ep_next, 0.25),
        (ximplied, 0.15),
    ]
    live = [(v, w) for v, w in components if v > 0]
    current = (
        sum(v * w for v, w in live) / sum(w for _, w in live) if live else 0.0
    )
    if n_played is None:
        return current

    # Anchor to a price-implied prior early in the season: FPL's price list
    # is the only signal not contaminated by tiny samples (even ep_next is
    # form-derived). The anchor fades as real matches accumulate.
    price = _to_float(element.get("now_cost")) / 10.0
    price_prior = 0.32 * price + 0.7 if price > 0 else current
    return credibility * current + (1.0 - credibility) * price_prior


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
    history = data.get("history") or {}

    team_games = {t["id"]: 0 for t in bootstrap["teams"]}
    for fx in fixtures:
        if fx.get("finished"):
            for tid in (fx.get("team_h"), fx.get("team_a")):
                if tid in team_games:
                    team_games[tid] += 1

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

        rows = history.get(str(element["id"])) or history.get(element["id"])
        if rows is not None:
            n_played = sum(1 for r in rows if (r.get("minutes") or 0) > 0)
        elif history:
            # History was fetched for everyone who has played; absence means
            # this player hasn't played yet — that's n=0 (price prior), not
            # "unknown" (which would skip the anchor and score them 0).
            n_played = 0
        else:
            n_played = None
        per_gw = base_points_per_gw(element, n_played) * availability(element)
        # Participation factor: a price prior assumes the player plays, but a
        # player used in n of his team's G matches earns (n+1)/(G+1) of it —
        # ever-presents keep full value, unused squad players fall to fodder
        # level and stop being "started" by the lineup picker.
        games = team_games.get(team_id, 0)
        if n_played is not None and games > 0:
            per_gw *= (n_played + 1) / (games + 1)
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
                next_score=round(per_gw * (multipliers[0] if multipliers else 0.0), 2),
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


def apply_overrides(players, overrides):
    """Apply manual score multipliers from scouting intel the model can't see.

    ``overrides`` maps player names (case-insensitive web_name match) to
    multipliers, e.g. {"Mbeumo": 1.15, "Szoboszlai": 0.85} for a role upgrade
    and a role downgrade. Returns the names that matched nothing so the
    caller can warn about typos.
    """
    by_name = {}
    for p in players:
        by_name.setdefault(p.name.lower(), []).append(p)

    unmatched = []
    for name, factor in overrides.items():
        matches = by_name.get(name.lower(), [])
        if not matches:
            unmatched.append(name)
            continue
        for p in matches:
            p.score = round(p.score * factor, 2)
            p.per_gw = round(p.per_gw * factor, 2)
            p.next_score = round(p.next_score * factor, 2)

    players.sort(key=lambda p: p.score, reverse=True)
    return unmatched
