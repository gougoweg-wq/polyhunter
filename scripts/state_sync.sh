#!/bin/sh
# Состояние бота (SQLite + модель) живёт в ветке `state`: один коммит, перезаписываемый force-push'ем.
#   state_sync.sh pull — скачать data/bot.db и data/fade_model.json из ветки state
#   state_sync.sh push — снять консистентный снимок базы и отправить
set -e
REMOTE="${STATE_REMOTE:-origin}"
mkdir -p data
case "$1" in
  pull)
    if git fetch -q "$REMOTE" state 2>/dev/null; then
      git show "$REMOTE/state:bot.db.gz" | gunzip -c > data/bot.db
      git show "$REMOTE/state:fade_model.json" > data/fade_model.json 2>/dev/null || true
      echo "состояние получено: $(du -h data/bot.db | cut -f1)"
    else
      echo "ветки state ещё нет — старт с пустой базы"
    fi ;;
  push)
    tmp=$(mktemp -d)
    python3 - data/bot.db "$tmp/bot.db" << 'PY'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1]); dst = sqlite3.connect(sys.argv[2])
src.backup(dst); dst.close(); src.close()
PY
    gzip -9 -f "$tmp/bot.db"
    db=$(git hash-object -w "$tmp/bot.db.gz")
    entries=$(printf '100644 blob %s\tbot.db.gz\n' "$db")
    if [ -f data/fade_model.json ]; then
      model=$(git hash-object -w data/fade_model.json)
      entries=$(printf '%s\n100644 blob %s\tfade_model.json\n' "$entries" "$model")
    fi
    tree=$(printf '%s\n' "$entries" | git mktree)
    commit=$(GIT_AUTHOR_NAME=polyhunter-bot GIT_AUTHOR_EMAIL=bot@polyhunter \
             GIT_COMMITTER_NAME=polyhunter-bot GIT_COMMITTER_EMAIL=bot@polyhunter \
             git commit-tree "$tree" -m "state $(date -u +%Y-%m-%dT%H:%M:%SZ)")
    git push -q --force "$REMOTE" "$commit:refs/heads/state"
    rm -rf "$tmp"
    echo "состояние отправлено: $(date -u +%H:%M) UTC" ;;
  *) echo "usage: state_sync.sh pull|push"; exit 1 ;;
esac
