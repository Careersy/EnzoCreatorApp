"""Aggregate creator pattern signals from graph retrieval output."""

from __future__ import annotations

from collections import Counter
from typing import Any


class CreatorPatternProfiler:
    def summarize(self, graph_payload: dict[str, Any]) -> dict[str, Any]:
        records = list(graph_payload.get("records", []))
        strongest_hooks = list(graph_payload.get("strongest_hooks", []))

        pattern_counts = Counter()
        creators = Counter()
        for row in records:
            pattern = str(row.get("pattern", ""))
            creator = str(row.get("creator", ""))
            if pattern:
                pattern_counts[pattern] += 1
            if creator:
                creators[creator] += 1

        return {
            "top_patterns": [p for p, _ in pattern_counts.most_common(12)],
            "top_creators": [c for c, _ in creators.most_common(6)],
            "strongest_hooks": [str(h.get("name", "")) for h in strongest_hooks][:10],
        }
