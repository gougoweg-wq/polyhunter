"""Лимиты риска из prediction-market-strategy: 1.5% на ставку, 25% всего открыто, проскальзывание ≤ 50% края."""
import pytest
from polyhunter import risk


def test_exposure_cap():
    assert risk.room(equity=1000, open_cost=240, want=15) == pytest.approx(10)   # до 25% осталось $10
    assert risk.room(equity=1000, open_cost=260, want=15) == 0
    assert risk.room(equity=1000, open_cost=0, want=40) == 15                    # и не больше 1.5% за раз


def test_slippage_gate_walks_the_ladder():
    # край 10 п.п. при лучшем аске 0.40; на $50 средняя цена уходит к 0.47 — съедено 70% края
    asks = [(0.40, 20), (0.50, 1000)]
    ok, avg = risk.slippage_ok(asks, usd=50, edge=0.10)
    assert not ok and avg > 0.45
    ok, avg = risk.slippage_ok([(0.40, 1000)], usd=50, edge=0.10)
    assert ok and avg == pytest.approx(0.40)


def test_phantom_penny_levels_ignored():
    assert risk.clean_asks([(0.01, 5000), (0.02, 10), (0.30, 100)]) == [(0.30, 100)]
