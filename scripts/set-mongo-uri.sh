#!/usr/bin/env bash
# Builds the Atlas connection string from a hidden password prompt and writes it
# to .env as MONGODB_URI and MDB_MCP_CONNECTION_STRING. Nothing is echoed.
# Usage: scripts/set-mongo-uri.sh <cluster-host> [db-user]
#   e.g. scripts/set-mongo-uri.sh cluster0.abcde.mongodb.net
set -euo pipefail
cd "$(dirname "$0")/.."
host="${1:?usage: $0 <cluster-host> [db-user]}"
user="${2:-andrewshatsky1_db_user}"
read -rsp "Password for $user: " pw; echo
enc=$(python3 -c 'import sys,urllib.parse;print(urllib.parse.quote(sys.stdin.read().rstrip("\n"),safe=""))' <<<"$pw")
uri="mongodb+srv://${user}:${enc}@${host}/?retryWrites=true&w=majority&appName=Cluster0"
touch .env
python3 - "$uri" <<'PY'
import sys, re, pathlib
p = pathlib.Path(".env"); uri = sys.argv[1]
lines = [l for l in p.read_text().splitlines() if not re.match(r"(MONGODB_URI|MDB_MCP_CONNECTION_STRING)=", l)]
lines += [f"MONGODB_URI={uri}", f"MDB_MCP_CONNECTION_STRING={uri}"]
p.write_text("\n".join(lines) + "\n")
PY
echo "Wrote MONGODB_URI and MDB_MCP_CONNECTION_STRING to .env"
