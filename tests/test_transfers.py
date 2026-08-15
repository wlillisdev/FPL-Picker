import pytest

from fpl_picker import scoring
from fpl_picker.optimizer import pick_team
from fpl_picker.transfers import evaluate_team


@pytest.fixture(scope="module")
def players(snapshot):
    return scoring.score_players(snapshot, horizon=5)


@pytest.fixture(scope="module")
def weak_squad(players):
    """A legal but deliberately mediocre squad: optimal at a tight budget, so
    a richer budget leaves clear room for beneficial transfers."""
    return [p.id for p in pick_team(players, budget=84.0).squad]


def test_zero_transfer_baseline_keeps_squad(players, weak_squad):
    report = evaluate_team(players, weak_squad, bank=0.0, max_transfers=2)
    assert {p.id for p in report.baseline.squad} == set(weak_squad)


def test_transfer_limit_respected(players, weak_squad):
    report = evaluate_team(players, weak_squad, bank=16.0, max_transfers=2)
    for plan in report.plans:
        assert plan.n_transfers <= 2
        assert len(plan.players_out) == len(plan.players_in) == plan.n_transfers
        # Swaps preserve position counts implicitly via squad shape; verify.
        out_pos = sorted(p.position for p in plan.players_out)
        in_pos = sorted(p.position for p in plan.players_in)
        assert out_pos == in_pos


def test_transfers_never_lose_points_gross(players, weak_squad):
    report = evaluate_team(players, weak_squad, bank=16.0, max_transfers=2)
    for plan in report.plans:
        assert plan.gross_points >= report.baseline.projected_points - 1e-6


def test_budget_includes_bank(players, weak_squad):
    by_id = {p.id: p for p in players}
    squad_value = sum(by_id[pid].price for pid in weak_squad)
    report = evaluate_team(players, weak_squad, bank=2.0, max_transfers=2)
    for plan in report.plans:
        assert plan.selection.total_cost <= squad_value + 2.0 + 1e-6


def test_hit_accounting(players, weak_squad):
    report = evaluate_team(
        players, weak_squad, bank=16.0, free_transfers=1, max_transfers=2
    )
    for plan in report.plans:
        expected_hit = max(0, plan.n_transfers - 1) * 4
        assert plan.hit_cost == expected_hit


def test_rating_between_0_and_100(players, weak_squad):
    report = evaluate_team(players, weak_squad, bank=0.0, max_transfers=1)
    assert 0 < report.rating <= 100.0


def test_optimal_squad_rates_100(players):
    optimal_ids = [p.id for p in pick_team(players, budget=100.0).squad]
    report = evaluate_team(players, optimal_ids, bank=0.0, max_transfers=1)
    assert report.rating >= 99.9
    # Already optimal at this budget: nothing should clear the threshold.
    assert report.recommended is None
