"""«Мозг» новостной модели: любой OpenAI-совместимый API нейросети (Groq, OpenRouter, Gemini, Cerebras…).

Настройка в .env:
  BRAIN_PROVIDER=pollinations    # pollinations (без ключа) | groq | openrouter | gemini | cerebras | custom
  BRAIN_API_KEY=...              # ключ сервиса
  BRAIN_MODEL=...                # необязательно: модель по умолчанию из пресета
  BRAIN_BASE_URL=...             # только для custom
"""
import asyncio
import json
import os
import re
import time

PRESETS = {
    # без ключа и регистрации: открытая модель OpenAI gpt-oss через Pollinations (анонимный лимит)
    "pollinations": ("https://text.pollinations.ai/openai", "openai"),
    "groq": ("https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "openrouter": ("https://openrouter.ai/api/v1", "meta-llama/llama-3.3-70b-instruct:free"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-2.5-flash"),
    "cerebras": ("https://api.cerebras.ai/v1", "llama-3.3-70b"),
}

SYSTEM = ("You are a careful superforecaster. You estimate probabilities of real-world events from news. "
          "Start from base rates, weigh evidence, avoid overreacting to single headlines, and remember that "
          "most dramatic events do not happen within short deadlines. Answer with JSON only.")


KEYLESS = {"pollinations"}


def config():
    provider = os.environ.get("BRAIN_PROVIDER", "pollinations").lower()
    base, model = PRESETS.get(provider, (os.environ.get("BRAIN_BASE_URL", ""), ""))
    return dict(provider=provider, base_url=os.environ.get("BRAIN_BASE_URL", base).rstrip("/"),
                model=os.environ.get("BRAIN_MODEL", model), key=os.environ.get("BRAIN_API_KEY", ""))


def ready():
    c = config()
    return bool((c["key"] or c["provider"] in KEYLESS) and c["base_url"] and c["model"])


def headers(c):
    h = {"Content-Type": "application/json"}
    if c["key"]:
        h["Authorization"] = f"Bearer {c['key']}"
    return h


def forecast_prompt(m, items, now_ts=None, max_items=40):
    """Вопрос, правила разрешения, срок и свежие заголовки. Цену рынка не показываем — против якоря."""
    now_ts = now_ts or time.time()
    today = time.strftime("%Y-%m-%d", time.gmtime(now_ts))
    lines = [f"Today is {today}.", f"Question: {m['question']}", f"Deadline / end date: {m.get('end_date') or 'unknown'}",
             f"Resolution rules: {(m.get('description') or '')[:1500]}", "", "Recent headlines (newest first):"]
    for i, it in enumerate(items[:max_items], 1):
        d = time.strftime("%Y-%m-%d", time.gmtime(it["ts"])) if it.get("ts") else "?"
        lines.append(f"{i}. [{d}] {it['title']} ({it.get('source') or '?'})")
    lines += ["", 'Return JSON: {"p_yes": number 0..1, "confidence": "low"|"medium"|"high", '
              '"reasoning": "max 3 sentences", "key_news": [headline numbers]}']
    return "\n".join(lines)


def parse_forecast(text):
    if not text:
        return None
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S) or re.search(r"(\{.*\})", text, re.S)
    if not m:
        return None
    try:
        d = json.loads(m.group(1))
        p = float(d["p_yes"])
    except (ValueError, KeyError, TypeError):
        return None
    conf = str(d.get("confidence", "low")).lower()
    return dict(p_yes=min(0.99, max(0.01, p)), confidence=conf if conf in ("low", "medium", "high") else "low",
                reasoning=str(d.get("reasoning", ""))[:600], key_news=d.get("key_news") or [])


async def ask(http, prompt, retries=4):
    c = config()
    body = {"model": c["model"], "temperature": 0.2, "max_tokens": 700,
            "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]}
    for attempt in range(retries):
        r = await http.post(f"{c['base_url']}/chat/completions", json=body, headers=headers(c), timeout=120)
        if r.status_code == 429 or r.status_code >= 500:     # бесплатные лимиты: ждём и повторяем
            await asyncio.sleep(min(60, 5 * 2 ** attempt))
            continue
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("brain: rate limited")
