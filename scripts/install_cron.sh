#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOCK_FILE="/tmp/shortrocity.lock"
MARKER_BEGIN="# --- shortrocity schedule begin ---"
MARKER_END="# --- shortrocity schedule end ---"

SKIP_LOCK="${SHORTROCITY_SKIP_LOCK:-0}"

if [[ "$SKIP_LOCK" != "1" ]]; then
    FLOCK_BIN="$(command -v flock || true)"
    if [[ -z "$FLOCK_BIN" ]]; then
        echo "Error: 'flock' command not found. Install util-linux or set SHORTROCITY_SKIP_LOCK=1." >&2
        exit 1
    fi
fi

mkdir -p "$LOG_DIR"

DEFAULT_SCHEDULE="0 0 * * * , 0 8 * * * , 0 16 * * *"
SCHEDULE_LIST="${SHORTROCITY_SCHEDULE:-$DEFAULT_SCHEDULE}"

if command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE_CMD="$(command -v docker-compose)"
else
    DOCKER_COMPOSE_CMD="/usr/bin/env docker compose"
fi

RUN_COMMAND="cd \"$PROJECT_ROOT\" && $DOCKER_COMPOSE_CMD run --rm animalsafarikids >> \"$LOG_DIR/shortrocity.log\" 2>&1"

generate_entries() {
    IFS=',' read -ra entries <<< "$SCHEDULE_LIST"
    for entry in "${entries[@]}"; do
        local trimmed
        trimmed="$(echo "$entry" | xargs)"
        if [[ -n "$trimmed" ]]; then
            if [[ "$SKIP_LOCK" == "1" ]]; then
                echo "$trimmed /bin/bash -lc '$RUN_COMMAND'"
            else
                echo "$trimmed $FLOCK_BIN -n $LOCK_FILE /bin/bash -lc '$RUN_COMMAND'"
            fi
        fi
    done
}

tmpfile="$(mktemp)"
cleanup() {
    rm -f "$tmpfile"
}
trap cleanup EXIT

if crontab -l >/dev/null 2>&1; then
    crontab -l | sed "/$MARKER_BEGIN/,/$MARKER_END/d" > "$tmpfile"
else
    : > "$tmpfile"
fi

{
    echo "$MARKER_BEGIN"
    generate_entries
    echo "$MARKER_END"
} >> "$tmpfile"

crontab "$tmpfile"

echo "Updated crontab with SHORTROCITY schedule:"
generate_entries
echo "Logs will be written to $LOG_DIR/shortrocity.log"
