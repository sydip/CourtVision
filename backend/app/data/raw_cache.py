from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeAlias, cast

JsonPayload: TypeAlias = dict[str, Any] | list[Any]


class RawResponseCache:
    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)

    def save(
        self,
        season: str,
        endpoint: str,
        payload: JsonPayload,
        *,
        query_parameters: dict[str, object] | None = None,
        source: str = "nba_api",
    ) -> Path:
        endpoint_dir = self._endpoint_dir(season, endpoint)
        endpoint_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        cache_path = endpoint_dir / f"{timestamp}.json"
        suffix = 1
        while cache_path.exists():
            cache_path = endpoint_dir / f"{timestamp}-{suffix}.json"
            suffix += 1
        envelope = {
            "endpoint": endpoint,
            "source": source,
            "season": season,
            "fetched_at": datetime.now(UTC).isoformat(),
            "query_parameters": query_parameters or {},
            "raw_payload": payload,
        }
        cache_path.write_text(json.dumps(envelope, indent=2, sort_keys=True), encoding="utf-8")
        return cache_path

    def load_latest(self, season: str, endpoint: str) -> JsonPayload | None:
        endpoint_dir = self._endpoint_dir(season, endpoint)
        if not endpoint_dir.exists():
            return None
        cache_files = sorted(endpoint_dir.glob("*.json"), reverse=True)
        if not cache_files:
            return None
        cached = json.loads(cache_files[0].read_text(encoding="utf-8"))
        if isinstance(cached, dict) and "raw_payload" in cached:
            return cast(JsonPayload, cached["raw_payload"])
        return cast(JsonPayload, cached)

    def latest_path(self, season: str, endpoint: str) -> Path | None:
        endpoint_dir = self._endpoint_dir(season, endpoint)
        if not endpoint_dir.exists():
            return None
        cache_files = sorted(endpoint_dir.glob("*.json"), reverse=True)
        return cache_files[0] if cache_files else None

    def _endpoint_dir(self, season: str, endpoint: str) -> Path:
        return self.root_dir / self._safe_path_part(season) / self._safe_path_part(endpoint)

    @staticmethod
    def _safe_path_part(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9_.=-]+", "_", value.strip())
        return cleaned or "unknown"
