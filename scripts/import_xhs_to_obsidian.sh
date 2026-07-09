#!/usr/bin/env zsh
set -euo pipefail

VAULT_PATH="${1:-}"
JSON_PATH="${2:-}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$HOME/Downloads}"
SCRIPT_DIR="${0:A:h}"

if [[ -z "$VAULT_PATH" ]]; then
  print -u2 "usage: $0 /path/to/ObsidianVault [xhs-favorites.json]"
  exit 2
fi

if [[ -z "$JSON_PATH" ]]; then
  newest=""
  newest_mtime=0
  for file in "$DOWNLOAD_DIR"/xhs-favorites-*.json(N); do
    mtime="$(stat -f %m "$file")"
    if (( mtime >= newest_mtime )); then
      newest="$file"
      newest_mtime="$mtime"
    fi
  done
  JSON_PATH="$newest"
fi

if [[ -z "$JSON_PATH" || ! -f "$JSON_PATH" ]]; then
  print -u2 "没有找到可导入的小红书 JSON。"
  exit 1
fi

python3 "$SCRIPT_DIR/xhs_to_obsidian.py" --skip-uncategorized --sync-current "$JSON_PATH" "$VAULT_PATH"
rm -f -- "$JSON_PATH"
print -r -- "已导入并删除：$JSON_PATH"
