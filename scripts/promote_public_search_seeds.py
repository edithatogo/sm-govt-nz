import argparse
import json
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.register_archive_source import load_manifest, upsert_source, write_manifest  # noqa: E402


DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")
DEFAULT_SUMMARY = Path("conductor/public_search_seed_promotion_summary.json")
GOVERNMENT_SUFFIXES = (".govt.nz", ".mil.nz", ".parliament.nz")


def host_from_url(url: str) -> str:
    parsed = urlparse(url)
    return (parsed.hostname or "").lower()


def is_public_government_domain(url: str) -> bool:
    host = host_from_url(url)
    return any(host.endswith(suffix) for suffix in GOVERNMENT_SUFFIXES)


def is_rss_feed(url: str) -> bool:
    lower = url.lower()
    path = urlparse(url).path.lower().rstrip("/")
    return (
        "feed.json" not in lower
        and (
            lower.endswith(("atom.xml", "rss.xml", "feed.xml", "rss-news.xml"))
            or path.endswith(("/feed", "/rss", "/rss2", "/atom", "/homerss"))
            or path.endswith(("/feed/news", "/feed/rss2", "/feed/atom"))
            or path.endswith(("/home/changes", "/home/rss"))
        )
    )


def is_json_feed(url: str, text: str = "") -> bool:
    lower = url.lower()
    return "feed.json" in lower or "json feed" in text.lower() or lower.endswith("feed+json")


def is_api_endpoint(url: str) -> bool:
    lower = url.lower()
    return any(
        token in lower
        for token in (
            "/.well-known/webfinger",
            "activity+json",
            "/openapi.json",
            "/swagger.json",
            "/api.json",
        )
    )


def choose_promotion(source: dict[str, Any]) -> dict[str, str] | None:
    url = str(source.get("url") or "").strip()
    if not url:
        return None
    link_text = str(source.get("link_text") or source.get("link_title") or "")
    if is_json_feed(url, link_text):
        return {
            "source_type": "json_feed",
            "platform": "json_feed",
            "archive_status": "ready",
            "feasibility": "high",
            "access_method": "public_json_feed",
            "auth": "none",
        }
    if is_rss_feed(url):
        return {
            "source_type": "rss_feed",
            "platform": "rss",
            "archive_status": "ready",
            "feasibility": "high",
            "access_method": "public_rss_feed",
            "auth": "none",
        }
    if is_api_endpoint(url):
        return {
            "source_type": "api_endpoint",
            "platform": "api",
            "archive_status": "ready",
            "feasibility": "high",
            "access_method": "public_api_or_openapi",
            "auth": "none",
        }
    if is_public_government_domain(url):
        return {
            "source_type": "website_page",
            "platform": "website_page",
            "archive_status": "ready",
            "feasibility": "high",
            "access_method": "public_website",
            "auth": "none",
        }
    return None


def promote_manifest(manifest_path: Path) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    promoted = 0
    by_type: dict[str, int] = {}
    for source in manifest.get("sources", []):
        if str(source.get("source_type") or "") != "search_seed":
            continue
        promotion = choose_promotion(source)
        if not promotion:
            continue
        source.update(
            {
                **promotion,
                "notes": (
                    f"Promoted from search_seed using public endpoint heuristics; "
                    f"original_source_type=search_seed"
                ),
            }
        )
        promoted += 1
        promoted_type = promotion["source_type"]
        by_type[promoted_type] = by_type.get(promoted_type, 0) + 1

    write_manifest(manifest_path, manifest)
    return {
        "promoted_count": promoted,
        "promoted_counts_by_type": dict(sorted(by_type.items())),
        "government_suffixes": list(GOVERNMENT_SUFFIXES),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Promote public search seeds into archiveable source types.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    summary = promote_manifest(args.manifest)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
