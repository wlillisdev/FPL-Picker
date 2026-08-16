"""Strategy engine: the captaincy decision framework from docs/research/08.

Implements the researched rules: a high-EO default is rank insurance; deviate
only when the full trigger stack aligns (small xPts gap, big EO gap, home
fixture vs a weak defence), scaled by rank posture (protect/neutral/chase).

EO here is approximated as selected_by_percent scaled up for premium-priced
players (true captaincy shares aren't in the public API); thresholds follow
the research doc's starting calibration and are constants to revisit once we
log our own outcomes.
"""

from dataclasses import dataclass

from .openfpl import team_match_logs

# Calibration constants from docs/research/08-captaincy.md.
STAY_GAP = 2.0        # default keeps the band if it leads by this many pts/GW
DEVIATE_GAP = 1.5     # alternative must be within this of the default
EO_DEFAULT_HIGH = 45  # selected_by % above which the default is "the field's pick"
EO_DIFFERENTIAL = 25  # below this, an alternative is a genuine differential
PREMIUM_PRICE = 9.0   # captaincy defaults are premium-priced players


@dataclass
class CaptainAdvice:
    captain: object
    default: object
    mode: str
    reason: str


def _eo_proxy(player):
    """Effective-ownership proxy: ownership, boosted for premiums (they
    attract the lion's share of captaincies on top of raw ownership)."""
    try:
        owned = float(player.stats.get("selected_by") or 0.0)
    except (TypeError, ValueError):
        owned = 0.0
    return owned * (1.5 if player.price >= PREMIUM_PRICE else 1.05)


def _fixture_boost(player, data):
    """True when the player's next fixture is at home vs a bottom-six-ranked
    opponent (venue-specific xGA ranking is a Phase 2 refinement)."""
    bootstrap = data["bootstrap"]
    fixtures = data["fixtures"]
    from .api import next_event_id

    event = next_event_id(bootstrap)
    logs = team_match_logs(bootstrap, fixtures)
    n_teams = len(bootstrap["teams"])
    for f in fixtures:
        if f.get("event") != event:
            continue
        if f.get("team_h") == player.team_id:
            opponent = f.get("team_a")
            log = logs.get(opponent) or []
            rank = log[-1]["rank"] if log else n_teams // 2
            return rank > n_teams - 6
        if f.get("team_a") == player.team_id:
            return False  # away fixture: no boost
    return False


def pick_captain(starting_xi, data, mode="neutral"):
    """Choose the captain from a starting XI per the researched framework.

    ``mode`` is the rank posture: protect | neutral | chase.
    Returns CaptainAdvice; the Selection's captain can be overridden with it.
    """
    pool = sorted(starting_xi, key=lambda p: p.score, reverse=True)
    best = pool[0]
    default = max(pool, key=_eo_proxy)
    best_leads_by = best.score - default.score

    if mode == "protect":
        if best_leads_by >= STAY_GAP:
            return CaptainAdvice(
                captain=best, default=default, mode=mode,
                reason=f"Even protecting rank, {best.name} projects "
                f"{best_leads_by:.1f} pts above the field's pick — too big to pass.",
            )
        return CaptainAdvice(
            captain=default, default=default, mode=mode,
            reason=f"Protecting rank: shadow the field with {default.name} "
            f"(EO proxy {_eo_proxy(default):.0f}%).",
        )

    if mode == "chase":
        diffs = [
            p for p in pool
            if _eo_proxy(p) < EO_DIFFERENTIAL
            and default.score - p.score <= STAY_GAP
        ]
        if diffs:
            punt = max(diffs, key=lambda p: p.score)
            return CaptainAdvice(
                captain=punt, default=default, mode=mode,
                reason=f"Chasing rank: {punt.name} is a genuine differential "
                f"(EO proxy {_eo_proxy(punt):.0f}%) within range of the default.",
            )
        return CaptainAdvice(
            captain=best, default=default, mode=mode,
            reason="Chasing, but no differential is close enough — take the "
            f"highest projection ({best.name}).",
        )

    # neutral: full trigger stack
    if default.id == best.id:
        return CaptainAdvice(
            captain=default, default=default, mode=mode,
            reason=f"{default.name} is both the field's pick and the highest "
            "projection — the safe armband is also the best one.",
        )
    if (
        _eo_proxy(default) > EO_DEFAULT_HIGH
        and _eo_proxy(best) < EO_DEFAULT_HIGH
        and default.score - best.score <= DEVIATE_GAP
        and _fixture_boost(best, data)
    ):
        return CaptainAdvice(
            captain=best, default=default, mode=mode,
            reason=f"Deviation triggers met: {best.name} projects at least as "
            f"well, is home to a bottom-six side, and carries far lower EO "
            f"than {default.name}.",
        )
    if best_leads_by > STAY_GAP:
        return CaptainAdvice(
            captain=best, default=default, mode=mode,
            reason=f"{best.name} out-projects the field's pick by "
            f"{best_leads_by:.1f} pts over the horizon — captain the points.",
        )
    return CaptainAdvice(
        captain=default, default=default, mode=mode,
        reason=f"No deviation trigger: keep the boring, high-EO armband "
        f"({default.name}). The research says this is how titles are won.",
    )
