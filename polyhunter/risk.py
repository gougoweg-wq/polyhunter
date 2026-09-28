"""Лимиты риска для бумажных моделей (по prediction-market-strategy):
ставка ≤ 1.5% капитала, всё открытое ≤ 25% капитала, проскальзывание ≤ 50% ожидаемого края,
«копеечные» уровни стакана (≤ 2¢) не считаются ликвидностью."""
from .paper import walk_book

MAX_BET = 0.015
MAX_OPEN = 0.25
MAX_SLIP_SHARE = 0.5


def clean_asks(asks, min_price=0.03):
    return [(p, s) for p, s in asks if p >= min_price]


def room(equity, open_cost, want, max_bet=MAX_BET, max_open=MAX_OPEN):
    """Сколько можно поставить: не больше want, 1.5% капитала и остатка до 25% в открытых позициях."""
    return max(0.0, min(want, max_bet * equity, max_open * equity - open_cost))


def slippage_ok(asks, usd, edge, max_share=MAX_SLIP_SHARE):
    """Пройти стакан на всю сумму: средняя цена не должна съесть больше половины края."""
    asks = sorted(asks)
    if not asks:
        return False, None
    shares, cost = walk_book(asks, usd=usd)
    if shares <= 0:
        return False, None
    avg = cost / shares
    return (avg - asks[0][0]) <= max_share * edge, avg
