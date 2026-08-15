"""Command-line interface for FPL-Picker."""

import argparse
import sys

from . import api, scoring
from .optimizer import pick_team

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
        "--lock", action="append", default=[], metavar="NAME",
        help="force a player into the squad (repeatable)",
    )
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="NAME",
        help="keep a player out of the squad (repeatable)",
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

    if args.top:
        for pos in FORMATION_ORDER:
            print(f"\n--- Top {args.top} {pos} ---")
            for p in [x for x in players if x.position == pos][: args.top]:
                print(format_player(p))

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
