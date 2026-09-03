"""Accuracy report: score our logged predictions against what actually happened.

Every run logs its projections to predictions/gw<N>.json. Once a gameweek is
played, its actual points live in the fetched match history — so we can
grade ourselves: mean absolute error overall and by position, versus a naive
price-only baseline, plus how our top-rated players actually did. This is
the honest ledger of whether the system is learning.
"""

import glob
import json
import os


def actual_points_by_gw(data):
    """(player_id, gw) -> actual FPL points, from fetched match history."""
    out = {}
    for pid, rows in (data.get("history") or {}).items():
        for r in rows:
            gw = r.get("round")
            if gw is None:
                continue
            key = (int(pid), int(gw))
            out[key] = out.get(key, 0) + (r.get("total_points") or 0)
    return out


def price_baseline(price):
    """The naive prediction: points from price alone."""
    return 0.32 * price + 0.7


def score_gameweek(pred_file, actuals):
    """Grade one logged prediction file. Returns a result dict or None if the
    gameweek hasn't been played yet."""
    with open(pred_file) as f:
        logged = json.load(f)
    gw = logged["gameweek"]

    rows = []
    for p in logged["players"]:
        actual = actuals.get((p["id"], gw))
        if actual is None:
            actual = 0  # no match row -> didn't feature
        rows.append((p, p.get("per_gw") or 0.0, actual))
    if not any(a for _, _, a in rows):
        return None  # gameweek not played at log-scoring time

    n = len(rows)
    mae = sum(abs(pred - a) for _, pred, a in rows) / n
    base_mae = sum(abs(price_baseline(p["price"]) - a) for p, _, a in rows) / n

    by_pos = {}
    for p, pred, a in rows:
        by_pos.setdefault(p["position"], []).append(abs(pred - a))
    pos_mae = {pos: sum(v) / len(v) for pos, v in by_pos.items()}

    top10 = sorted(rows, key=lambda r: -r[1])[:10]
    top10_return = sum(1 for _, _, a in top10 if a >= 5)

    return {
        "gw": gw,
        "n": n,
        "mae": mae,
        "baseline_mae": base_mae,
        "pos_mae": pos_mae,
        "top10": [(p["name"], pred, a) for p, pred, a in top10],
        "top10_returns": top10_return,
    }


def print_accuracy_report(data, directory="predictions"):
    files = sorted(glob.glob(os.path.join(directory, "gw*.json")))
    if not files:
        print("No logged predictions found — run the picker weekly and this "
              "report builds itself.")
        return
    actuals = actual_points_by_gw(data)

    print("=== Prediction accuracy report ===")
    print("(MAE = mean absolute error per player-GW; a PERFECT model scores "
          "~1.96 — see docs/research/03. Beating the price-only baseline is "
          "the pass mark.)\n")
    any_scored = False
    for f in files:
        result = score_gameweek(f, actuals)
        if result is None:
            print(f"GW{os.path.basename(f)[2:-5]}: not played yet (logged, waiting)")
            continue
        any_scored = True
        beat = "BEAT" if result["mae"] < result["baseline_mae"] else "LOST TO"
        print(
            f"GW{result['gw']}: MAE {result['mae']:.2f} vs price-only "
            f"baseline {result['baseline_mae']:.2f} -> {beat} baseline "
            f"({result['n']} players)"
        )
        pos = "  ".join(f"{k} {v:.2f}" for k, v in sorted(result["pos_mae"].items()))
        print(f"  by position: {pos}")
        print(f"  our top-10 rated: {result['top10_returns']}/10 returned (5+ pts)")
        for name, pred, actual in result["top10"][:5]:
            print(f"    {name:<20} predicted {pred:>5.2f}  actual {actual:>3}")
        print()
    if not any_scored:
        print("\nNo completed gameweeks to score yet.")
