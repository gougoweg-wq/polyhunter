"""Поставить аватарку бота из assets/avatar.png через Bot API (setMyProfilePhoto).
Запуск: .venv/bin/python -m bot.set_avatar"""
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
token = next(l.split("=", 1)[1].strip() for l in (ROOT / ".env").read_text().splitlines() if l.startswith("BOT_TOKEN="))
r = httpx.post(f"https://api.telegram.org/bot{token}/setMyProfilePhoto",
               data={"photo": json.dumps({"type": "static", "photo": "attach://avatar"})},
               files={"avatar": ("avatar.png", (ROOT / "assets/avatar.png").read_bytes(), "image/png")}, timeout=60)
print(r.json())
