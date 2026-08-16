"""Command-line interface for FPL-Picker."""

import argparse
import sys

import requests

from . import api, scoring
from .optimizer import pick_team
from .transfers import evaluate_team

FORMATION_ORDER = ["GK", "DEF", "MID", "FWD"]


def resolve_names(names, players, label):
    """Map user-supplied names to player ids (case-insensitive web_name match)."""
    ids = []
    for name in names:
        matches = [p for p in players if p.name.lower() == name.lower()]
        if not matches:
            partial = [p for p in players if name.lower() in p.name.lower()]
            if len(partial) == 1:
                matches = partial
        if not matches:
            sys.exit(f"error: no player found matching --{label} {name!r}")
        if len(matches) > 1:
            options = ", ".join(f"{p.name} ({p.team})" for p in matches)
            sys.exit(f"error: --{label} {name!r} is ambiguous: {options}")
        ids.append(matches[0].id)
    return ids


def format_player(p, captain=None, vice=None):
    tag = ""
    if captain and p.id == captain.id:
        tag = " (C)"
    elif vice and p.id == vice.id:
        tag = " (V)"
    flag = "" if p.status == "a" else f"  [!{p.status}]"
    return (
        f"  {p.position:<4} {p.name + tag:<22} {p.team:<4} "
        f"£{p.price:>5.1f}m  {p.score:>6.2f} pts{flag}"
    )


def print_selection(selection, horizon):
    xi_shape = {pos: 0 for pos in FORMATION_ORDER}
    for p in selection.starting_xi:
        xi_shape[p.position] += 1
    formation = "-".join(str(xi_shape[pos]) for pos in ["DEF", "MID", "FWD"])

    print(f"\n=== Starting XI ({formation}) ===")
    for p in selection.starting_xi:
        print(format_player(p, selection.captain, selection.vice_captain))
    print("\n=== Bench (in order) ===")
    for p in selection.bench:
        print(format_player(p))
    print(
        f"\nTotal cost: £{selection.total_cost:.1f}m   "
        f"Projected points (next {horizon} GWs, captain doubled): "
        f"{selection.projected_points:.1f}"
    )
    print(f"Captain: {selection.captain.name}   Vice: {selection.vice_captain.name}")


def print_team_report(report, horizon, free_transfers):
    print(f"\n=== Rate my team: {report.rating}/100 ===")
    print(
        f"Your squad projects {report.baseline.projected_points:.1f} pts over the "
        f"next {horizon} GWs (best XI, captain doubled);\n"
        f"a perfect wildcard squad at the same budget projects "
        f"{report.optimal.projected_points:.1f}."
    )

    print("\n=== Best XI from your current squad (no transfers) ===")
    print_selection(report.baseline, horizon)

    print("\n=== Transfer options ===")
    print(f"  (assuming {free_transfers} free transfer(s); hits cost 4 pts)")
    for plan in report.plans:
        if plan.n_transfers == 0:
            print("  No beneficial transfer found at this size.")
            continue
        moves = ", ".join(
            f"{o.name} → {i.name}"
            for o, i in zip(plan.players_out, plan.players_in)
        )
        hit = f", -{plan.hit_cost} hit" if plan.hit_cost else ""
        print(
            f"  {plan.n_transfers} transfer(s): {moves}  "
            f"(net {plan.net_gain:+.1f} pts over {horizon} GWs{hit})"
        )

    if report.recommended:
        plan = report.recommended
        moves = "; ".join(
            f"OUT {o.name} ({o.team}) → IN {i.name} ({i.team})"
            for o, i in zip(plan.players_out, plan.players_in)
        )
        print(f"\nRecommendation: {moves}  [net {plan.net_gain:+.1f} pts]")
    else:
        print(
            "\nRecommendation: hold your transfers — no move clears the "
            "strategy threshold this week (free moves must gain, hits must "
            "gain > 4 + margin)."
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="fpl-picker", description="AI-assisted FPL team picker"
    )
    parser.add_argument("--budget", type=float, default=100.0, help="budget in £m")
    parser.add_argument(
        "--horizon", type=int, default=5, help="gameweeks to project over"
    )
    parser.add_argument(
        "--bench-weight",
        type=float,
        default=0.1,
        help="weight given to bench players' points in the objective",
    )
    parser.add_argument(
        "--team", type=int, metavar="TEAM_ID",
        help="your FPL team ID: rate the squad and suggest transfers instead "
        "of picking from scratch",
    )
    parser.add_argument(
        "--free-transfers", type=int, default=1, metavar="N",
        help="free transfers available this week (default 1)",
    )
    parser.add_argument(
        "--max-transfers", type=int, default=2, metavar="N",
        help="largest number of transfers to consider (default 2)",
    )
    parser.add_argument(
        "--lock", action="append", default=[], metavar="NAME",
        help="force a player into the squad (repeatable)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="NAME",
        help="keep a player out of the squad (repeatable)",
    )
    parser.add_argument(
        "--overrides", metavar="FILE",
        help="JSON file of score multipliers for news the model can't see, "
        'e.g. {"Mbeumo": 1.15, "Szoboszlai": 0.85}',
    )
    parser.add_argument(
        "--data", metavar="FILE", help="load an offline API snapshot instead of fetching"
    )
    parser.add_argument(
        "--save-data", metavar="FILE", help="save the fetched API data to a JSON file"
    )
    parser.add_argument(
        "--with-history", action="store_true",
        help="also fetch per-player match history (needed for --openfpl; "
        "one API call per player, takes a few minutes)",
    )
    parser.add_argument(
        "--with-understat", action="store_true",
        help="also fetch Understat xG data and merge it into the history "
        "(fills the OpenFPL features that are otherwise left blank)",
    )
    parser.add_argument(
        "--rank-mode", choices=["protect", "neutral", "chase"], default="neutral",
        help="rank posture for the captaincy algorithm (default neutral)",
    )
    parser.add_argument(
        "--openfpl", metavar="DIR",
        help="use the OpenFPL pre-trained models from a local clone of "
        "https://github.com/daniegr/OpenFPL as the forecaster (needs match "
        "history in the data; see README)",
    )
    parser.add_argument(
        "--openfpl-folds", type=int, default=5, metavar="N",
        help="how many of OpenFPL's 5 CV folds to load (fewer = faster, default 5)",
    )
    parser.add_argument(
        "--top", type=int, default=0, metavar="N",
        help="also print the top N scored players per position",
    )
    args = parser.parse_args(argv)

    if args.data:
        data = api.load_data(args.data)
        print(f"Loaded data snapshot from {args.data}")
    else:
        print("Fetching live data from the FPL API...")
        data = api.fetch_data(with_history=args.with_history)
        if args.with_understat:
            from . import understat

            season_year = int(
                (data["bootstrap"]["events"][0].get("deadline_time") or "2026")[:4]
            )
            print(f"Fetching Understat data for {season_year}/{season_year + 1}...")
            try:
                us = understat.fetch_understat(season_year)
                matched, total = understat.merge_into_snapshot(data, us)
                print(f"Merged Understat stats for {matched}/{total} players.")
            except Exception as exc:  # site blocked, season not published yet, format drift
                print(
                    f"  warning: Understat data unavailable ({exc}). This is "
                    "normal before the season's first matches are played. "
                    "Continuing without it — xG-ecosystem features stay blank."
                )
    if args.save_data:
        api.save_data(data, args.save_data)
        print(f"Saved data snapshot to {args.save_data}")

    gw = api.next_event_id(data["bootstrap"])
    print(f"Projecting from GW{gw} over {args.horizon} gameweeks.")

    players = scoring.score_players(data, horizon=args.horizon)

    if args.openfpl:
        if not data.get("history"):
            if args.with_history or "history" in data:
                sys.exit(
                    "error: no per-player match history exists yet — no "
                    "matches have been played this season. The OpenFPL "
                    "forecaster works from GW2 onward; until then run "
                    "without --openfpl to use the built-in blend."
                )
            sys.exit(
                "error: --openfpl needs per-player match history in the data. "
                "Refetch with --with-history (and --save-data to keep it), "
                "e.g.: python -m fpl_picker --with-history --save-data data.json"
            )
        from .openfpl import score_with_openfpl

        print("Running OpenFPL ensemble forecaster (this can take a minute)...")
        scores, n_scored, n_skipped = score_with_openfpl(
            data, args.openfpl, horizon=args.horizon, folds=args.openfpl_folds
        )
        for p in players:
            if p.id in scores:
                p.score = round(scores[p.id], 2)
        players.sort(key=lambda p: p.score, reverse=True)
        print(
            f"OpenFPL scored {n_scored} players; kept the blend for "
            f"{n_skipped} without match history."
        )

    if args.overrides:
        import json

        with open(args.overrides) as f:
            overrides = json.load(f)
        unmatched = scoring.apply_overrides(players, overrides)
        print(f"Applied {len(overrides) - len(unmatched)} score override(s).")
        for name in unmatched:
            print(f"  warning: override {name!r} matched no player")

    log_predictions(players, gw, args.horizon)

    if args.top:
        for pos in FORMATION_ORDER:
            print(f"\n--- Top {args.top} {pos} ---")
            for p in [x for x in players if x.position == pos][: args.top]:
                print(format_player(p))

    if args.team:
        try:
            team = api.fetch_team(args.team, data["bootstrap"])
        except ValueError as exc:
            sys.exit(f"error: {exc}")
        except requests.RequestException as exc:
            sys.exit(
                f"error: could not fetch team {args.team} from the FPL API "
                f"({exc}). Note: --team needs direct API access, so run it "
                "from a machine the FPL API doesn't block."
            )
        name = (
            f"{team['entry'].get('player_first_name', '')} "
            f"{team['entry'].get('player_last_name', '')}"
        ).strip()
        print(
            f"\nTeam: {team['entry'].get('name', args.team)}"
            + (f" ({name})" if name else "")
            + f"   Bank: £{team['bank']:.1f}m   Picks from GW{team['event']}"
        )
        report = evaluate_team(
            players,
            team["picks"],
            bank=team["bank"],
            free_transfers=args.free_transfers,
            max_transfers=args.max_transfers,
            bench_weight=args.bench_weight,
        )
        apply_captaincy(report.baseline, data, args.rank_mode)
        print_team_report(report, args.horizon, args.free_transfers)
        return

    selection = pick_team(
        players,
        budget=args.budget,
        bench_weight=args.bench_weight,
        locked=resolve_names(args.lock, players, "lock"),
        excluded=resolve_names(args.exclude, players, "exclude"),
    )
    apply_captaincy(selection, data, args.rank_mode)
    print_selection(selection, args.horizon)


def log_predictions(players, gw, horizon, directory="predictions"):
    """Record this run's projections so we can score ourselves later.

    Writes predictions/gw<N>.json (overwritten per run, so the file reflects
    the last pre-deadline run). The accuracy report in Phase 4 reads these.
    """
    import datetime
    import json
    import os

    try:
        os.makedirs(directory, exist_ok=True)
        path = os.path.join(directory, f"gw{gw}.json")
        payload = {
            "gameweek": gw,
            "horizon": horizon,
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "players": [
                {
                    "id": p.id, "name": p.name, "team": p.team,
                    "position": p.position, "price": p.price,
                    "score": p.score, "per_gw": p.per_gw,
                }
                for p in players
            ],
        }
        with open(path, "w") as f:
            json.dump(payload, f)
        print(f"Logged projections to {path} (for later accuracy scoring).")
    except OSError as exc:
        print(f"  warning: could not log predictions ({exc})")


def apply_captaincy(selection, data, mode):
    """Run the researched captaincy algorithm and update the selection."""
    from .strategy import pick_captain

    advice = pick_captain(selection.starting_xi, data, mode=mode)
    if advice.captain.id != selection.captain.id:
        selection.captain = advice.captain
        selection.vice_captain = max(
            (p for p in selection.starting_xi if p.id != advice.captain.id),
            key=lambda p: p.score,
        )
    print(f"\nCaptaincy ({advice.mode}): {advice.reason}")


if __name__ == "__main__":
    main()
