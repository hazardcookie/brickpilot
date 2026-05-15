#!/usr/bin/env python3
"""Lightweight local storage for Brickpilot bookmark reason tags."""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
  from openpilot.common.params import Params


class _PathsProxy:
  @staticmethod
  def log_root() -> str:
    from openpilot.system.hardware.hw import Paths
    return Paths.log_root()


Paths = _PathsProxy

PHEV_CONTEXT_TAGS = ("ev", "hev", "engine", "regen", "stop_creep", "too_lazy", "too_eager", "mads_lfa", "steering_jerk")
VALID_BOOKMARK_REASONS = ("acceleration", "braking", "steering", "phev_context")
BOOKMARK_TAG_SCHEMA_VERSION = 1
BOOKMARK_TAGS_PATH_ENV = "BRICKPILOT_BOOKMARK_TAGS_PATH"


def _log_exception(message: str) -> None:
  try:
    from openpilot.common.swaglog import cloudlog

    cloudlog.exception(message)
  except Exception:
    pass


def _decode_param(value: bytes | str | None) -> str | None:
  if value is None:
    return None
  if isinstance(value, bytes):
    return value.decode("utf-8", errors="replace")
  return value


def bookmark_tags_path() -> Path:
  override = os.environ.get(BOOKMARK_TAGS_PATH_ENV)
  if override:
    return Path(override)

  # Keep tags out of realdata so they are not treated as route artifacts, but
  # close enough to logs for simple adb/scp collection from comma disk.
  return Path(Paths.log_root()).parent / "brickpilot" / "bookmark_tags.jsonl"


def _parse_segment_num(segment_name: str, route: str) -> int | None:
  prefix = f"{route}--"
  if not segment_name.startswith(prefix):
    return None
  try:
    return int(segment_name[len(prefix):])
  except ValueError:
    return None


def current_route_and_segment(params: Params | None = None) -> tuple[str | None, int | None, str | None]:
  """Return (route, latest_segment_num, latest_segment_name) when locally visible."""
  if params is None:
    from openpilot.common.params import Params

    params = Params()
  route = _decode_param(params.get("CurrentRoute"))
  if not route:
    return None, None, None

  latest_segment: int | None = None
  latest_segment_name: str | None = None
  try:
    log_root = Path(Paths.log_root())
    if log_root.is_dir():
      for entry in log_root.iterdir():
        if not entry.is_dir():
          continue
        segment_num = _parse_segment_num(entry.name, route)
        if segment_num is not None and (latest_segment is None or segment_num > latest_segment):
          latest_segment = segment_num
          latest_segment_name = entry.name
  except Exception:
    _log_exception("failed to resolve current bookmark segment")

  return route, latest_segment, latest_segment_name


def build_bookmark_tag_record(reason: str,
                              bookmark_log_mono_time: int | None = None,
                              source: str = "bookmarkButton",
                              tags: list[str] | tuple[str, ...] | None = None) -> dict[str, Any]:
  if reason not in VALID_BOOKMARK_REASONS:
    raise ValueError(f"invalid bookmark reason: {reason}")

  wall_time_unix_ns = time.time_ns()
  route, segment, segment_name = current_route_and_segment()
  record = {
    "schema_version": BOOKMARK_TAG_SCHEMA_VERSION,
    "wall_time": datetime.fromtimestamp(wall_time_unix_ns / 1e9, timezone.utc).isoformat(),
    "wall_time_unix_ns": wall_time_unix_ns,
    "tag_log_mono_time": time.monotonic_ns(),
    "bookmark_button_log_mono_time": bookmark_log_mono_time,
    "source": source,
    "reason": reason,
    "route": route,
    "segment": segment,
    "segment_name": segment_name,
  }
  if tags is not None:
    record["tags"] = list(tags)
  return record


def append_bookmark_tag(reason: str,
                        bookmark_log_mono_time: int | None = None,
                        source: str = "bookmarkButton",
                        tags: list[str] | tuple[str, ...] | None = None) -> bool:
  """Append one JSONL bookmark tag record. Returns False on write failure."""
  try:
    if reason == "phev_context" and tags is None:
      tags = PHEV_CONTEXT_TAGS
    record = build_bookmark_tag_record(reason, bookmark_log_mono_time, source, tags)
    line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
    path = bookmark_tags_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # O_APPEND keeps each tiny write atomic without fsyncing in the UI thread.
    with path.open("a", encoding="utf-8") as f:
      f.write(line)
    return True
  except Exception:
    _log_exception("failed to append Brickpilot bookmark tag")
    return False
