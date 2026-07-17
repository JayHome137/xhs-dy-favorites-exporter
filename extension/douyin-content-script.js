(function bootstrapDouyinFavoritesExporter() {
  if (window.__DOUYIN_FAVORITES_EXPORTER__) return;
  window.__DOUYIN_FAVORITES_EXPORTER__ = true;

  var HOST_ID = "douyin-favorites-exporter-host";
  var AUTO_SCROLL_DELAY_MS = 1200;
  var MAX_IDLE_ROUNDS = 5;
  var MAX_TITLE_LENGTH = 160;

  var state = {
    items: new Map(),
    running: false,
    idleRounds: 0,
    timerId: null,
    statusText: "等待采集"
  };

  var ui = {};

  function text(value) {
    return String(value || "").replace(/\s+/g, " ").trim();
  }

  function clampTitle(value) {
    var result = text(value);
    return result ? result.slice(0, MAX_TITLE_LENGTH) : "无标题";
  }

  function absoluteUrl(href) {
    try {
      return new URL(href, location.href).href;
    } catch (_) {
      return String(href || "");
    }
  }

  function parseCard(anchor) {
    var url = absoluteUrl(anchor.getAttribute("href"));
    var match = url.match(/\/video\/(\d+)/);
    if (!match) return null;

    var image = anchor.querySelector("img");
    var alt = text(image && image.getAttribute("alt"));
    var author = "";
    var title = alt || text(anchor.textContent);
    var colonIndex = title.indexOf("：");

    if (colonIndex > 0 && colonIndex < 40) {
      author = text(title.slice(0, colonIndex));
      title = text(title.slice(colonIndex + 1));
    }

    return {
      aweme_id: match[1],
      title: clampTitle(title),
      author: author,
      url: url,
      cover: image ? image.src : null,
      note_type: "video",
      source: "dom"
    };
  }

  function scanDom() {
    var before = state.items.size;
    document.querySelectorAll('a[href*="/video/"]').forEach(function (anchor) {
      var item = parseCard(anchor);
      if (!item) return;
      state.items.set(item.aweme_id, Object.assign({}, state.items.get(item.aweme_id), item));
    });

    if (state.items.size > before) {
      state.idleRounds = 0;
      setStatus("已采集 " + state.items.size + " 条");
    }

    render();
    return state.items.size - before;
  }

  function findScrollContainer() {
    var route = document.querySelector(".route-scroll-container");
    if (route && route.scrollHeight > route.clientHeight) return route;

    var best = null;
    Array.from(document.querySelectorAll("body *")).forEach(function (element) {
      var overflowY = getComputedStyle(element).overflowY;
      var canScroll = element.scrollHeight > element.clientHeight + 80;
      if (!canScroll || overflowY === "visible") return;
      if (!best || element.scrollHeight > best.scrollHeight) best = element;
    });

    return best || document.scrollingElement || document.documentElement;
  }

  function startCollection() {
    if (state.running) return;

    state.running = true;
    state.idleRounds = 0;
    setStatus("开始采集");
    scanDom();
    tick();
  }

  function tick() {
    if (!state.running) return;

    var before = state.items.size;
    var container = findScrollContainer();
    if (container) {
      container.scrollTop = container.scrollHeight;
    }

    window.scrollTo(0, document.documentElement.scrollHeight);
    scanDom();

    if (state.items.size === before) {
      state.idleRounds += 1;
    } else {
      state.idleRounds = 0;
    }

    if (state.idleRounds >= MAX_IDLE_ROUNDS) {
      stopCollection("采集完成，共 " + state.items.size + " 条");
      return;
    }

    state.timerId = window.setTimeout(tick, AUTO_SCROLL_DELAY_MS);
  }

  function stopCollection(message) {
    state.running = false;
    if (state.timerId) {
      window.clearTimeout(state.timerId);
      state.timerId = null;
    }
    setStatus(message || "已停止，共 " + state.items.size + " 条");
  }

  function resetResults() {
    stopCollection("已清空");
    state.items.clear();
    state.idleRounds = 0;
    render();
  }

  function exportResults() {
    scanDom();
    var payload = {
      exported_at: new Date().toISOString(),
      page_url: location.href,
      total_items: state.items.size,
      items: Array.from(state.items.values())
    };

    var blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json;charset=utf-8" });
    var url = URL.createObjectURL(blob);
    var link = document.createElement("a");
    link.href = url;
    link.download = "douyin-favorites-" + new Date().toISOString().replace(/[:.]/g, "-") + ".json";
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setStatus("已导出 " + state.items.size + " 条");
  }

  function setStatus(message) {
    state.statusText = message;
    render();
  }

  function ensurePanel() {
    if (ui.host || !document.body) return;

    var host = document.createElement("div");
    host.id = HOST_ID;
    host.style.position = "fixed";
    host.style.right = "16px";
    host.style.bottom = "16px";
    host.style.zIndex = "2147483647";

    var root = host.attachShadow({ mode: "open" });
    root.innerHTML =
      '<style>' +
      '#panel{width:300px;background:#fff;border:1px solid rgba(0,0,0,.14);border-radius:12px;box-shadow:0 16px 36px rgba(0,0,0,.16);font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;color:#161823;padding:14px;}' +
      '.header{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:10px;}' +
      '.title{font-size:15px;font-weight:700;}' +
      '.collapse-toggle{width:28px;height:28px;padding:0;border-radius:7px;background:#f1f1f2;color:#161823;line-height:1;}' +
      '#panel.collapsed{width:40px;padding:0;}' +
      '#panel.collapsed .title,#panel.collapsed .panel-body{display:none;}' +
      '#panel.collapsed .header{margin:0;}' +
      '#panel.collapsed .collapse-toggle{width:40px;height:40px;}' +
      '.count{font-size:26px;font-weight:750;margin-bottom:8px;}' +
      '.status{font-size:12px;line-height:1.5;background:#f6f6f6;border-radius:8px;padding:9px;margin-bottom:10px;}' +
      '.buttons{display:grid;grid-template-columns:1fr 1fr;gap:8px;}' +
      'button{border:0;border-radius:8px;padding:9px 10px;font-size:13px;font-weight:650;cursor:pointer;}' +
      'button:disabled{opacity:.5;cursor:not-allowed;}' +
      '.primary{background:#fe2c55;color:#fff;}' +
      '.dark{background:#161823;color:#fff;}' +
      '.ghost{background:#f1f1f2;color:#161823;}' +
      '.warn{background:#fff1f1;color:#b40022;grid-column:1 / -1;}' +
      '.hint{font-size:11px;line-height:1.45;color:#666;margin-top:10px;}' +
      '</style>' +
      '<div id="panel">' +
      '<div class="header">' +
      '<div class="title">抖音收藏导出器</div>' +
      '<button class="collapse-toggle" data-action="collapse" type="button" title="收起面板" aria-label="收起面板" aria-expanded="true">-</button>' +
      '</div>' +
      '<div class="panel-body">' +
      '<div class="count" data-role="count">0</div>' +
      '<div class="status" data-role="status">等待采集</div>' +
      '<div class="buttons">' +
      '<button class="primary" data-action="start">开始采集</button>' +
      '<button class="dark" data-action="stop">停止</button>' +
      '<button class="ghost" data-action="scan">补扫当前页</button>' +
      '<button class="ghost" data-action="export">导出 JSON</button>' +
      '<button class="warn" data-action="reset">清空本次结果</button>' +
      '</div>' +
      '<div class="hint">打开抖音个人页的收藏 Tab 后点击开始采集。第一版只读取网页已渲染的视频卡片。</div>' +
      '</div>' +
      '</div>';

    ui.host = host;
    ui.panel = root.querySelector("#panel");
    ui.count = root.querySelector('[data-role="count"]');
    ui.status = root.querySelector('[data-role="status"]');
    ui.start = root.querySelector('[data-action="start"]');
    ui.stop = root.querySelector('[data-action="stop"]');
    ui.scan = root.querySelector('[data-action="scan"]');
    ui.export = root.querySelector('[data-action="export"]');
    ui.reset = root.querySelector('[data-action="reset"]');
    ui.collapse = root.querySelector('[data-action="collapse"]');

    ui.start.addEventListener("click", startCollection);
    ui.stop.addEventListener("click", function () { stopCollection(); });
    ui.scan.addEventListener("click", function () {
      var added = scanDom();
      setStatus("补扫完成，新增 " + added + " 条");
    });
    ui.export.addEventListener("click", exportResults);
    ui.reset.addEventListener("click", resetResults);
    ui.collapse.addEventListener("click", togglePanel);

    document.body.appendChild(host);
    render();
  }

  function togglePanel() {
    var collapsed = ui.panel.classList.toggle("collapsed");
    var label = collapsed ? "展开面板" : "收起面板";
    ui.collapse.textContent = collapsed ? "+" : "-";
    ui.collapse.title = label;
    ui.collapse.setAttribute("aria-label", label);
    ui.collapse.setAttribute("aria-expanded", String(!collapsed));
  }

  function render() {
    if (!ui.host) return;
    ui.count.textContent = String(state.items.size);
    ui.status.textContent = state.statusText;
    ui.start.disabled = state.running;
    ui.stop.disabled = !state.running;
    ui.export.disabled = state.items.size === 0;
  }

  function boot() {
    ensurePanel();
    scanDom();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
})();
