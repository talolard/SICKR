"""Scrapy extensions used by the sidecar."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scrapy import signals
from scrapy.crawler import Crawler


class RunStatsExtension:
    """Persist crawler stats as JSON so the CLI can summarize each stage."""

    def __init__(self, stats_path: str | None) -> None:
        self._stats_path = Path(stats_path).expanduser().resolve() if stats_path else None

    @classmethod
    def from_crawler(cls, crawler: Crawler) -> RunStatsExtension:
        extension = cls(crawler.settings.get("RUN_STATS_PATH"))
        crawler.signals.connect(extension.spider_closed, signal=signals.spider_closed)
        return extension

    def spider_closed(self, spider: object) -> None:
        if self._stats_path is None:
            return
        stats = spider.crawler.stats.get_stats()  # type: ignore[attr-defined]
        serializable_stats: dict[str, Any] = {}
        for key, value in stats.items():
            if isinstance(value, (str, int, float, bool)) or value is None:
                serializable_stats[str(key)] = value
            else:
                serializable_stats[str(key)] = str(value)
        self._stats_path.parent.mkdir(parents=True, exist_ok=True)
        self._stats_path.write_text(
            json.dumps(serializable_stats, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
