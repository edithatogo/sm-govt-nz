#!/usr/bin/env python3
"""Evaluate adapter libraries and source-type risk taxonomy for non-credential captures.

Phase 1 - Adapter Ranking (Task 3): Add source-type risk field.
Phase 2 - Library Evaluation (Tasks 5 & 6): httpx + trafilatura evaluation.

Output: conductor/adapter_library_evaluation.json
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "conductor" / "adapter_library_evaluation.json"


def main() -> None:
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "track_id": "govt_archive_noncredential_adapters_20260625",
        "source_type_risk_taxonomy": build_risk_taxonomy(),
        "library_evaluations": {
            "feedparser": {"verdict": "actively_used"},
            "httpx": {"verdict": "evaluated"},
            "trafilatura": {"verdict": "not_imported_but_htmlparser_used"},
        },
        "youtube_rss_strategy": {
            "preferred": "channel RSS via feedparser",
            "fallback": "yt-dlp or YouTube Data API v3",
        },
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    print(f"Written: {OUTPUT}")


def build_risk_taxonomy() -> dict[str, dict[str, str]]:
    return {
        "website_page": {"legal": "low", "technical": "low", "credential": "none", "rate_limit": "low"},
        "rss": {"legal": "low", "technical": "low", "credential": "none", "rate_limit": "low"},
        "youtube": {"legal": "low", "technical": "medium", "credential": "none", "rate_limit": "low"},
        "bluesky": {"legal": "low", "technical": "low", "credential": "low", "rate_limit": "medium"},
        "newsletter_page": {"legal": "medium", "technical": "medium", "credential": "none", "rate_limit": "low"},
        "sitemap": {"legal": "low", "technical": "low", "credential": "none", "rate_limit": "low"},
        "media_release": {"legal": "low", "technical": "medium", "credential": "none", "rate_limit": "low"},
        "facebook": {"legal": "high", "technical": "high", "credential": "high", "rate_limit": "high"},
        "instagram": {"legal": "high", "technical": "high", "credential": "high", "rate_limit": "high"},
        "threads": {"legal": "medium", "technical": "high", "credential": "high", "rate_limit": "medium"},
        "linkedin": {"legal": "high", "technical": "high", "credential": "high", "rate_limit": "high"},
        "x": {"legal": "medium", "technical": "medium", "credential": "high", "rate_limit": "high"},
    }


if __name__ == "__main__":
    main()