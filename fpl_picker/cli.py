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
        "--top", type=int, default=0, metavar="N",
        help="also print the top N scored players per position",
    )
    args = parser.parse_args(argv)

    if args.data:
        data = api.load_data(args.data)
        print(f"Loaded data snapshot from {args.data}")
    else:
        print("Fetching live data from the FPL API...")
        data = api.fetch_data()
    if args.save_data:
        api.save_data(data, args.save_data)
        print(f"Saved data snapshot to {args.save_data}")

    gw = api.next_event_id(data["bootstrap"])
    print(f"Projecting from GW{gw} over {args.horizon} gameweeks.")

    players = scoring.score_players(data, horizon=args.horizon)

    if args.overrides:
        import json

        with open(args.overrides) as f:
            overrides = json.load(f)
        unmatched = scoring.apply_overrides(players, overrides)
        print(f"Applied {len(overrides) - len(unmatched)} score override(s).")
        for name in unmatched:
            print(f"  warning: override {name!r} matched no player")

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
        print_team_report(report, args.horizon, args.free_transfers)
        return

    selection = pick_team(
        players,
        budget=args.budget,
        bench_weight=args.bench_weight,
        locked=resolve_names(args.lock, players, "lock"),
        excluded=resolve_names(args.exclude, players, "exclude"),
    )
    print_selection(selection, args.horizon)


if __name__ == "__main__":
    main()
