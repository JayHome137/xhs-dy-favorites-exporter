#!/usr/bin/env zsh
set -euo pipefail

FAVORITES_URL="${1:-${DOUYIN_FAVORITES_URL:-https://www.douyin.com/user/self?showTab=favorite_collection}}"
DOWNLOAD_DIR="${DOWNLOAD_DIR:-$HOME/Downloads}"
TIMEOUT_SECONDS="${EXPORT_TIMEOUT_SECONDS:-180}"
PANEL_WAS_COLLAPSED=0

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

serialize_payload() {
  run_chrome_js '
(() => {
  const host = document.getElementById("douyin-favorites-exporter-host");
  if (!host?.shadowRoot) return "";
  host.removeAttribute("data-export-payload");
  host.dispatchEvent(new Event("douyin-favorites-exporter:serialize"));
  return host.getAttribute("data-export-payload") || "";
})()
'
}

expand_panel() {
  run_chrome_js '
(() => {
  const root = document.getElementById("douyin-favorites-exporter-host")?.shadowRoot;
  const panel = root?.querySelector("#panel");
  const button = root?.querySelector("[data-action=collapse]");
  if (!panel || !button) return "missing";
  if (!panel.classList.contains("collapsed")) return "already-expanded";
  button.click();
  return "clicked";
})()
'
}

restore_panel() {
  if (( PANEL_WAS_COLLAPSED == 0 )); then
    return
  fi
  run_chrome_js '
(() => {
  const root = document.getElementById("douyin-favorites-exporter-host")?.shadowRoot;
  const panel = root?.querySelector("#panel");
  const button = root?.querySelector("[data-action=collapse]");
  if (!panel || !button || panel.classList.contains("collapsed")) return;
  button.click();
})()
' >/dev/null 2>&1 || true
  PANEL_WAS_COLLAPSED=0
}

trap restore_panel EXIT

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

panel_result="$(expand_panel)"
if [[ "$panel_result" == "clicked" ]]; then
  PANEL_WAS_COLLAPSED=1
elif [[ "$panel_result" != "already-expanded" ]]; then
  print -u2 "无法展开抖音导出面板：$panel_result"
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

payload="$(serialize_payload)"
if [[ -z "$payload" ]]; then
  print -u2 "无法读取抖音采集结果"
  exit 1
fi

mkdir -p "$DOWNLOAD_DIR"
exported="$DOWNLOAD_DIR/douyin-favorites-$(date -u '+%Y-%m-%dT%H-%M-%SZ').json"
print -r -- "$payload" > "$exported"
/usr/bin/python3 -m json.tool "$exported" >/dev/null

restore_panel
print -r -- "$exported"
