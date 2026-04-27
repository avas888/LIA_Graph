"""SQLite-backed cache for scraper fetches.

Schema:
  CREATE TABLE scraper_cache (
      cache_id            INTEGER PRIMARY KEY AUTOINCREMENT,
      source              TEXT NOT NULL,           -- 'secretaria_senado' | 'dian_normograma' | ...
      url                 TEXT NOT NULL,
      canonical_norm_id   TEXT,                    -- v3 addition (§0.11.3 contract 3)
      fetched_at_utc      TEXT NOT NULL,           -- ISO8601
      status_code         INTEGER NOT NULL,
      content_sha256      TEXT NOT NULL,
      content             BLOB NOT NULL,
      content_type        TEXT,
      parsed_text         TEXT,                    -- post-parse plaintext (per-scraper)
      parsed_meta         TEXT,                    -- JSON sidecar (modification notes, etc.)
      UNIQUE(source, url)
  );
  CREATE INDEX idx_scraper_cache_source_canonical ON scraper_cache(source, canonical_norm_id);
  CREATE INDEX idx_scraper_cache_canonical        ON scraper_cache(canonical_norm_id);

The v3-additive `canonical_norm_id` column lets 1B-β query the cache by
canonical id directly, removing one free-text join the v2 plan had implicit.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping

LOGGER = logging.getLogger(__name__)


DEFAULT_CACHE_PATH = Path("var/scraper_cache.db")


_SCHEMA = """
CREATE TABLE IF NOT EXISTS scraper_cache (
    cache_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source              TEXT NOT NULL,
    url                 TEXT NOT NULL,
    canonical_norm_id   TEXT,
    fetched_at_utc      TEXT NOT NULL,
    status_code         INTEGER NOT NULL,
    content_sha256      TEXT NOT NULL,
    content             BLOB NOT NULL,
    content_type        TEXT,
    parsed_text         TEXT,
    parsed_meta         TEXT,
    UNIQUE(source, url)
);
CREATE INDEX IF NOT EXISTS idx_scraper_cache_source_canonical
    ON scraper_cache(source, canonical_norm_id);
CREATE INDEX IF NOT EXISTS idx_scraper_cache_canonical
    ON scraper_cache(canonical_norm_id);
"""


@dataclass(frozen=True)
class CacheEntry:
    source: str
    url: str
    canonical_norm_id: str | None
    fetched_at_utc: str
    status_code: int
    content_sha256: str
    content: bytes
    content_type: str | None
    parsed_text: str | None
    parsed_meta: dict[str, Any]


class ScraperCache:
    """Thin wrapper around SQLite. Safe for concurrent readers; serial writers."""

    def __init__(self, path: Path | str = DEFAULT_CACHE_PATH) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.executescript(_SCHEMA)
            conn.commit()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path))
        try:
            conn.row_factory = sqlite3.Row
            yield conn
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get(self, source: str, url: str) -> CacheEntry | None:
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM scraper_cache WHERE source=? AND url=?",
                (source, url),
            )
            row = cur.fetchone()
        return _row_to_entry(row) if row else None

    def get_by_canonical(
        self,
        canonical_norm_id: str,
        *,
        source: str | None = None,
    ) -> list[CacheEntry]:
        with self._connect() as conn:
            if source:
                cur = conn.execute(
                    "SELECT * FROM scraper_cache "
                    "WHERE canonical_norm_id=? AND source=?",
                    (canonical_norm_id, source),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM scraper_cache WHERE canonical_norm_id=?",
                    (canonical_norm_id,),
                )
            return [_row_to_entry(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def put(
        self,
        *,
        source: str,
        url: str,
        content: bytes,
        status_code: int,
        canonical_norm_id: str | None = None,
        content_type: str | None = None,
        parsed_text: str | None = None,
        parsed_meta: Mapping[str, Any] | None = None,
    ) -> None:
        digest = hashlib.sha256(content).hexdigest()
        meta_json = json.dumps(parsed_meta or {}, ensure_ascii=False, sort_keys=True)
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO scraper_cache (
                    source, url, canonical_norm_id, fetched_at_utc,
                    status_code, content_sha256, content, content_type,
                    parsed_text, parsed_meta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, url) DO UPDATE SET
                    canonical_norm_id = excluded.canonical_norm_id,
                    fetched_at_utc    = excluded.fetched_at_utc,
                    status_code       = excluded.status_code,
                    content_sha256    = excluded.content_sha256,
                    content           = excluded.content,
                    content_type      = excluded.content_type,
                    parsed_text       = excluded.parsed_text,
                    parsed_meta       = excluded.parsed_meta
                """,
                (
                    source,
                    url,
                    canonical_norm_id,
                    now,
                    int(status_code),
                    digest,
                    content,
                    content_type,
                    parsed_text,
                    meta_json,
                ),
            )
            conn.commit()

    def attach_canonical_norm_id(self, *, source: str, url: str, canonical_norm_id: str) -> None:
        """Backfill the canonical id on an existing row (v3 migration step)."""

        with self._connect() as conn:
            conn.execute(
                "UPDATE scraper_cache SET canonical_norm_id=? WHERE source=? AND url=?",
                (canonical_norm_id, source, url),
            )
            conn.commit()

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        with self._connect() as conn:
            total = conn.execute("SELECT COUNT(*) FROM scraper_cache").fetchone()[0]
            with_canon = conn.execute(
                "SELECT COUNT(*) FROM scraper_cache WHERE canonical_norm_id IS NOT NULL"
            ).fetchone()[0]
            sources = conn.execute(
                "SELECT source, COUNT(*) FROM scraper_cache GROUP BY source"
            ).fetchall()
        return {
            "total_rows": int(total),
            "rows_with_canonical_id": int(with_canon),
            "by_source": {row[0]: int(row[1]) for row in sources},
        }


def _row_to_entry(row: sqlite3.Row) -> CacheEntry:
    parsed_meta_raw = row["parsed_meta"] or "{}"
    try:
        parsed_meta = json.loads(parsed_meta_raw)
    except json.JSONDecodeError:
        parsed_meta = {}
    return CacheEntry(
        source=row["source"],
        url=row["url"],
        canonical_norm_id=row["canonical_norm_id"],
        fetched_at_utc=row["fetched_at_utc"],
        status_code=int(row["status_code"]),
        content_sha256=row["content_sha256"],
        content=row["content"],
        content_type=row["content_type"],
        parsed_text=row["parsed_text"],
        parsed_meta=parsed_meta,
    )


__all__ = ["CacheEntry", "ScraperCache", "DEFAULT_CACHE_PATH"]
