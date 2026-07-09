import json
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pathlib import Path


CATEGORY_RULES = [
    ("职场求职", ("boss", "找工作", "求职", "简历", "offer", "面试", "上班", "毕业", "职场", "副业", "创业", "工作")),
    ("AI工具", ("ai", "chatgpt", "prompt", "提示词", "skill", "插件", "开源", "神器", "工具", "软件", "app", "mac", "apple", "邮箱", "域名", "网站", "github", "知识库", "语音输入", "文件传输")),
    ("信息安全", ("zoomeye", "黑客", "搜索引擎", "网络空间测绘")),
    ("科技数码", ("cat5e", "10gbps", "mlcc", "内存", "网线", "小米", "净化器", "滤芯", "手机", "电脑", "数码", "鼠标", "办公", "windows", "iptv", "checker", "苹果")),
    ("财经商业", ("花呗", "支付宝", "征信", "银行", "价格", "企业", "抽贷", "中小微", "割韭菜", "行业", "贷款", "彩票")),
    ("健康护肤", ("黑头", "新毒株", "病毒", "健康", "皮肤", "护肤", "美妆", "化妆", "底妆", "妆前", "妆后", "身材", "掏耳朵", "耳朵")),
    ("家居生活", ("桌面", "茶几", "家居", "装修", "收纳", "日常", "复刻", "diy", "铝型材", "鱼缸", "水草缸", "小缸", "马桶", "尿垢", "家务", "过滤桶", "铁锅")),
    ("美食", ("做法", "菜谱", "空气炸锅", "鸡翅", "辣椒", "下饭", "厨房", "美式", "吃", "牛肉汤", "酱油鸡", "焗鸡", "萝卜", "生肉", "食记", "低卡")),
    ("旅行户外", ("旅行", "旅游", "东京", "大阪", "京都", "酒店", "路线", "攻略", "山洞", "探险", "远方")),
    ("影视娱乐", ("韩剧", "万茜", "文章", "pp", "好帅", "大女主", "爽", "歌")),
    ("小说写作", ("小说", "精修", "写作", "修魔", "海麻子", "虚无", "陷落")),
    ("社会新闻", ("台风", "广西", "被骗", "公之于众", "评论区", "致歉")),
    ("情感成长", ("男生", "女生", "男人", "女人", "上坡路", "关系", "性张力", "大笑")),
    ("购物好物", ("好物", "购物", "平替", "测评", "开箱", "清单", "配饰")),
]


def category_for(title, author=""):
    haystack = f"{title or ''} {author or ''}".lower()
    # ponytail: keyword buckets beat an LLM dependency for first-pass cleanup; add AI only after this ceiling hurts.
    for category, keywords in CATEGORY_RULES:
        if any(keyword.lower() in haystack for keyword in keywords):
            return category
    return "待分类"


def safe_filename(text):
    text = re.sub(r'[\\/:*?"<>|#\[\]\n\r\t]+', "-", text or "未命名")
    text = re.sub(r"\s+", " ", text).strip(" .-")
    return (text or "未命名")[:80]


def clean_title(raw_title, note_id):
    title = re.sub(r"\s+", " ", str(raw_title or "")).strip()
    if not title or re.fullmatch(r"[0-9a-fA-F]{16,32}", title):
        return f"无标题-{note_id}"
    return title


def yaml_string(value):
    return json.dumps(str(value or ""), ensure_ascii=False)


def wiki_alias(text):
    return str(text or "").replace("[", " ").replace("]", " ").replace("|", "-")


def item_url(item, note_id):
    url = item.get("url") or f"https://www.xiaohongshu.com/explore/{note_id}"
    token = item.get("xsec_token")
    if not token or "xsec_token=" in url:
        return url
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    query.append(("xsec_token", token))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def existing_notes(xhs_root):
    notes = {}
    if not xhs_root.exists():
        return notes

    for path in xhs_root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        note_id_match = re.search(r'^note_id:\s+"?([^"\n]+)"?', text, re.MULTILINE)
        title_match = re.search(r"^#\s+(\d{3})\.\s+(.+)$", text, re.MULTILINE)
        category_match = re.search(r'^category:\s+"?([^"\n]+)"?', text, re.MULTILINE)
        if not note_id_match or not title_match:
            continue
        notes[note_id_match.group(1)] = {
            "path": path,
            "number": title_match.group(1),
            "title": title_match.group(2),
            "category": category_match.group(1) if category_match else path.parent.name,
        }
    return notes


def note_body(number, title, category, created, note_id, item):
    url = item_url(item, note_id)
    cover = item.get("cover")
    cover_line = f"[打开封面]({cover})" if cover else "无"
    return f"""---
id: XHS-{number}
source: xiaohongshu
category: {yaml_string(category)}
status: 待判断
created: {yaml_string(created)}
note_id: {yaml_string(note_id)}
original_url: {yaml_string(url)}
---

# {number}. {title}

## 摘要
待补充。

## 信息
- 作者：{item.get("author") or "未知"}
- 类型：{item.get("note_type") or "未知"}
- 点赞：{item.get("liked_count") or "未知"}
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
    text = re.sub(r"^id:\s+XHS-\d{3}", f"id: XHS-{number}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^category:\s+.*$", f"category: {yaml_string(category)}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^original_url:\s+.*$", f"original_url: {yaml_string(url)}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"^#\s+\d{3}\.\s+.*$", f"# {number}. {title}", text, count=1, flags=re.MULTILINE)
    text = re.sub(r"\[打开原收藏\]\([^)]+\)", f"[打开原收藏]({url})", text, count=1)
    path.write_text(text, encoding="utf-8")


def prune_empty_dirs(root):
    if not root.exists():
        return
    for path in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda p: len(p.parts), reverse=True):
        try:
            path.rmdir()
        except OSError:
            pass


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


def export_records(payload, skip_uncategorized):
    seen = set()
    records = []
    for item in payload.get("items", []):
        note_id = str(item.get("note_id") or "").strip()
        if not note_id or note_id in seen:
            continue
        seen.add(note_id)
        title = clean_title(item.get("title"), note_id)
        category = category_for(title, item.get("author"))
        if skip_uncategorized and category == "待分类":
            continue
        records.append({"note_id": note_id, "title": title, "category": category, "item": item})
    return records


def convert_export(input_path, output_dir, skip_uncategorized=False, sync_current=False):
    payload = json.loads(Path(input_path).read_text(encoding="utf-8"))
    root = Path(output_dir) / "平台收藏"
    xhs_root = root / "小红书"
    existing = existing_notes(xhs_root)
    written = []
    grouped = {}
    created = str(payload.get("exported_at") or "")[:10] or "unknown-date"
    records = export_records(payload, skip_uncategorized)

    if sync_current:
        desired_ids = {record["note_id"] for record in records}
        for note_id, note in existing.items():
            if note_id not in desired_ids:
                note["path"].unlink()
        existing = existing_notes(xhs_root)
        for note_id, note in existing.items():
            tmp_path = note["path"].with_name(f".xhs-sync-{note_id}.md")
            note["path"].rename(tmp_path)
            note["path"] = tmp_path
        sequence = 0
        records = ordered_records(records)
    else:
        sequence = max((int(note["number"]) for note in existing.values()), default=0)

    for record in records:
        note_id = record["note_id"]
        title = record["title"]
        category = record["category"]
        item = record["item"]
        if note_id in existing:
            note = existing[note_id]
            if sync_current:
                sequence += 1
                number = f"{sequence:03d}"
                note_dir = xhs_root / category
                note_dir.mkdir(parents=True, exist_ok=True)
                note_path = note_dir / f"{number} - {safe_filename(title)}.md"
                note["path"].rename(note_path)
                update_existing_body(note_path, number, title, category, item_url(item, note_id))
                note = {"path": note_path, "number": number, "title": title, "category": category}
            rel = note["path"].relative_to(root)
            link_target = rel.with_suffix("").as_posix()
            grouped.setdefault(note["category"], []).append(
                f'{note["number"]}. [[{link_target}|{note["number"]}. {wiki_alias(note["title"])}]] · [原链接]({item_url(item, note_id)})'
            )
            continue

        sequence += 1
        number = f"{sequence:03d}"
        note_dir = xhs_root / category
        note_dir.mkdir(parents=True, exist_ok=True)
        note_path = note_dir / f"{number} - {safe_filename(title)}.md"
        url = item_url(item, note_id)
        note_path.write_text(note_body(number, title, category, created, note_id, item), encoding="utf-8")
        written.append(note_path)
        rel = note_path.relative_to(root)
        link_target = rel.with_suffix("").as_posix()
        grouped.setdefault(category, []).append(
            f'{number}. [[{link_target}|{number}. {wiki_alias(title)}]] · [原链接]({url})'
        )

    root.mkdir(parents=True, exist_ok=True)
    index_lines = ["# 小红书收藏整理", "", f"来源：{Path(input_path).name}", f"导入日期：{created}", ""]
    for category, _keywords in CATEGORY_RULES:
        if category in grouped:
            index_lines.extend([f"## {category}", "", *grouped.pop(category), ""])
    if grouped:
        for category in sorted(grouped):
            index_lines.extend([f"## {category}", "", *grouped[category], ""])
    (root / "小红书收藏整理.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    prune_empty_dirs(xhs_root)
    return written


if __name__ == "__main__":
    skip_uncategorized = "--skip-uncategorized" in sys.argv
    sync_current = "--sync-current" in sys.argv
    args = [arg for arg in sys.argv[1:] if arg not in ("--skip-uncategorized", "--sync-current")]
    if len(args) != 2:
        raise SystemExit("usage: python xhs_to_obsidian.py [--skip-uncategorized] [--sync-current] xhs-favorites.json /path/to/obsidian-vault")
    for path in convert_export(args[0], args[1], skip_uncategorized=skip_uncategorized, sync_current=sync_current):
        print(path)
