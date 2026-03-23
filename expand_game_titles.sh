#!/usr/bin/env bash
set -euo pipefail

# ----- Configuration -----
CONFIG_FILE="${1:-}"
JSON_URL="https://raw.githubusercontent.com/jsnli/steamappidlist/refs/heads/master/data/games_appid.json"
LOCAL_JSON="games_appid.json"
TMP_FILE=$(mktemp)
trap 'rm -f "$TMP_FILE"' EXIT

# ----- Usage -----
if [[ -z "$CONFIG_FILE" ]]; then
    echo "Usage: $0 <config_file>"
    exit 1
fi

if [[ ! -f "$CONFIG_FILE" ]]; then
    echo "Error: Config file '$CONFIG_FILE' not found."
    exit 1
fi

# ----- Dependencies -----
if ! command -v jq &>/dev/null; then
    echo "Error: 'jq' is required but not installed. Please install jq (https://stedolan.github.io/jq/)."
    exit 1
fi

# ----- Fetch JSON only if missing -----
if [[ ! -f "$LOCAL_JSON" ]]; then
    echo "Downloading $JSON_URL to $LOCAL_JSON ..."
    curl -sSf "$JSON_URL" -o "$LOCAL_JSON" || {
        echo "Error: Failed to download JSON data."
        exit 1
    }
else
    echo "Using cached $LOCAL_JSON (delete it to force a fresh download)."
fi

# ----- Extract existing appids from config as a JSON array of numbers -----
EXISTING_APPIDS_JSON=$(mktemp)
trap 'rm -f "$EXISTING_APPIDS_JSON"' EXIT

awk '/^[[:space:]]*[0-9]+:/ {
    match($0, /[0-9]+/);
    print substr($0, RSTART, RLENGTH)
}' "$CONFIG_FILE" | jq -R -s -c 'split("\n") | map(select(length>0) | tonumber)' > "$EXISTING_APPIDS_JSON"

# ----- Generate new lines for missing appids -----
NEW_PREFIXED=$(mktemp)
trap 'rm -f "$NEW_PREFIXED"' EXIT

jq -r --argjson existing "$(cat "$EXISTING_APPIDS_JSON")" '
    .[] |
    .appid as $appid |
    if $existing | index($appid) then empty else
        "\($appid)\t  \($appid): \"\(.name)\" #\(.name)"
    end
' "$LOCAL_JSON" > "$NEW_PREFIXED"

# ----- Prepare existing lines with appid prefix -----
EXISTING_PREFIXED=$(mktemp)
trap 'rm -f "$EXISTING_PREFIXED"' EXIT

awk '/^[[:space:]]*[0-9]+:/ {
    match($0, /[0-9]+/);
    appid = substr($0, RSTART, RLENGTH);
    printf "%010d\t%s\n", appid, $0
}' "$CONFIG_FILE" > "$EXISTING_PREFIXED"

# ----- Combine, sort, and write final output -----
{
    echo "GameTitles:"
    cat "$EXISTING_PREFIXED" "$NEW_PREFIXED" \
        | sort -n \
        | cut -f2-
} > "$TMP_FILE"

# ----- Backup and replace -----
cp "$CONFIG_FILE" "$CONFIG_FILE.bak"
mv "$TMP_FILE" "$CONFIG_FILE"
echo "Config updated. Backup saved as $CONFIG_FILE.bak"
