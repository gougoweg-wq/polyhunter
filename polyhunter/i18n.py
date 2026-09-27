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
                  "<b>Тестовая торговля</b> ($1 000 не настоящих денег, цены — живой стакан):\n"
                  "💼 /paper — счёт · пришлите ссылку на рынок — кнопки покупки\n"
                  "🤖 /ai — модель «против китов» · /copy ai 20 — копировать её\n"
                  "📋 /copy <code>адрес</code> 25 — копировать кошелёк · 🏁 /leaders · ⚡ /desk\n\n"
                  "Это аналитика открытых данных, а не финансовый совет."),
        "help": ("<b>Команды</b>\n"
                 "/top [news|sports|crypto|all] — рейтинг\n"
                 "/wallet &lt;адрес|ник&gt; — карточка кошелька\n"
                 "/market &lt;ссылка polymarket&gt; — умные деньги в рынке\n"
                 "/follow &lt;адрес&gt;, /unfollow &lt;адрес&gt;, /following — свой список\n"
                 "/radar — последние сигналы\n"
                 "/alerts — включить или выключить типы сигналов\n"
                 "/threshold &lt;сумма&gt; — минимальная ставка для сигнала\n"
                 "/paper — тестовый счёт, /reset — сбросить\n"
                 "/ai — модель, /copy ai 20 — копировать её\n"
                 "/copy &lt;адрес&gt; 25, /copies, /uncopy &lt;адрес&gt; — копирование\n"
                 "/leaders — лидеры, /desk — бот polydesk\n"
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
        "alerts.fade": "Сигналы «против»", "alerts.follow": "Мой список", "alerts.ai": "Сделки модели",
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
        "paper.title": "💼 <b>Счёт</b> · тестовые деньги",
        "paper.equity": "Капитал <b>{eq}</b> · свободно {cash} · итог <b>{pnl}</b> ({pct})",
        "paper.empty": "Позиций нет. Пришлите ссылку на рынок, чтобы купить, или /copy ai — копировать модель.",
        "paper.pos": "{i}. <b>{outcome}</b> · {title}\n    {shares} акц. · вход {entry} → сейчас {mark} · <b>{pnl}</b>",
        "paper.foot": "Цены — живой стакан Polymarket. Деньги тестовые.",
        "ai.title": "🤖 <b>Модель «против китов»</b> · эксперимент",
        "ai.what": ("Крупные игроки Polymarket в среднем переплачивают: их исходы выигрывают реже своей цены. "
                    "Модель видит крупную покупку кошелька обычного тира и, если перевес ≥ 2 п.п., покупает "
                    "противоположный исход. Против тиров 💎S и 🔥A не ставит. Размер — ¼ Келли, не больше 2% счёта."),
        "ai.backtest": ("Проверка на будущем ({a} — {b}): {bets} ставок, ROI <b>{roi}</b> (95%: {lo} … {hi}), "
                        "log-loss {ll} против {mll} у цен рынка."),
        "ai.caveat": "Это верхняя оценка: проверка по средним ценам позиций. Настоящий результат — живой счёт ниже.",
        "ai.off": "Модель сейчас не торгует: на проверке она не обыграла цены рынка.",
        "ai.account": "Живой счёт модели: <b>{eq}</b> · итог <b>{pnl}</b> · позиций {n}",
        "ai.last": "Последние сделки:",
        "ev.ai_fade": "🤖 <b>Модель</b> ставит против кита: {tier} купил «{lo}» по {lp}\nКупила <b>{outcome}</b> по <b>{price}</b> на <b>{usd}</b> · оценка модели {pm}",
        "ev.ai_follow": "🤖 <b>Модель</b> повторяет сильный кошелёк\nКупила <b>{outcome}</b> по <b>{price}</b> на <b>{usd}</b> · оценка модели {pm}",
        "ev.copy_buy": "📋 <b>Скопировано</b> ({leader}): куплено <b>{outcome}</b> по {price} на {usd}",
        "ev.copy_sell": "📋 <b>Скопировано</b> ({leader}): продано {frac} позиции «{outcome}» по {price} · {pnl}",
        "ev.copy_fail": "📋 Не удалось скопировать ({leader}): {reason}",
        "ev.settle_win": "✅ <b>Рынок разрешился</b>: «{outcome}» выиграл · {pnl}",
        "ev.settle_loss": "❌ <b>Рынок разрешился</b>: «{outcome}» проиграл · {pnl}",
        "desk.title": "⚡ <b>polydesk</b> · бот на 5-минутных рынках биткоина (бумага)",
        "desk.body": "Капитал <b>{eq}</b> (старт {start}) · реализовано <b>{pnl}</b>\nРынков {m} · выиграно {winp} · сделок за сутки {f}",
        "desk.last": "Последние рынки:",
        "desk.none": "polydesk не запущен или ещё не торговал.",
        "lead.title": "🏁 <b>Лидеры бумажной торговли</b>",
        "lead.empty": "Пока никто не торговал.",
        "buy.ok": "✅ Куплено <b>{outcome}</b> · {shares} акц. по {price} на {usd}",
        "buy.partial": " (стакан тонкий — исполнено частично)",
        "sell.ok": "✅ Продано {shares} акц. по {price} · {pnl}",
        "err.cash": "Не хватает тестовых денег. /paper — посмотреть счёт, /reset — начать заново.",
        "err.no_liquidity": "В стакане нет подходящих заявок.",
        "err.no_position": "Этой позиции уже нет.",
        "copy.ok": "📋 Копирую {who}: каждая его покупка — {usd} с вашего тестового счёта, продажи — той же долей.",
        "copy.ai": "📋 Копирую модель: каждая её ставка — {usd} с вашего тестового счёта.",
        "copy.bad": "Пример: /copy ai 20 или /copy &lt;адрес&gt; 25",
        "copy.list": "📋 <b>Копирую</b>",
        "copy.none": "Вы никого не копируете. /copy ai 20 — копировать модель.",
        "copy.off": "Больше не копирую {who}.",
        "reset.ask": "Сбросить счёт до $1,000? Позиции и история удалятся.",
        "reset.ok": "Счёт сброшен: $1,000.",
        "market.buy_hint": "Кнопки ниже — купить исход на тестовые деньги.",
        "btn.buy": "🛒 {usd} · {outcome}",
        "btn.sell_half": "Продать ½ #{i}", "btn.sell_all": "Продать всё #{i}",
        "btn.copy_ai": "📋 Копировать модель $20", "btn.ai_alerts": "🔔 Сделки модели",
        "btn.reset_yes": "Да, сбросить", "btn.cancel": "Отмена", "btn.uncopy": "✖ {who}",
        "btn.radar": "🚨 Радар", "btn.alerts": "⚙️ Сигналы",
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
                  "<b>Paper trading</b> ($1,000 of test money, live order-book prices):\n"
                  "💼 /paper — account · send a market link to get buy buttons\n"
                  "🤖 /ai — fade-the-whales model · /copy ai 20 — copy it\n"
                  "📋 /copy <code>address</code> 25 — copy a wallet · 🏁 /leaders · ⚡ /desk\n\n"
                  "Open-data analytics, not financial advice."),
        "help": ("<b>Commands</b>\n"
                 "/top [news|sports|crypto|all] — leaderboard\n"
                 "/wallet &lt;address|name&gt; — wallet card\n"
                 "/market &lt;polymarket link&gt; — smart money in a market\n"
                 "/follow &lt;address&gt;, /unfollow &lt;address&gt;, /following — your list\n"
                 "/radar — latest signals\n"
                 "/alerts — toggle signal types\n"
                 "/threshold &lt;amount&gt; — minimum bet size for a signal\n"
                 "/paper — test account, /reset — reset it\n"
                 "/ai — the model, /copy ai 20 — copy it\n"
                 "/copy &lt;address&gt; 25, /copies, /uncopy &lt;address&gt; — copy trading\n"
                 "/leaders — leaders, /desk — polydesk bot\n"
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
        "alerts.fade": "Fade signals", "alerts.follow": "My list", "alerts.ai": "Model trades",
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
        "paper.title": "💼 <b>Account</b> · test money",
        "paper.equity": "Equity <b>{eq}</b> · free {cash} · P&amp;L <b>{pnl}</b> ({pct})",
        "paper.empty": "No positions. Send a market link to buy, or /copy ai to copy the model.",
        "paper.pos": "{i}. <b>{outcome}</b> · {title}\n    {shares} sh · entry {entry} → now {mark} · <b>{pnl}</b>",
        "paper.foot": "Prices come from the live Polymarket order book. Money is not real.",
        "ai.title": "🤖 <b>Fade-the-whales model</b> · experiment",
        "ai.what": ("Big Polymarket players overpay on average: their outcomes win less often than their price. "
                    "When a regular-tier wallet buys big and the edge is ≥ 2 pp, the model buys the opposite "
                    "outcome. It never fades 💎S and 🔥A wallets. Size: ¼ Kelly, at most 2% of the account."),
        "ai.backtest": ("Out-of-sample test ({a} — {b}): {bets} bets, ROI <b>{roi}</b> (95%: {lo} … {hi}), "
                        "log-loss {ll} vs {mll} for market prices."),
        "ai.caveat": "This is an upper bound: the test uses average position prices. The live account below is the real result.",
        "ai.off": "The model is not trading: it did not beat market prices out of sample.",
        "ai.account": "Live model account: <b>{eq}</b> · P&amp;L <b>{pnl}</b> · positions {n}",
        "ai.last": "Latest trades:",
        "ev.ai_fade": "🤖 <b>Model</b> fades a whale: {tier} bought «{lo}» at {lp}\nBought <b>{outcome}</b> at <b>{price}</b> for <b>{usd}</b> · model estimate {pm}",
        "ev.ai_follow": "🤖 <b>Model</b> follows a strong wallet\nBought <b>{outcome}</b> at <b>{price}</b> for <b>{usd}</b> · model estimate {pm}",
        "ev.copy_buy": "📋 <b>Copied</b> ({leader}): bought <b>{outcome}</b> at {price} for {usd}",
        "ev.copy_sell": "📋 <b>Copied</b> ({leader}): sold {frac} of «{outcome}» at {price} · {pnl}",
        "ev.copy_fail": "📋 Could not copy ({leader}): {reason}",
        "ev.settle_win": "✅ <b>Market resolved</b>: «{outcome}» won · {pnl}",
        "ev.settle_loss": "❌ <b>Market resolved</b>: «{outcome}» lost · {pnl}",
        "desk.title": "⚡ <b>polydesk</b> · bitcoin 5-minute markets bot (paper)",
        "desk.body": "Equity <b>{eq}</b> (start {start}) · realized <b>{pnl}</b>\nMarkets {m} · won {winp} · fills in 24 h {f}",
        "desk.last": "Latest markets:",
        "desk.none": "polydesk is not running or has not traded yet.",
        "lead.title": "🏁 <b>Paper trading leaders</b>",
        "lead.empty": "Nobody has traded yet.",
        "buy.ok": "✅ Bought <b>{outcome}</b> · {shares} sh at {price} for {usd}",
        "buy.partial": " (thin book — partially filled)",
        "sell.ok": "✅ Sold {shares} sh at {price} · {pnl}",
        "err.cash": "Not enough test money. /paper to view the account, /reset to start over.",
        "err.no_liquidity": "No suitable orders in the book.",
        "err.no_position": "This position is already gone.",
        "copy.ok": "📋 Copying {who}: each of their buys is {usd} from your test account, sells at the same fraction.",
        "copy.ai": "📋 Copying the model: each of its bets is {usd} from your test account.",
        "copy.bad": "Example: /copy ai 20 or /copy &lt;address&gt; 25",
        "copy.list": "📋 <b>Copying</b>",
        "copy.none": "You are not copying anyone. /copy ai 20 to copy the model.",
        "copy.off": "No longer copying {who}.",
        "reset.ask": "Reset the account to $1,000? Positions and history will be deleted.",
        "reset.ok": "Account reset: $1,000.",
        "market.buy_hint": "Use the buttons below to buy an outcome with test money.",
        "btn.buy": "🛒 {usd} · {outcome}",
        "btn.sell_half": "Sell ½ #{i}", "btn.sell_all": "Sell all #{i}",
        "btn.copy_ai": "📋 Copy model $20", "btn.ai_alerts": "🔔 Model trades",
        "btn.reset_yes": "Yes, reset", "btn.cancel": "Cancel", "btn.uncopy": "✖ {who}",
        "btn.radar": "🚨 Radar", "btn.alerts": "⚙️ Alerts",
    },
}


def lang_of(code):
    return "ru" if (code or "").lower().startswith(("ru", "uk", "be", "kk", "uz")) else "en"


def tr(lang, key, **kw):
    s = T.get(lang, T["en"]).get(key) or T["en"].get(key, key)
    return s.format(**kw) if kw else s
