import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import douyin_to_obsidian
import enrich_xhs_with_scrapling
import xhs_to_obsidian


class ContentOverviewTests(unittest.TestCase):
    def test_scrapling_enrichment_only_fetches_new_ids_by_default(self):
        payload = {
            "items": [
                {"note_id": "existing", "title": "旧收藏", "url": "https://www.xiaohongshu.com/explore/existing"},
                {"note_id": "new", "title": "新收藏", "url": "https://www.xiaohongshu.com/explore/new"},
            ]
        }
        fetched = []

        def fake_fetch(url):
            fetched.append(url)
            return "这是一段从公开详情页读取的正文。它足够长，可以用于生成本地内容概览，而且没有使用账号凭据。"

        stats = enrich_xhs_with_scrapling.enrich_payload(payload, {"existing"}, fake_fetch)

        self.assertEqual(stats["enriched"], 1)
        self.assertEqual(len(fetched), 1)
        self.assertNotIn("content_text", payload["items"][0])
        self.assertIn("content_text", payload["items"][1])

    def test_backfill_only_replaces_generated_placeholders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir) / "vault"
            note_root = vault / "平台收藏" / "小红书" / "AI工具"
            note_root.mkdir(parents=True)
            pending = note_root / "001 - 待补充.md"
            manual = note_root / "002 - 手写.md"
            pending.write_text(
                '---\nnote_id: "pending"\n---\n\n# 001. 示例\n\n## 摘要\n待补充。\n\n## 信息\n',
                encoding="utf-8",
            )
            manual.write_text(
                '---\nnote_id: "manual"\n---\n\n# 002. 示例\n\n## 摘要\n这是我的手写摘要。\n\n## 信息\n',
                encoding="utf-8",
            )
            payload = {
                "items": [
                    {"note_id": "pending", "title": "示例", "content_text": "第一句正文。第二句正文。"},
                    {"note_id": "manual", "title": "示例", "content_text": "不应覆盖手写内容。"},
                ]
            }

            updated = enrich_xhs_with_scrapling.backfill_summaries(payload, vault)

            self.assertEqual(updated, 1)
            self.assertIn("第一句正文。第二句正文。", pending.read_text(encoding="utf-8"))
            self.assertIn("这是我的手写摘要。", manual.read_text(encoding="utf-8"))

    def test_xhs_summary_uses_two_sentences_and_removes_noise(self):
        item = {
            "content_text": "照片整理技巧：先建立智能相册。再按日期筛选重复照片！第三句不应出现。#效率工具# https://example.com/x"
        }

        summary = xhs_to_obsidian.summarize_content(item, "照片整理技巧")

        self.assertEqual(summary, "先建立智能相册。再按日期筛选重复照片！")

    def test_douyin_summary_is_honest_when_only_title_is_available(self):
        item = {"content_text": "三分钟学会家常菜"}

        summary = douyin_to_obsidian.summarize_content(item, "三分钟学会家常菜")

        self.assertEqual(summary, "仅获取到页面标题，暂无可用正文描述。")

    def test_new_notes_get_overviews_and_duplicate_ids_are_not_recreated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload_path = temp / "xhs.json"
            vault = temp / "vault"
            payload = {
                "exported_at": "2026-07-30T10:00:00Z",
                "items": [
                    {
                        "note_id": "note-1",
                        "title": "照片整理技巧",
                        "content_text": "照片整理技巧：先建立智能相册。再按日期筛选重复照片！",
                    },
                    {
                        "note_id": "note-1",
                        "title": "重复项",
                        "content_text": "这条重复记录不应生成第二篇笔记。",
                    },
                    {
                        "note_id": "note-2",
                        "title": "只有标题的收藏",
                    },
                ],
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            first_written = xhs_to_obsidian.convert_export(payload_path, vault)
            second_written = xhs_to_obsidian.convert_export(payload_path, vault)
            notes = list((vault / "平台收藏" / "小红书").rglob("*.md"))

            self.assertEqual(len(first_written), 2)
            self.assertEqual(second_written, [])
            self.assertEqual(len(notes), 2)
            rendered = "\n".join(path.read_text(encoding="utf-8") for path in notes)
            self.assertIn("先建立智能相册。再按日期筛选重复照片！", rendered)
            self.assertIn("仅获取到页面标题，暂无可用正文描述。", rendered)

    def test_sync_keeps_a_handwritten_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload_path = temp / "douyin.json"
            vault = temp / "vault"
            payload = {
                "exported_at": "2026-07-30T10:00:00Z",
                "items": [
                    {
                        "aweme_id": "10001",
                        "title": "家常菜做法",
                        "content_text": "先准备食材。然后小火慢炖。",
                    }
                ],
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            douyin_to_obsidian.convert_export(payload_path, vault, sync_current=True)
            note_path = next((vault / "平台收藏" / "抖音").rglob("*.md"))
            original = note_path.read_text(encoding="utf-8")
            note_path.write_text(
                original.replace("先准备食材。然后小火慢炖。", "这是我的手写摘要。"),
                encoding="utf-8",
            )

            douyin_to_obsidian.convert_export(payload_path, vault, sync_current=True)
            updated_path = next((vault / "平台收藏" / "抖音").rglob("*.md"))
            updated = updated_path.read_text(encoding="utf-8")

            self.assertIn("这是我的手写摘要。", updated)
            self.assertNotIn("先准备食材。然后小火慢炖。", updated)

    def test_douyin_backfill_only_replaces_generated_placeholders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            payload_path = temp / "douyin.json"
            vault = temp / "vault"
            payload = {
                "exported_at": "2026-08-07T10:00:00Z",
                "items": [
                    {
                        "aweme_id": "20001",
                        "title": "家常菜做法",
                        "content_text": "先准备食材。然后小火慢炖。",
                    }
                ],
            }
            payload_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            douyin_to_obsidian.convert_export(payload_path, vault)
            note_path = next((vault / "平台收藏" / "抖音").rglob("*.md"))
            original = note_path.read_text(encoding="utf-8")
            note_path.write_text(
                original.replace("先准备食材。然后小火慢炖。", "待补充。"),
                encoding="utf-8",
            )

            updated = douyin_to_obsidian.backfill_summaries(payload, vault)

            self.assertEqual(updated, 1)
            self.assertIn("先准备食材。然后小火慢炖。", note_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
