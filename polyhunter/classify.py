"""Категория рынка по названию и слагу: sports / crypto / news."""
import re

SPORTS = re.compile(
    r"\b(vs\.?|win on|spread|o/u|over/under|fc|nfl|nba|mlb|nhl|epl|ufc|dota|cs2|lol|valorant|"
    r"premier league|champions league|europa league|serie a|la liga|bundesliga|ligue 1|tennis|atp|wta|"
    r"grand prix|f1|us open|wimbledon|roland garros|french open|australian open|world cup|olympics?|"
    r"super bowl|stanley cup|nba finals|world series|ballon d'or|top goal ?scorer|mvp|boxing|fight night|"
    r"heavyweight|golf|pga|masters|cricket|ipl|halftime|exact score|goal ?scorer|euro 20\d\d|copa|"
    r"playoffs?|relegated|championship)\b", re.I)
SPORT_SLUG = re.compile(r"^(epl|nfl|nba|mlb|nhl|unl|ucl|atp|wta|cs2|lol|dota|ufc|mls|cfb|ncaab)-")
CRYPTO = re.compile(r"\b(bitcoin|btc|ethereum|eth|solana|sol|xrp|doge|crypto|up or down)\b", re.I)


def category(title, slug=""):
    s = f"{title or ''} {slug or ''}"
    if CRYPTO.search(s):
        return "crypto"
    if SPORTS.search(s) or SPORT_SLUG.match(slug or ""):
        return "sports"
    return "news"
