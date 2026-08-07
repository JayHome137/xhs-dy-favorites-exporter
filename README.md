# 小红书 & 抖音收藏导出器

一个 Chrome 扩展，在真实登录态下把小红书和抖音网页版收藏列表导出为结构化 JSON。另附可选的 Obsidian 导入脚本。

小红书收藏导出部分参考了 [PCPrincipal67/xhs-favorites-exporter](https://github.com/PCPrincipal67/xhs-favorites-exporter) 的实现思路。

不重放私有 API，不保存密码，不下载视频。它只在你已经登录的网页里，把你自己的收藏索引整理出来。

手动导出是主流程；Chrome 自动操作和 Obsidian 导入都是可选步骤。不是 Codex 用户也可以直接忽略自动操作脚本。

一个扩展同时支持小红书和抖音；进入不同网站时，会自动加载对应平台的采集逻辑。

## 它能做什么

- 小红书：读取首屏 SSR 数据，拦截收藏分页 XHR，扫描 DOM 卡片，自动滚动采集。
- 抖音：扫描网页版收藏页已经渲染的视频卡片，自动滚动采集。
- 按平台分别导出 JSON：
  - `xhs-favorites-*.json`
  - `douyin-favorites-*.json`
- 可选导入 Obsidian：
  - `平台收藏/小红书收藏整理.md`
  - `平台收藏/小红书/<分类>/*.md`
  - `平台收藏/抖音收藏整理.md`
  - `平台收藏/抖音/<分类>/*.md`
- Obsidian 新笔记会根据页面已有文字生成最多两句的内容概览；没有正文时会明确标记，不分析图片、视频画面或语音。
- 可选使用 Scrapling 从公开小红书详情页补全正文，只处理尚未导入 Obsidian 的新 `note_id`，不读取 Chrome Cookie。
- 可选 Chrome 自动操作：用脚本打开收藏页、临时展开面板并导出 JSON，完成后恢复原来的收起状态。

## 安装扩展

1. 下载或 clone 本仓库。
2. 打开 Chrome，进入 `chrome://extensions`。
3. 打开「开发者模式」。
4. 点「加载已解压的扩展程序」。
5. 选择本仓库里的 `extension/` 目录。
6. 打开小红书收藏页或抖音收藏页，确认页面右下角出现对应的导出面板。

不要选择仓库根目录，必须选择 `extension/` 目录。

### 更新扩展

更新仓库代码后，在 `chrome://extensions` 页面点击这个扩展的刷新按钮，再刷新小红书或抖音页面即可。

## 操作演示

完整链路如下：

```text
Chrome 登录平台
  -> 加载 extension/
  -> 打开小红书收藏页或抖音收藏页
  -> 自动出现对应平台面板
  -> 开始采集并自动滚动
  -> 导出 JSON 到下载目录
  -> 可选：导入 Obsidian
  -> 去重、按标题归类、更新编号
  -> 导入成功后删除本次 JSON
```

### 手动操作小红书

1. 打开小红书网页版并登录。
2. 进入个人主页的「收藏」Tab。
3. 刷新页面。
4. 确认右下角出现「小红书收藏导出器」。
5. 点击「开始采集」，等待数量稳定或状态显示完成。
6. 点击「导出 JSON」。
7. 在下载目录找到 `xhs-favorites-*.json`。
8. 不使用面板时点击 `-` 收起；新打开的小红书页面会保持收起状态。

### 手动操作抖音

1. 打开抖音网页版并登录。
2. 进入个人页的收藏 Tab，例如 `/user/self?showTab=favorite_collection`。
3. 确认右下角出现「抖音收藏导出器」。
4. 点击「开始采集」，等待数量稳定或状态显示完成。
5. 点击「导出 JSON」。
6. 在下载目录找到 `douyin-favorites-*.json`。
7. 不使用面板时点击 `-` 收起；新打开的抖音页面会保持收起状态。

如果页面没有出现面板，先确认扩展已启用，再刷新当前页面。小红书和抖音页面不需要同时打开。

## 导出字段

小红书：

| 字段 | 说明 |
|------|------|
| `note_id` | 小红书笔记 ID |
| `xsec_token` | 详情页访问 token |
| `url` | 带 token 的完整链接 |
| `title` | 标题 |
| `content_text` | 页面提供的正文或描述；收藏列表没有提供时为空 |
| `author` | 作者昵称 |
| `cover` | 封面图链接 |
| `liked_count` | 点赞数 |
| `note_type` | 笔记类型 |
| `sources` | 数据来源 |

抖音：

| 字段 | 说明 |
|------|------|
| `aweme_id` | 抖音视频 ID |
| `url` | 视频链接 |
| `title` | 标题或描述 |
| `content_text` | 网页卡片提供的描述；没有提供时为空 |
| `author` | 作者昵称 |
| `cover` | 封面图链接 |
| `note_type` | 类型，当前主要是 `video` |
| `source` | 数据来源，当前是 `dom` |

## 可选：导入 Obsidian

导入是独立步骤。只想要 JSON 的用户可以跳过这里。

### 小红书

```bash
python3 scripts/xhs_to_obsidian.py --skip-uncategorized --sync-current \
  ~/Downloads/xhs-favorites-xxxx.json \
  /path/to/ObsidianVault
```

### 抖音

```bash
python3 scripts/douyin_to_obsidian.py --sync-current \
  ~/Downloads/douyin-favorites-xxxx.json \
  /path/to/ObsidianVault
```

参数说明：

| 参数 | 说明 |
|------|------|
| `--sync-current` | 以当前 JSON 为准同步 Obsidian，删除已经不在 JSON 里的旧笔记 |
| `--skip-uncategorized` | 小红书导入时跳过无法归类的条目 |

导入脚本会按 `note_id` / `aweme_id` 去重。已有笔记不会整篇重写，只更新编号、分类、标题和原链接，尽量保留你在 Obsidian 里手写的内容。

导入器会把 `content_text` 清理成最多两句、280 字以内的内容概览。这个过程完全在本机执行，不调用大模型或外部摘要服务。页面没有提供正文时，笔记会显示“仅获取到页面标题，暂无可用正文描述”。

### 可选：用 Scrapling 补全小红书正文

小红书收藏列表通常只有标题。安装 [Scrapling](https://github.com/D4Vinci/Scrapling) 后，可以在导入前读取公开详情页文字：

```bash
scrapling extract --help
python3 scripts/enrich_xhs_with_scrapling.py \
  ~/Downloads/xhs-favorites-xxxx.json \
  /path/to/ObsidianVault
```

补全器只访问 JSON 中已经存在的 `xiaohongshu.com` 原链接，不读取或传递 Chrome Cookie，不访问第三方摘要服务。默认跳过 Vault 中已有的 `note_id`，避免每周重复抓取旧收藏。`scripts/import_xhs_to_obsidian.sh` 检测到本机已安装 Scrapling 时会自动执行这一步；未安装时仍可正常导入，只是没有正文的条目会使用明确的占位说明。

需要一次性补齐旧笔记时，可以显式使用 `--include-existing --backfill`。回填只替换“待补充”或自动占位说明，不重建索引、不改编号和分类，也不覆盖手写摘要。不要把这两个参数加入每周任务。

抖音没有接入 Scrapling。实测其公开详情页经常只返回登录页面，因此抖音概览仅使用 Chrome 页面已经提供的描述，避免把登录凭据交给额外抓取工具。

也可以使用导入辅助脚本。它会自动选择下载目录里最新的对应 JSON，并且只在导入成功后删除本次导入的 JSON。

```bash
scripts/import_xhs_to_obsidian.sh /path/to/ObsidianVault
scripts/import_douyin_to_obsidian.sh /path/to/ObsidianVault
```

如果不想用最新文件，也可以显式指定 JSON：

```bash
scripts/import_xhs_to_obsidian.sh /path/to/ObsidianVault ~/Downloads/xhs-favorites-xxxx.json
scripts/import_douyin_to_obsidian.sh /path/to/ObsidianVault ~/Downloads/douyin-favorites-xxxx.json
```

## 可选：Chrome 自动操作

自动操作只负责代替你点击网页里的扩展面板，不会取消收藏，也不会删除平台上的任何内容。它适合已经登录 Chrome、扩展已安装、收藏页结构没有明显变化的场景。

要求：

- macOS + Google Chrome。
- Chrome 已允许 Apple 事件里的 JavaScript：`View > Developer > Allow JavaScript from Apple Events`。
- 已安装本仓库 `extension/` 扩展。
- 小红书或抖音网页端保持登录。

非 Codex 用户可以直接在终端运行这些脚本；Codex 用户也可以让 Codex 调用同样的脚本。脚本不会包含任何本机私有路径、定时任务或账号信息。

### 自动导出小红书

小红书收藏页 URL 每个人不同，需要传入你自己的收藏页地址：

```bash
scripts/export_xhs_chrome.sh "https://www.xiaohongshu.com/user/profile/...?showTab=liked"
```

也可以用环境变量：

```bash
XHS_FAVORITES_URL="https://www.xiaohongshu.com/user/profile/...?showTab=liked" \
  scripts/export_xhs_chrome.sh
```

### 自动导出抖音

抖音默认打开个人收藏页：

```bash
scripts/export_douyin_chrome.sh
```

如果你的收藏页地址不同，可以显式传入：

```bash
scripts/export_douyin_chrome.sh "https://www.douyin.com/user/self?showTab=favorite_collection"
```

### 自动导出后导入 Obsidian

保持导出和导入分开，便于你先检查 JSON：

```bash
scripts/export_xhs_chrome.sh "https://www.xiaohongshu.com/user/profile/...?showTab=liked"
scripts/import_xhs_to_obsidian.sh /path/to/ObsidianVault

scripts/export_douyin_chrome.sh
scripts/import_douyin_to_obsidian.sh /path/to/ObsidianVault
```

需要每周自动跑时，可以用你自己的 `launchd`、`cron`、Raycast、Keyboard Maestro 或其他调度器调用上面的命令。本仓库不内置个人化定时配置。

## 导出格式示例

小红书：

```json
{
  "exported_at": "2026-07-09T12:00:00.000Z",
  "page_url": "https://www.xiaohongshu.com/user/profile/...",
  "total_items": 87,
  "items": [
    {
      "note_id": "6805d5dc000000001c0328ce",
      "xsec_token": "ABCD1234",
      "url": "https://www.xiaohongshu.com/explore/6805d5dc000000001c0328ce?xsec_token=ABCD1234",
      "title": "示例标题",
      "content_text": "示例正文描述。",
      "author": "示例作者",
      "cover": "https://...",
      "liked_count": "12",
      "note_type": "normal",
      "sources": ["ssr", "xhr"]
    }
  ]
}
```

抖音：

```json
{
  "exported_at": "2026-07-09T12:00:00.000Z",
  "page_url": "https://www.douyin.com/user/self?showTab=favorite_collection",
  "total_items": 52,
  "items": [
    {
      "aweme_id": "7659364533756038436",
      "title": "示例视频标题",
      "content_text": "示例视频描述。",
      "author": "示例作者",
      "url": "https://www.douyin.com/video/7659364533756038436",
      "cover": "https://...",
      "note_type": "video",
      "source": "dom"
    }
  ]
}
```

## 技术原理

```
┌─────────────────────────────────────────────┐
│ 小红书                                       │
│ page-bridge.js 读 SSR + 拦截 XHR             │
│ xhs-content-script.js 扫 DOM + 自动滚动 + 导出 │
├─────────────────────────────────────────────┤
│ 抖音                                         │
│ douyin-content-script.js 扫 DOM 视频卡片      │
│ 自动滚动 + 去重 + 导出 JSON                  │
├─────────────────────────────────────────────┤
│ Obsidian                                     │
│ Scrapling 可选补全小红书正文                  │
│ scripts/*.py 生成概览并导入 Markdown          │
└─────────────────────────────────────────────┘
```

关键取舍：

- 小红书详情链接依赖 `xsec_token`，导出时会尽量保存完整链接。
- 小红书 API 有签名和风控，扩展不复现签名，只读取页面自己拿到的数据。
- 抖音接口有 `msToken` / `a_bogus` 等参数，扩展不逆向接口，只读取网页已渲染卡片。
- Obsidian 导入是可选脚本，不绑定扩展。

## 已知限制

- 扩展只导出收藏列表提供的文字；可选 Scrapling 只补全公开小红书详情页正文，不抓评论、全部图片或视频文件。
- 抖音只读取网页端已渲染的视频卡片；网页没显示的条目不会凭空出现。
- 小红书少数 DOM 补扫条目可能缺少 `xsec_token`。
- 需要你在 Chrome 中保持对应平台的登录状态。
- 不支持自动取消收藏。
- 自动操作依赖网页结构和扩展面板按钮，平台改版后可能需要调整选择器。
- 仓库不内置个人化定时任务；需要自动化时可自行用调度器调用脚本。

## 文件说明

| 文件 | 说明 |
|------|------|
| `extension/manifest.json` | Chrome Manifest V3 配置 |
| `extension/xhs-content-script.js` | 小红书控制面板、滚动、导出 |
| `extension/page-bridge.js` | 小红书页面上下文桥接脚本 |
| `extension/douyin-content-script.js` | 抖音控制面板、DOM 扫描、导出 |
| `scripts/xhs_to_obsidian.py` | 小红书 JSON 导入 Obsidian |
| `scripts/douyin_to_obsidian.py` | 抖音 JSON 导入 Obsidian |
| `scripts/enrich_xhs_with_scrapling.py` | 可选：只为新增小红书收藏补全公开详情页文字 |
| `scripts/export_xhs_chrome.sh` | 可选：自动打开小红书收藏页并触发导出 |
| `scripts/export_douyin_chrome.sh` | 可选：自动打开抖音收藏页并触发导出 |
| `scripts/import_xhs_to_obsidian.sh` | 可选：导入最新小红书 JSON，成功后删除该 JSON |
| `scripts/import_douyin_to_obsidian.sh` | 可选：导入最新抖音 JSON，成功后删除该 JSON |

## License

MIT
