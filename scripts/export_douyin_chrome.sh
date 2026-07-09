#!/usr/bin/env zsh
set -euo pipefail

FAVORITES_URL="${1:-${DOUYIN_FAVORITES_URL:-https://www.douyin.com/user/self?showTab=favorite_collection}}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$HOME/Downloads}"
TIMEOUT_SECONDS="${EXPORT_TIMEOUT_SECONDS:-180}"
PATTERN="douyin-favorites-*.json"

run_chrome_js() {
  /usr/bin/osascript - "$@" <<'APPLESCRIPT'
on run argv
  tell application "Google Chrome"
    if not (exists front window) then make new window
    return execute active tab of front window javascript (item 1 of argv)
  end tell
end run
APPLESCRIPT
}

open_chrome_url() {
  /usr/bin/osascript - "$1" <<'APPLESCRIPT'
on run argv
  tell application "Google Chrome"
    activate
    if not (exists front window) then make new window
    set URL of active tab of front window to item 1 of argv
  end tell
end run
APPLESCRIPT
}

panel_state() {
  run_chrome_js '
(() => {
  const host = document.getElementById("douyin-favorites-exporter-host");
  const root = host && host.shadowRoot;
  if (!root) return JSON.stringify({ hasHost: false });
  return JSON.stringify({
    hasHost: true,
    count: root.querySelector("[data-role=count]")?.textContent || "0",
    status: root.querySelector("[data-role=status]")?.textContent || "",
    exportDisabled: !!root.querySelector("[data-action=export]")?.disabled
  });
})()
'
}

click_action() {
  run_chrome_js "
(() => {
  const host = document.getElementById('douyin-favorites-exporter-host');
  const root = host && host.shadowRoot;
  const button = root && root.querySelector('[data-action=\"$1\"]');
  if (!button) return 'missing';
  button.click();
  return 'clicked';
})()
"
}

latest_new_file() {
  local newest=""
  local newest_mtime=0
  local file mtime
  for file in "$DOWNLOAD_DIR"/${~PATTERN}(N); do
    mtime="$(stat -f %m "$file")"
    if (( mtime >= START_EPOCH && mtime >= newest_mtime )); then
      newest="$file"
      newest_mtime="$mtime"
    fi
  done
  [[ -n "$newest" ]] && print -r -- "$newest"
}

START_EPOCH="$(date +%s)"
open_chrome_url "$FAVORITES_URL"

deadline=$(( START_EPOCH + TIMEOUT_SECONDS ))
while (( $(date +%s) < deadline )); do
  state="$(panel_state 2>/dev/null || true)"
  if [[ "$state" == *'"hasHost":true'* ]]; then
    break
  fi
  sleep 1
done

if [[ "${state:-}" != *'"hasHost":true'* ]]; then
  print -u2 "未找到抖音导出面板。请确认扩展已安装启用，并且当前页面是抖音网页。"
  exit 1
fi

click_action reset >/dev/null || true
sleep 1
click_action scan >/dev/null || true
sleep 1
click_action start >/dev/null

while (( $(date +%s) < deadline )); do
  state="$(panel_state 2>/dev/null || true)"
  if [[ "$state" == *"采集完成"* || "$state" == *"已停止"* ]]; then
    break
  fi
  sleep 2
done

state="$(panel_state 2>/dev/null || true)"
if [[ "$state" == *'"count":"0"'* || "$state" == *'"exportDisabled":true'* ]]; then
  print -u2 "没有可导出的抖音收藏。当前状态：$state"
  exit 1
fi

click_action export >/dev/null

while (( $(date +%s) < deadline )); do
  exported="$(latest_new_file || true)"
  if [[ -n "$exported" ]]; then
    print -r -- "$exported"
    exit 0
  fi
  sleep 1
done

print -u2 "已触发导出，但未在 $DOWNLOAD_DIR 找到新的 $PATTERN"
exit 1
