import argparse
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from xhs_to_obsidian import summarize_content


MIN_CONTENT_LENGTH = 40
SUMMARY_SOURCE = "> 来源：页面文字，未分析图片、视频画面或语音。"
SUMMARY_PLACEHOLDERS = (
    "待补充。",
    "仅获取到页面标题，暂无可用正文描述。",
)
REJECT_MARKERS = (
    "页面不存在",
    "笔记不存在",
    "安全验证",
    "访问频繁",
)


def existing_note_ids(vault_path):
    return set(existing_note_paths(vault_path))


def existing_note_paths(vault_path):
    root = Path(vault_path) / "平台收藏" / "小红书"
    note_paths = {}
    if not root.exists():
        return note_paths

    for path in root.rglob("*.md"):
        text = path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'^note_id:\s+"?([^"\n]+)"?', text, re.MULTILINE)
        if match:
            note_paths[match.group(1)] = path
    return note_paths


def usable_content(text, title=""):
    content = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(content) < MIN_CONTENT_LENGTH:
        return ""
    if any(marker in content for marker in REJECT_MARKERS):
        return ""
    if title and content == re.sub(r"\s+", " ", str(title)).strip():
        return ""
    return content


def fetch_with_scrapling(url, scrapling_bin):
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
        output_path = Path(handle.name)
    try:
        result = subprocess.run(
            [
                scrapling_bin,
                "extract",
                "get",
                url,
                str(output_path),
                "--timeout",
                "30",
                "--ai-targeted",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=45,
        )
        if result.returncode != 0 or not output_path.exists():
            return ""
        return output_path.read_text(encoding="utf-8", errors="replace")
    finally:
        output_path.unlink(missing_ok=True)


def enrich_payload(payload, existing_ids, fetcher, include_existing=False, limit=0):
    stats = {"eligible": 0, "enriched": 0, "failed": 0, "skipped_existing": 0}

    for item in payload.get("items", []):
        note_id = str(item.get("note_id") or "").strip()
        if not note_id or item.get("content_text"):
            continue
        if note_id in existing_ids and not include_existing:
            stats["skipped_existing"] += 1
            continue
        if limit and stats["eligible"] >= limit:
            break

        url = str(item.get("url") or "").strip()
        if not url.startswith("https://www.xiaohongshu.com/"):
            continue

        stats["eligible"] += 1
        content = usable_content(fetcher(url), item.get("title"))
        if content:
            item["content_text"] = content
            stats["enriched"] += 1
        else:
            stats["failed"] += 1

    return stats


def write_json_atomic(path, payload):
    path = Path(path)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def backfill_summaries(payload, vault_path, limit=0):
    note_paths = existing_note_paths(vault_path)
    updated = 0
    placeholder_pattern = "|".join(re.escape(value) for value in SUMMARY_PLACEHOLDERS)
    block_pattern = rf"(## 摘要\n)(?:{placeholder_pattern})(?:\n\n> 来源：[^\n]+)?"

    for item in payload.get("items", []):
        if limit and updated >= limit:
            break
        note_id = str(item.get("note_id") or "").strip()
        path = note_paths.get(note_id)
        if not path or not item.get("content_text"):
            continue

        summary = summarize_content(item, item.get("title"))
        if summary in SUMMARY_PLACEHOLDERS:
            continue

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


def main():
    parser = argparse.ArgumentParser(description="Enrich new Xiaohongshu exports with public page text.")
    parser.add_argument("json_path")
    parser.add_argument("vault_path")
    parser.add_argument("--include-existing", action="store_true")
    parser.add_argument("--backfill", action="store_true")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--scrapling-bin", default=shutil.which("scrapling") or "")
    args = parser.parse_args()

    if not args.scrapling_bin or not Path(args.scrapling_bin).exists():
        raise SystemExit("scrapling executable not found")

    json_path = Path(args.json_path)
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    stats = enrich_payload(
        payload,
        existing_note_ids(args.vault_path),
        lambda url: fetch_with_scrapling(url, args.scrapling_bin),
        include_existing=args.include_existing,
        limit=max(0, args.limit),
    )
    stats["backfilled"] = (
        backfill_summaries(payload, args.vault_path, limit=max(0, args.limit))
        if args.backfill
        else 0
    )
    write_json_atomic(json_path, payload)
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
