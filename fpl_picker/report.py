"""Accuracy report: score our logged predictions against what happened.

Read this before trusting a number out of it.

An earlier version of this file reported a single mean absolute error over
every player in the game, against a baseline of ``0.32 * price + 0.7``, and
printed "a PERFECT model scores ~1.96" beside it. All three choices were
wrong together, and they flattered the model badly enough to be misleading:

* Most of the ~700 logged players do not play in a given gameweek, and a
  player with no match row is scored as 0 actual. The model predicts near
  zero for them too, so several hundred rows are trivially correct and drag
  the average down toward zero.
* The price baseline predicts ~2.0 points for a £4.0m player, so it eats
  about two points of error on every one of those same non-players. Beating
  it was close to automatic and said nothing about the model.
* The ~1.96 figure comes from a published study measured on a *filtered* pool
  of roughly 178 players per gameweek. Comparing a 700-row average against it
  is comparing different populations.

So accuracy is now reported over three separate pools, never mixed, against
baselines that are actually trying:

* ``all``      — every logged player. Honest only against sane baselines.
* ``played``   — minutes > 0. Target: MAE <= 2.10, RMSE <= 2.90.
* ``starters`` — minutes >= 60. This is the pool the published ceiling of
  MAE 1.957 / RMSE 2.806 applies to. A model claiming much under 1.90 here
  is leaking information, not succeeding.

RMSE is reported alongside MAE because FPL points are right-skewed: MAE
rewards predicting the median and hides whether a model ever finds a haul.
"""

import glob
import json
import math
import os

# The published ceiling for a model with perfect probabilistic knowledge,
# measured on a starters-style pool (FPL Review, "Ultimate Truth", N=3,730).
# Roughly 85% of single-gameweek variance is irreducible, so this is a wall,
# not a stretch goal.
PERFECT_MODEL = {"mae": 1.957, "rmse": 2.806}

POOLS = ("all", "played", "starters")


def actual_rows_by_gw(data):
    """(player_id, gw) -> {"points", "minutes"} from fetched match history."""
    out = {}
    for pid, rows in (data.get("history") or {}).items():
        for r in rows:
            gw = r.get("round")
            if gw is None:
                continue
            key = (int(pid), int(gw))
            agg = out.setdefault(key, {"points": 0, "minutes": 0})
            agg["points"] += r.get("total_points") or 0
            agg["minutes"] += r.get("minutes") or 0
    return out


def baselines(player):
    """Naive predictions worth measuring against.

    A price regression is not one of them: it has no idea who is playing, so
    beating it demonstrates nothing. These three are what a lazy but sensible
    manager would actually use.
    """
    return {
        "season PPG": float(player.get("ppg") or 0.0),
        "last-5 form": float(player.get("form") or 0.0),
        "FPL ep_next": float(player.get("ep_next") or 0.0),
    }


def errors(pairs):
    """(MAE, RMSE) for a list of (predicted, actual) pairs."""
    if not pairs:
        return None, None
    n = len(pairs)
    mae = sum(abs(p - a) for p, a in pairs) / n
    rmse = math.sqrt(sum((p - a) ** 2 for p, a in pairs) / n)
    return mae, rmse


def score_gameweek(pred_file, actuals):
    """Grade one logged prediction file, or None if the gameweek is unplayed."""
    with open(pred_file) as f:
        logged = json.load(f)
    gw = logged["gameweek"]

    rows = []
    for p in logged["players"]:
        row = actuals.get((p["id"], gw))
        # No match row means the player did not feature: zero points, zero
        # minutes. That is a real observation, but it belongs in the "all"
        # pool only — it tells you nothing about predicting a footballer.
        points = (row or {}).get("points", 0)
        minutes = (row or {}).get("minutes", 0)
        rows.append((p, p.get("per_gw") or 0.0, points, minutes))

    if not any(mins for _, _, _, mins in rows):
        return None  # gameweek not played yet

    pools = {
        "all": rows,
        "played": [r for r in rows if r[3] > 0],
        "starters": [r for r in rows if r[3] >= 60],
    }

    result = {"gw": gw, "pools": {}}
    for name, pool in pools.items():
        if not pool:
            continue
        mae, rmse = errors([(pred, a) for _, pred, a, _ in pool])
        base = {}
        for label in baselines(pool[0][0]):
            base[label] = errors(
                [(baselines(p).get(label, 0.0), a) for p, _, a, _ in pool]
            )[0]
        result["pools"][name] = {
            "n": len(pool),
            "mae": mae,
            "rmse": rmse,
            "baselines": base,
        }

    played = pools["played"]
    by_pos = {}
    for p, pred, a, _ in played:
        by_pos.setdefault(p["position"], []).append(abs(pred - a))
    result["pos_mae"] = {pos: sum(v) / len(v) for pos, v in by_pos.items()}

    # Ranking quality on the pool we could actually have picked from, with the
    # same measure applied to a baseline so the number means something.
    ranked = sorted(rows, key=lambda r: -r[1])[:10]
    result["top10"] = [(p["name"], pred, a) for p, pred, a, _ in ranked]
    result["top10_returns"] = sum(1 for _, _, a, _ in ranked if a >= 5)
    ppg_ranked = sorted(rows, key=lambda r: -float(r[0].get("ppg") or 0.0))[:10]
    result["top10_baseline_returns"] = sum(1 for _, _, a, _ in ppg_ranked if a >= 5)
    return result


def print_accuracy_report(data, directory="predictions"):
    files = sorted(glob.glob(os.path.join(directory, "gw*.json")))
    if not files:
        print("No logged predictions found — run the picker weekly and this "
              "report builds itself.")
        return
    actuals = actual_rows_by_gw(data)

    print("=== Prediction accuracy report ===")
    print(
        "Three pools, never mixed. 'starters' (60+ mins) is the only one the\n"
        f"published ceiling applies to: MAE {PERFECT_MODEL['mae']:.3f} / RMSE "
        f"{PERFECT_MODEL['rmse']:.3f} for a model with perfect knowledge.\n"
        "The pass mark is beating season-PPG, last-5 form and FPL's own\n"
        "ep_next on the 'played' and 'starters' pools. One gameweek is not a\n"
        "measurement; look at the trend over several.\n"
    )

    scored = []
    for f in files:
        result = score_gameweek(f, actuals)
        if result is None:
            print(f"GW{os.path.basename(f)[2:-5]}: not played yet (logged, waiting)")
            continue
        scored.append(result)
        print(f"GW{result['gw']}:")
        for name in POOLS:
            pool = result["pools"].get(name)
            if not pool:
                continue
            best_label = min(pool["baselines"], key=lambda k: pool["baselines"][k])
            best = pool["baselines"][best_label]
            verdict = "beat" if pool["mae"] < best else "LOST TO"
            line = (
                f"  {name:<9} n={pool['n']:<4} MAE {pool['mae']:.2f}  "
                f"RMSE {pool['rmse']:.2f}  — {verdict} best baseline "
                f"({best_label} {best:.2f})"
            )
            if name == "starters":
                gap = pool["mae"] - PERFECT_MODEL["mae"]
                line += f"\n            {gap:+.2f} MAE vs the perfect-model ceiling"
            print(line)
        pos = "  ".join(f"{k} {v:.2f}" for k, v in sorted(result["pos_mae"].items()))
        print(f"  by position (played): {pos}")
        print(
            f"  top-10 rated: {result['top10_returns']}/10 returned 5+ pts "
            f"(season-PPG ranking managed "
            f"{result['top10_baseline_returns']}/10)"
        )
        for name, pred, actual in result["top10"][:5]:
            print(f"    {name:<20} predicted {pred:>5.2f}  actual {actual:>3}")
        print()

    if not scored:
        print("\nNo completed gameweeks to score yet.")
        return
    if len(scored) < 5:
        print(
            f"Only {len(scored)} gameweek(s) scored. Single-gameweek error is "
            "mostly noise —\ntreat any difference under ~0.2 MAE as "
            "meaningless until there are several."
        )
