"""Честная живая статистика моделей: доход на $ с 95% интервалом и сколько ставок нужно для вывода."""
import math


def settled_returns(trades):
    """Доход на поставленный $ по разрешённым ставкам: pnl / вложенное (вложенное = выплата − pnl)."""
    out = []
    for t in trades:
        if t.get("side") in ("WIN", "LOSS") and t.get("pnl") is not None:
            cost = (t.get("usd") or 0) - t["pnl"]
            if cost > 0:
                out.append(t["pnl"] / cost)
    return out


def live_record(returns, expected=0.075):
    n = len(returns)
    if n == 0:
        return dict(n=0, mean=0.0, lo=0.0, hi=0.0, needed=None, expected=expected)
    m = sum(returns) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in returns) / (n - 1)) if n > 1 else 1.0
    se = sd / math.sqrt(n)
    needed = math.ceil((2 * sd / expected) ** 2) if expected else None     # z≈2: заметить ожидаемый край
    return dict(n=n, mean=m, lo=m - 1.96 * se, hi=m + 1.96 * se, needed=needed, expected=expected)
