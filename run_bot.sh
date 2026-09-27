#!/bin/bash
# Запуск бота. Mac не засыпает, пока бот работает; при падении перезапуск через 10 секунд.
cd "$(dirname "$0")"
[ -f .env ] || { echo "Нет .env — скопируйте .env.example и вставьте BOT_TOKEN"; exit 1; }
[ -d .venv ] || { python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt; }
while true; do
  caffeinate -is .venv/bin/python -m bot.app 2>&1 | tee -a data/bot.log
  echo "бот остановился, перезапуск через 10 с"; sleep 10
done
