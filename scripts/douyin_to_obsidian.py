import html
import json
import re
import sys
from pathlib import Path


CATEGORY_RULES = [
    ("AI工具", ("ai", "skill", "github", "工具", "项目", "软件", "插件", "网站", "obs", "ios", "投屏")),
    ("美食", ("做菜", "美食", "鸡腿", "豉油鸡", "凉面", "米饭", "牛肉", "咖啡", "厨房", "食谱", "厨师", "煲汤", "好汤", "老火汤", "蒸鸡", "炒肉", "家常菜", "腌辣椒", "辣椒", "夹馍")),
    ("财经商业", ("商业", "创业", "支付", "收款", "stripe", "上市", "投资", "经营", "房产", "别墅", "豪宅")),
    ("健康养生", ("皮肤科", "常备药", "养生", "脚气", "联苯苄唑", "元气")),
    ("汽车出行", ("电动车", "新国标", "续航", "好车", "二手车")),
    ("运动户外", ("钓鱼", "鱼竿", "户外", "运动")),
    ("影音娱乐", ("音乐", "乐队", "mv", "dj", "mc", "搞笑", "生日祝福", "鲜花", "回春丹", "skrillex")),
    ("旅行户外", ("旅行", "澳洲", "whv", "户外", "攻略", "签证", "洛杉矶", "公务舱", "出行vlog", "哈尔滨", "冰雪大世界")),
    ("家居生活", ("搬家", "家居", "好物", "洗护", "收纳", "生活")),
    ("学习成长", ("学习", "手册", "成长", "申请", "国学", "易经", "人生智慧", "认知", "英语", "中考", "志愿征集")),
    ("社会新闻", ("哈萨克斯坦", "14岁", "小长假", "新闻", "老师点外卖", "历史", "伟人", "正能量")),
    ("服饰穿搭", ("鞋带", "鞋子", "穿搭", "好鞋", "跑步鞋", "女装")),
    ("美妆护肤", ("化妆", "通勤妆", "美妆", "毛戈平")),
    ("情感成长", ("会好", "迟早")),
]

SUMMARY_MAX_LENGTH = 280
SUMMARY_SOURCE = "> 来源：页面文字，未分析视频画面或语音。"
SUMMARY_PLACEHOLDERS = (
    "待补充。",
    "仅获取到页面标题，暂无可用正文描述。",
)


def matches_keyword(haystack, keyword):
    if keyword.isascii() and keyword.isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])", haystack) is not None
    return keyword.lower() in haystack


def category_for(title):
    haystack = str(title or "").lower()
    for category, keywords in CATEGORY_RULES:
        if any(matches_keyword(haystack, keyword) for keyword in keywords):
            return category
    return "待人工确认"


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|#\[\]\n\r\t]+', "-", text or "未命名")
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return (text or "未命名")[:80]


def clean_title(value, aweme_id):
    title = re.sub(r"\s+", " ", str(value or "")).strip()
    return title


def clean_content_text(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"#([^#\s]+)#", r"\1", text)
    text = re.sub(r"(?<!\S)#([^\s#]+)", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def summarize_content(item, title):
    raw = (
        item.get("content_excerpt")
        or item.get("content_text")
        or item.get("description")
        or item.get("desc")
    )
    text = clean_content_text(raw)
    normalized_title = clean_content_text(title)

    if normalized_title and text.startswith(normalized_title):
        text = text[len(normalized_title):].lstrip(" ：:，,-—")

    if not text or text == normalized_title:
        return "仅获取到页面标题，暂无可用正文描述。"

    sentences = [part.strip() for part in re.findall(r"[^。！？!?]+[。！？!?]?", text) if part.strip()]
    summary = "".join(sentences[:2]) or text
    if len(summary) > SUMMARY_MAX_LENGTH:
        summary = summary[:SUMMARY_MAX_LENGTH].rstrip(" ，,。；;") + "..."
    return summary


def yaml_string(value):
    return json.dumps(str(value or ""), ensure_ascii=False)


def existing_notes(douyin_root):
    notes = {}
    if not douyin_root.exists():
        return notes
    for path in douyin_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        id_match = re.search(r'^aweme_id:\s+"?([^"\n]+)"?', text, re.MULTILINE)
        title_match = re.search(r"^#\s+(\d{3})\.\s+(.+)$", text, re.MULTILINE)
        category_match = re.search(r'^category:\s+"?([^"\n]+)"?', text, re.MULTILINE)
        if not id_match or not title_match:
            continue
        notes[id_match.group(1)] = {
            "path": path,
            "number": title_match.group(1),
            "title": title_match.group(2),
            "category": category_match.group(1) if category_match else path.parent.name,
        }
    return notes


def export_records(payload):
    seen = set()
    records = []
    for item in payload.get("items", []):
        aweme_id = str(item.get("aweme_id") or "").strip()
        if not aweme_id or aweme_id in seen:
            continue
        seen.add(aweme_id)
        title = clean_title(item.get("title"), aweme_id)
        if not title or title == "无标题":
            continue
        records.append({
            "aweme_id": aweme_id,
            "title": title,
            "category": category_for(title),
            "item": item,
        })
    return records


def ordered_records(records):
    by_category = {}
    for record in records:
        by_category.setdefault(record["category"], []).append(record)
    ordered = []
    for category, _keywords in CATEGORY_RULES:
        ordered.extend(by_category.pop(category, []))
    for category in sorted(by_category):
        ordered.extend(by_category[category])
    return ordered


def note_body(number, title, category, created, aweme_id, item):
    url = item.get("url") or f"https://www.douyin.com/video/{aweme_id}"
    cover = item.get("cover")
    cover_line = f"[打开封面]({cover})" if cover else "无"
    summary = summarize_content(item, title)
    return f"""---
id: DOUYIN-{number}
source: douyin
category: {yaml_string(category)}
status: 待判断
created: {yaml_string(created)}
aweme_id: {yaml_string(aweme_id)}
original_url: {yaml_string(url)}
---

# {number}. {title}

## 摘要
{summary}

> 来源：页面文字，未分析视频画面或语音。

## 信息
- 作者：{item.get("author") or "未知"}
- 类型：{item.get("note_type") or "video"}
- 封面：{cover_line}

## 清理判断
- [ ] 保留
- [ ] 不需要
- [ ] 已回平台处理

## 原链接
[打开原收藏]({url})
"""


def update_existing_body(path, number, title, category, url):
    text = path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(r"^id:\s+DOUYIN-\d{3}", f"id: DOUYIN-{number}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^category:\s+.*$", f"category: {yaml_string(category)}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^original_url:\s+.*$", f"original_url: {yaml_string(url)}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^#\s+\d{3}\.\s+.*$", f"# {number}. {title}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"\[打开原收藏\]\([^)]+\)", f"[打开原收藏]({url})", text, count=1)
    path.write_text(text, encoding="utf-8")


def backfill_summaries(payload, vault_path):
    douyin_root = Path(vault_path) / "平台收藏" / "抖音"
    existing = existing_notes(douyin_root)
    placeholder_pattern = "|".join(re.escape(value) for value in SUMMARY_PLACEHOLDERS)
    block_pattern = rf"(## 摘要\n)(?:{placeholder_pattern})(?:\n\n> 来源：[^\n]+)?"
    updated = 0

    for record in export_records(payload):
        note = existing.get(record["aweme_id"])
        if not note or not record["item"].get("content_text"):
            continue

        summary = summarize_content(record["item"], record["title"])
        if summary in SUMMARY_PLACEHOLDERS:
            continue

        path = note["path"]
        text = path.read_text(encoding="utf-8", errors="replace")
        replaced, count = re.subn(
            block_pattern,
            lambda match: f"{match.group(1)}{summary}\n\n{SUMMARY_SOURCE}",
            text,
            count=1,
        )
        if count:
            temporary = path.with_name(f".{path.name}.tmp")
            temporary.write_text(replaced, encoding="utf-8")
            temporary.replace(path)
            updated += 1

    return updated


def prune_empty_dirs(root):
    if not root.exists():
        return
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


def add_index_line(grouped, root, note, url):
    rel = note["path"].relative_to(root).with_suffix("").as_posix()
    grouped.setdefault(note["category"], []).append(
        f'{note["number"]}. [[{rel}|{note["number"]}. {note["title"]}]] · [原链接]({url})'
    )


def convert_export(input_path, vault_path, sync_current=False):
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    root = Path(vault_path) / "平台收藏"
    douyin_root = root / "抖音"
    existing = existing_notes(douyin_root)
    grouped = {}
    written = []
    created = str(payload.get("exported_at") or "")[:10] or "unknown-date"
    records = export_records(payload)

    if sync_current:
        desired_ids = {record["aweme_id"] for record in records}
        for aweme_id, note in existing.items():
            if aweme_id not in desired_ids:
                note["path"].unlink()
        existing = existing_notes(douyin_root)
        for aweme_id, note in existing.items():
            tmp_path = note["path"].with_name(f".douyin-sync-{aweme_id}.md")
            note["path"].rename(tmp_path)
            note["path"] = tmp_path
        sequence = 0
        records = ordered_records(records)
    else:
        sequence = max((int(note["number"]) for note in existing.values()), default=0)

    for record in records:
        aweme_id = record["aweme_id"]
        title = record["title"]
        category = record["category"]
        item = record["item"]
        url = item.get("url") or f"https://www.douyin.com/video/{aweme_id}"

        if aweme_id in existing:
            note = existing[aweme_id]
            if sync_current:
                sequence += 1
                number = f"{sequence:03d}"
                note_dir = douyin_root / category
                note_dir.mkdir(parents=True, exist_ok=True)
                note_path = note_dir / f"{number} - {safe_filename(title)}.md"
                note["path"].rename(note_path)
                update_existing_body(note_path, number, title, category, url)
                note = {"path": note_path, "number": number, "title": title, "category": category}
            add_index_line(grouped, root, note, url)
            continue

        sequence += 1
        number = f"{sequence:03d}"
        note_dir = douyin_root / category
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / f"{number} - {safe_filename(title)}.md"
        note_path.write_text(note_body(number, title, category, created, aweme_id, item), encoding="utf-8")
        written.append(note_path)
        add_index_line(grouped, root, {"path": note_path, "number": number, "title": title, "category": category}, url)

    root.mkdir(parents=True, exist_ok=True)
    index_lines = ["# 抖音收藏整理", "", f"来源：{Path(input_path).name}", f"导入日期：{created}", ""]
    for category, _keywords in CATEGORY_RULES:
        if category in grouped:
            index_lines.extend([f"## {category}", "", *grouped.pop(category), ""])
    for category in sorted(grouped):
        index_lines.extend([f"## {category}", "", *grouped[category], ""])
    (root / "抖音收藏整理.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    prune_empty_dirs(douyin_root)
    return written


if __name__ == "__main__":
    sync_current = "--sync-current" in sys.argv
    backfill_only = "--backfill-only" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg not in ("--sync-current", "--backfill-only")]
    if len(args) != 2:
        raise SystemExit("usage: python3 douyin_to_obsidian.py [--sync-current|--backfill-only] douyin-favorites.json /path/to/ObsidianVault")
    if backfill_only:
        payload = json.loads(Path(args[0]).read_text(encoding="utf-8"))
        print(f"backfilled={backfill_summaries(payload, args[1])}")
    else:
        for path in convert_export(args[0], args[1], sync_current=sync_current):
            print(path)
