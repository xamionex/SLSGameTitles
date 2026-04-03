#!/usr/bin/env python3
import json
import os
import urllib.request
from urllib.error import URLError

JSON_URL = "https://raw.githubusercontent.com/jsnli/steamappidlist/refs/heads/master/data/games_appid.json"
YAML_FILES = {
    "titles.yaml": "original",       # comment = original (unescaped) name
    "originaltitles.yaml": "escaped" # comment = escaped name
}

def fetch_games():
    """Fetch and parse the JSON data from the given URL."""
    try:
        with urllib.request.urlopen(JSON_URL) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data
    except URLError as e:
        print(f"Error fetching data: {e}")
        return None

def escape_yaml_string(s):
    """Escape backslashes and double quotes for a YAML double‑quoted string."""
    s = s.replace('\\', '\\\\')   # escape backslashes
    s = s.replace('"', '\\"')     # escape double quotes
    return s

def read_existing_entries(file_path):
    """
    Read a YAML file with lines of the form:
        id: "escaped_name"  #comment
    Returns a dictionary {id: (escaped_name, comment)} where comment is the
    string after '#', stripped of leading/trailing spaces.
    """
    entries = {}
    if not os.path.exists(file_path):
        return entries

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith("GameTitles:"):
                continue
            # Split at first colon
            if ':' not in line:
                continue
            id_part, rest = line.split(':', 1)
            id_part = id_part.strip()
            if not id_part.isdigit():
                continue
            appid = int(id_part)
            rest = rest.strip()
            # Extract the double-quoted string
            if not rest.startswith('"'):
                continue
            # Find closing quote respecting backslash escapes
            i = 1
            while i < len(rest):
                if rest[i] == '"' and rest[i-1] != '\\':
                    break
                i += 1
            else:
                continue
            quoted_content = rest[1:i]
            # The rest after the closing quote
            after_quote = rest[i+1:].strip()
            comment = ""
            if '#' in after_quote:
                comment = after_quote.split('#', 1)[1].strip()
            entries[appid] = (quoted_content, comment)
    return entries

def main():
    games = fetch_games()
    if games is None:
        return

    # Build dict of original names
    original_names = {}
    for game in games:
        appid = game.get("appid")
        name = game.get("name")
        if appid is not None and name is not None:
            original_names[appid] = name

    for yaml_file, comment_type in YAML_FILES.items():
        existing = read_existing_entries(yaml_file)  # id -> (escaped, comment)
        # Merge: keep existing entries, add missing ones
        merged = {}
        # First copy all existing
        for appid, (escaped, comment) in existing.items():
            merged[appid] = (escaped, comment)
        # Add missing IDs
        for appid, name in original_names.items():
            if appid not in merged:
                escaped = escape_yaml_string(name)
                # Generate comment based on comment_type
                if comment_type == "original":
                    comment = name  # unescaped original name
                else:  # "escaped"
                    comment = escaped
                merged[appid] = (escaped, comment)
        # Write back sorted
        with open(yaml_file, 'w', encoding='utf-8') as f:
            f.write("GameTitles:\n")
            for appid in sorted(merged.keys()):
                escaped, comment = merged[appid]
                f.write(f'  {appid}: "{escaped}"  #{comment}\n')
        # Report changes
        added = len(merged) - len(existing)
        if added == 0:
            print(f"No changes for {yaml_file}")
        else:
            print(f"Updated {yaml_file} with {len(merged)} total entries (added {added} new)")

if __name__ == "__main__":
    main()
