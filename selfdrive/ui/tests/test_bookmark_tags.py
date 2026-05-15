import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpilot.selfdrive.ui.feedback import bookmark_tags


class TestBookmarkTags(unittest.TestCase):
  def test_append_bookmark_tag_jsonl(self):
    with tempfile.TemporaryDirectory() as td:
      out = Path(td) / "bookmark_tags.jsonl"
      with patch.dict("os.environ", {bookmark_tags.BOOKMARK_TAGS_PATH_ENV: str(out)}), \
           patch.object(bookmark_tags, "current_route_and_segment", return_value=("route-id", 7, "route-id--7")):
        self.assertTrue(bookmark_tags.append_bookmark_tag("braking", 123456789))

      records = [json.loads(line) for line in out.read_text().splitlines()]
      self.assertEqual(len(records), 1)
      record = records[0]
      self.assertEqual(record["schema_version"], 1)
      self.assertEqual(record["reason"], "braking")
      self.assertEqual(record["source"], "bookmarkButton")
      self.assertEqual(record["bookmark_button_log_mono_time"], 123456789)
      self.assertEqual(record["route"], "route-id")
      self.assertEqual(record["segment"], 7)
      self.assertEqual(record["segment_name"], "route-id--7")
      self.assertIsInstance(record["tag_log_mono_time"], int)
      self.assertIsInstance(record["wall_time_unix_ns"], int)

  def test_invalid_bookmark_reason_is_rejected(self):
    with tempfile.TemporaryDirectory() as td:
      out = Path(td) / "bookmark_tags.jsonl"
      with patch.dict("os.environ", {bookmark_tags.BOOKMARK_TAGS_PATH_ENV: str(out)}):
        with self.assertRaises(ValueError):
          bookmark_tags.build_bookmark_tag_record("lane_change")
      self.assertFalse(out.exists())

  def test_phev_context_bookmark_includes_taxonomy_tags(self):
    with tempfile.TemporaryDirectory() as td:
      out = Path(td) / "bookmark_tags.jsonl"
      with patch.dict("os.environ", {bookmark_tags.BOOKMARK_TAGS_PATH_ENV: str(out)}), \
           patch.object(bookmark_tags, "current_route_and_segment", return_value=("route-id", 3, "route-id--3")):
        self.assertTrue(bookmark_tags.append_bookmark_tag("phev_context", 987654321))

      record = json.loads(out.read_text().splitlines()[0])
      self.assertEqual(record["reason"], "phev_context")
      self.assertEqual(record["tags"], list(bookmark_tags.PHEV_CONTEXT_TAGS))

  def test_current_route_and_segment_finds_latest(self):
    with tempfile.TemporaryDirectory() as td:
      log_root = Path(td) / "realdata"
      log_root.mkdir()
      (log_root / "abc--1").mkdir()
      (log_root / "abc--12").mkdir()
      (log_root / "abc--not-a-segment").mkdir()
      (log_root / "other--99").mkdir()

      class FakeParams:
        def get(self, key):
          assert key == "CurrentRoute"
          return b"abc"

      with patch.object(bookmark_tags.Paths, "log_root", return_value=str(log_root)):
        self.assertEqual(bookmark_tags.current_route_and_segment(FakeParams()), ("abc", 12, "abc--12"))


if __name__ == "__main__":
  unittest.main()
