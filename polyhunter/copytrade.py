"""Правила копирования сделок лидера на бумажные счета."""


def sell_fraction(sold, remaining):
    """Лидер продал `sold` акций, у него осталось `remaining`: копировщик продаёт ту же долю."""
    if sold <= 0:
        return 0.0
    if not remaining:
        return 1.0
    return sold / (sold + remaining)


def new_trades(acts, cursor):
    """Сделки лидера новее курсора. Первый запуск (cursor=None) ставит курсор и ничего не повторяет."""
    last = max((a["timestamp"] for a in acts), default=cursor)
    if cursor is None:
        return [], last
    fresh = sorted((a for a in acts if a["timestamp"] > cursor), key=lambda a: a["timestamp"])
    return fresh, max(last or 0, cursor)
