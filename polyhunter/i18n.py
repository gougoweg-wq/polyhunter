"""Тексты бота на русском и английском. Язык берётся из Telegram (language_code)."""

TIER_ICON = {"S": "💎", "A": "🔥", "B": "✅", "C": "▫️", "D": "🔻", "F": "🧊", "?": "❔"}

T = {
    "ru": {
        "cat.news": "новости", "cat.sports": "спорт", "cat.crypto": "крипта", "cat.all": "все рынки",
        "card.tier": "тир", "card.score": "рейтинг",
        "card.profile": "профиль",
        "card.edge": "Край к ценам: <b>{post} п.п.</b> (сырой {raw}, q = {q})",
        "card.bets": "Ставок до исхода: <b>{n}</b> · событий {events}",
        "card.wins": "Выиграно <b>{wins}</b> при ожидаемых {exp}",
        "card.money": "ROI <b>{roi}</b> · P&amp;L <b>{pnl}</b>",
        "card.best": "Сильнее всего: {cat}",
        "card.timing": "Время входа: цена уходит в его сторону на {t} п.п. за 6 ч сильнее, чем у похожих ставок",
        "card.meaning.S": "Элита: стабильно обыгрывает цены, и это не похоже на везение.",
        "card.meaning.A": "Сильный игрок: обыгрывает цены, уверенность высокая.",
        "card.meaning.B": "Слегка лучше рынка, но доказательств мало.",
        "card.meaning.C": "Играет как рынок.",
        "card.meaning.D": "Чуть хуже цен.",
        "card.meaning.F": "Стабильно хуже цен — его ставки полезно читать наоборот.",
        "card.meaning.?": "Мало ставок до исхода, выводы делать рано.",
        "top.title": "🏆 <b>Умные деньги · {cat}</b>",
        "top.row": "{i}. {icon}<b>{tier}</b> {score} · {who} · ROI {roi} · {n} ставок",
        "top.empty": "Рейтинг ещё считается. Загляните через несколько минут.",
        "top.foot": "Рейтинг 0–100: 50 — как рынок. Край сжат эмпирическим Байесом, чтобы везунчики не всплывали наверх.",
        "alert.smart": "🚨 <b>Умные деньги</b> · {icon}{tier} {who}",
        "alert.fade": "🧊 <b>Сигнал «против»</b> · тир F {who}",
        "alert.follow": "⭐ <b>Ваш список</b> · {who}",
        "alert.fresh": "🐋 <b>Свежий кит</b> · {who} · прошлых ставок: {hist}",
        "alert.bought": "Купил <b>{outcome}</b> по <b>{price}</b> на <b>{usd}</b>",
        "alert.stats": "Рейтинг {score} · край {post} п.п. · ROI {roi}",
        "alert.fade_note": "Его ставки выигрывают на {pp} п.п. реже, чем обещают цены.",
        "alert.fresh_note": "Новый адрес сразу ставит крупно на аутсайдера. Так иногда выглядят ставки со знанием, но это не доказательство.",
        "cluster.title": "🌊 <b>Поток денег</b>: {w} за {m} мин · <b>{usd}</b>",
        "cluster.body": "Исход <b>{outcome}</b>, средняя цена <b>{vwap}</b>",
        "start": ("👋 <b>Polyhunter</b> ищет на Polymarket кошельки, которые выигрывают чаще, чем обещают цены, "
                  "и следит за ними в реальном времени.\n\n"
                  "Что умею:\n"
                  "🏆 /top — рейтинг умных денег\n"
                  "🔎 /wallet <code>адрес или ник</code> — разбор кошелька\n"
                  "📍 /market <code>ссылка</code> — кто крупно ставит на рынок\n"
                  "⭐ /follow <code>адрес</code> — следить за кошельком\n"
                  "🚨 /radar — последние сигналы\n"
                  "⚙️ /alerts — какие сигналы присылать\n\n"
                  "Это аналитика открытых данных, а не финансовый совет."),
        "help": ("<b>Команды</b>\n"
                 "/top [news|sports|crypto|all] — рейтинг\n"
                 "/wallet &lt;адрес|ник&gt; — карточка кошелька\n"
                 "/market &lt;ссылка polymarket&gt; — умные деньги в рынке\n"
                 "/follow &lt;адрес&gt;, /unfollow &lt;адрес&gt;, /following — свой список\n"
                 "/radar — последние сигналы\n"
                 "/alerts — включить или выключить типы сигналов\n"
                 "/threshold &lt;сумма&gt; — минимальная ставка для сигнала\n"
                 "/stats — что мы узнали о рынке\n"
                 "/about — как это считается"),
        "about": ("<b>Как считается рейтинг</b>\n\n"
                  "1. Цена исхода = вероятность, которую дал рынок. Кто ставит по ценам p₁…pₙ, "
                  "при честном рынке выигрывает Σp раз.\n"
                  "2. Берём только ставки, удержанные до исхода, и сравниваем выигрыши с этим ожиданием.\n"
                  "3. Ставки одного события связаны, поэтому значимость считаем по событиям.\n"
                  "4. Кошельков тысячи — поправка Бенджамини–Хохберга (q-value).\n"
                  "5. Край сжимаем эмпирическим Байесом: шумные оценки тянутся к нулю.\n\n"
                  "Тиры: 💎S элита · 🔥A сильный · ✅B чуть лучше · ▫️C как рынок · 🔻D хуже · 🧊F читать наоборот.\n\n"
                  "Данные: открытый API Polymarket. Код: github.com/gougoweg-wq/polyhunter"),
        "follow.ok": "⭐ Слежу за {who}. Пришлю каждую его ставку от {usd}.",
        "follow.bad": "Нужен адрес кошелька 0x… или ник из рейтинга.",
        "unfollow.ok": "Больше не слежу за {who}.",
        "following.empty": "Список пуст. Добавьте кошелёк: /follow <code>адрес</code>",
        "following.title": "⭐ <b>Ваш список</b>",
        "wallet.notfound": "Не нашёл такой кошелёк в базе. Пришлите полный адрес 0x…, я посчитаю его с нуля.",
        "wallet.computing": "⏳ Считаю историю кошелька…",
        "wallet.nodata": "У кошелька мало ставок, удержанных до исхода. Выводы делать рано.",
        "radar.empty": "Сигналов пока нет. Радар проверяет ленту каждые 30 секунд.",
        "radar.title": "🚨 <b>Последние сигналы</b>",
        "alerts.title": "⚙️ <b>Какие сигналы присылать</b>\nНажмите, чтобы включить или выключить.",
        "alerts.smart": "Умные деньги", "alerts.fresh": "Свежие киты", "alerts.cluster": "Потоки денег",
        "alerts.fade": "Сигналы «против»", "alerts.follow": "Мой список",
        "threshold.ok": "Минимальная ставка для сигнала: {usd}.",
        "threshold.bad": "Пример: /threshold 5000",
        "market.bad": "Пришлите ссылку на рынок Polymarket, например https://polymarket.com/event/…",
        "market.notfound": "Не нашёл такой рынок.",
        "market.title": "📍 <b>{title}</b>",
        "market.outcome": "<b>{outcome}</b> · цена {price}",
        "market.smart": "  умные деньги: {usd}", "market.fade": "  «против»: {usd}",
        "market.holder": "  {icon}{tier} {who} — {usd}",
        "market.verdict_yes": "🧭 Умные деньги больше за «{outcome}».",
        "market.verdict_none": "🧭 Умных денег в рынке мало, явного перевеса нет.",
        "stats": ("📈 <b>Что показывают данные</b>\n\n"
                  "• Проверено кошельков: <b>{wallets}</b>, ставок до исхода: <b>{bets}</b>\n"
                  "• Крупные игроки в сумме выигрывают <b>{wr}</b> ставок при обещанных ценами <b>{er}</b>\n"
                  "• Аутсайдеры дешевле 0.2 выигрывают <b>{lw}</b> вместо <b>{le}</b> — их переоценивают\n"
                  "• Тиров 💎S: <b>{s}</b>, 🔥A: <b>{a}</b>, 🧊F: <b>{f}</b>"),
        "err": "Что-то пошло не так. Попробуйте ещё раз через минуту.",
        "btn.top_news": "🗞 Новости", "btn.top_sports": "⚽ Спорт", "btn.top_crypto": "₿ Крипта",
        "btn.top_all": "🌐 Все", "btn.follow": "⭐ Следить", "btn.unfollow": "✖ Не следить",
        "btn.profile": "Профиль на Polymarket", "btn.market": "Открыть рынок",
    },
    "en": {
        "cat.news": "news", "cat.sports": "sports", "cat.crypto": "crypto", "cat.all": "all markets",
        "card.tier": "tier", "card.score": "score",
        "card.profile": "profile",
        "card.edge": "Edge vs prices: <b>{post} pp</b> (raw {raw}, q = {q})",
        "card.bets": "Bets held to resolution: <b>{n}</b> · events {events}",
        "card.wins": "Won <b>{wins}</b> vs {exp} expected",
        "card.money": "ROI <b>{roi}</b> · P&amp;L <b>{pnl}</b>",
        "card.best": "Strongest in: {cat}",
        "card.timing": "Entry timing: price moves his way {t} pp more within 6 h than for similar bets",
        "card.meaning.S": "Elite: consistently beats the prices, and it does not look like luck.",
        "card.meaning.A": "Strong: beats the prices with high confidence.",
        "card.meaning.B": "Slightly better than the market, weak evidence.",
        "card.meaning.C": "Plays like the market.",
        "card.meaning.D": "Slightly worse than prices.",
        "card.meaning.F": "Consistently worse than prices — worth reading in reverse.",
        "card.meaning.?": "Too few resolved bets to judge.",
        "top.title": "🏆 <b>Smart money · {cat}</b>",
        "top.row": "{i}. {icon}<b>{tier}</b> {score} · {who} · ROI {roi} · {n} bets",
        "top.empty": "The leaderboard is still being computed. Check back in a few minutes.",
        "top.foot": "Score 0–100: 50 = the market. Edge is shrunk with empirical Bayes so lucky wallets do not float up.",
        "alert.smart": "🚨 <b>Smart money</b> · {icon}{tier} {who}",
        "alert.fade": "🧊 <b>Fade signal</b> · tier F {who}",
        "alert.follow": "⭐ <b>Your list</b> · {who}",
        "alert.fresh": "🐋 <b>Fresh whale</b> · {who} · past bets: {hist}",
        "alert.bought": "Bought <b>{outcome}</b> at <b>{price}</b> for <b>{usd}</b>",
        "alert.stats": "Score {score} · edge {post} pp · ROI {roi}",
        "alert.fade_note": "His bets win {pp} pp less often than the prices imply.",
        "alert.fresh_note": "A new address goes big on an underdog right away. Informed bets sometimes look like this, but it is not proof.",
        "cluster.title": "🌊 <b>Money flow</b>: {w} in {m} min · <b>{usd}</b>",
        "cluster.body": "Outcome <b>{outcome}</b>, average price <b>{vwap}</b>",
        "start": ("👋 <b>Polyhunter</b> finds Polymarket wallets that win more often than the prices imply "
                  "and tracks them in real time.\n\n"
                  "What I do:\n"
                  "🏆 /top — smart money leaderboard\n"
                  "🔎 /wallet <code>address or name</code> — wallet breakdown\n"
                  "📍 /market <code>link</code> — who bets big on a market\n"
                  "⭐ /follow <code>address</code> — track a wallet\n"
                  "🚨 /radar — latest signals\n"
                  "⚙️ /alerts — choose your signals\n\n"
                  "Open-data analytics, not financial advice."),
        "help": ("<b>Commands</b>\n"
                 "/top [news|sports|crypto|all] — leaderboard\n"
                 "/wallet &lt;address|name&gt; — wallet card\n"
                 "/market &lt;polymarket link&gt; — smart money in a market\n"
                 "/follow &lt;address&gt;, /unfollow &lt;address&gt;, /following — your list\n"
                 "/radar — latest signals\n"
                 "/alerts — toggle signal types\n"
                 "/threshold &lt;amount&gt; — minimum bet size for a signal\n"
                 "/stats — what we learned about the market\n"
                 "/about — how it works"),
        "about": ("<b>How the score works</b>\n\n"
                  "1. An outcome's price is the market's probability. Betting at prices p₁…pₙ, "
                  "a wallet wins Σp times on a fair market.\n"
                  "2. Only bets held to resolution count; wins are compared with that expectation.\n"
                  "3. Bets on one event are correlated, so significance is computed per event.\n"
                  "4. Thousands of wallets — Benjamini–Hochberg correction (q-value).\n"
                  "5. Edge is shrunk with empirical Bayes: noisy estimates are pulled to zero.\n\n"
                  "Tiers: 💎S elite · 🔥A strong · ✅B slightly better · ▫️C market · 🔻D worse · 🧊F fade.\n\n"
                  "Data: public Polymarket API. Code: github.com/gougoweg-wq/polyhunter"),
        "follow.ok": "⭐ Tracking {who}. I will send every bet from {usd}.",
        "follow.bad": "Send a 0x… wallet address or a name from the leaderboard.",
        "unfollow.ok": "No longer tracking {who}.",
        "following.empty": "Your list is empty. Add a wallet: /follow <code>address</code>",
        "following.title": "⭐ <b>Your list</b>",
        "wallet.notfound": "This wallet is not in the database. Send the full 0x… address and I will compute it from scratch.",
        "wallet.computing": "⏳ Computing wallet history…",
        "wallet.nodata": "Too few bets held to resolution to judge.",
        "radar.empty": "No signals yet. The radar checks the feed every 30 seconds.",
        "radar.title": "🚨 <b>Latest signals</b>",
        "alerts.title": "⚙️ <b>Signals to send</b>\nTap to turn on or off.",
        "alerts.smart": "Smart money", "alerts.fresh": "Fresh whales", "alerts.cluster": "Money flows",
        "alerts.fade": "Fade signals", "alerts.follow": "My list",
        "threshold.ok": "Minimum bet size for a signal: {usd}.",
        "threshold.bad": "Example: /threshold 5000",
        "market.bad": "Send a Polymarket market link, e.g. https://polymarket.com/event/…",
        "market.notfound": "Market not found.",
        "market.title": "📍 <b>{title}</b>",
        "market.outcome": "<b>{outcome}</b> · price {price}",
        "market.smart": "  smart money: {usd}", "market.fade": "  fade money: {usd}",
        "market.holder": "  {icon}{tier} {who} — {usd}",
        "market.verdict_yes": "🧭 Smart money leans «{outcome}».",
        "market.verdict_none": "🧭 Little smart money here, no clear lean.",
        "stats": ("📈 <b>What the data shows</b>\n\n"
                  "• Wallets checked: <b>{wallets}</b>, bets held to resolution: <b>{bets}</b>\n"
                  "• Big players win <b>{wr}</b> of bets while prices imply <b>{er}</b>\n"
                  "• Underdogs below 0.2 win <b>{lw}</b> instead of <b>{le}</b> — they are overpriced\n"
                  "• Tier 💎S: <b>{s}</b>, 🔥A: <b>{a}</b>, 🧊F: <b>{f}</b>"),
        "err": "Something went wrong. Please try again in a minute.",
        "btn.top_news": "🗞 News", "btn.top_sports": "⚽ Sports", "btn.top_crypto": "₿ Crypto",
        "btn.top_all": "🌐 All", "btn.follow": "⭐ Follow", "btn.unfollow": "✖ Unfollow",
        "btn.profile": "Polymarket profile", "btn.market": "Open market",
    },
}


def lang_of(code):
    return "ru" if (code or "").lower().startswith(("ru", "uk", "be", "kk", "uz")) else "en"


def tr(lang, key, **kw):
    s = T.get(lang, T["en"]).get(key) or T["en"].get(key, key)
    return s.format(**kw) if kw else s
