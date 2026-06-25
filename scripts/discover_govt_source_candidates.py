import argparse
import hashlib
import html
import json
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


DEFAULT_REGISTRY = Path("registry/government_directory.json")
DEFAULT_CONFIG = Path("config/govt_source_discovery.json")
DEFAULT_REPORT = Path("conductor/govt_source_candidate_report.json")
DEFAULT_SUMMARY = Path("conductor/govt_source_candidate_summary.md")
DEFAULT_MANIFEST = Path("conductor/govt_archive_source_manifest.json")

PLATFORM_HOSTS = {
    "bluesky": ("bsky.app",),
    "facebook": ("facebook.com", "fb.com"),
    "instagram": ("instagram.com",),
    "linkedin": ("linkedin.com",),
    "threads": ("threads.net",),
    "x": ("x.com", "twitter.com"),
    "youtube": ("youtube.com", "youtu.be"),
}

NEWSLETTER_TERMS = ("newsletter", "subscribe", "email updates", "alerts", "mailing list")
FEED_TERMS = ("rss", "atom", "feed.xml", "/feed")


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.alternates: list[dict[str, str]] = []
        self._active_href = ""
        self._active_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {name.lower(): value or "" for name, value in attrs}
        if tag == "a" and attr.get("href"):
            self._active_href = attr["href"]
            self._active_text = []
        if tag == "link" and attr.get("href"):
            rel = attr.get("rel", "").lower()
            typ = attr.get("type", "").lower()
            if "alternate" in rel and ("rss" in typ or "atom" in typ or "xml" in typ):
                self.alternates.append(
                    {
                        "href": attr["href"],
                        "title": attr.get("title", ""),
                        "type": typ,
                    }
                )

    def handle_data(self, data: str) -> None:
        if self._active_href:
            self._active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._active_href:
            self.links.append(
                {
                    "href": self._active_href,
                    "text": html.unescape(" ".join(self._active_text).strip()),
                }
            )
            self._active_href = ""
            self._active_text = []


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def stable_id(*parts: str) -> str:
    joined = "|".join(part.strip().lower() for part in parts if part)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:16]


def normalize_agencies(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, dict) and isinstance(raw.get("agencies"), list):
        return raw["agencies"]
    if isinstance(raw, list):
        return raw
    raise ValueError("government directory must be an agency list or an object with agencies")


def social_profile_items(agency: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    profiles = agency.get("social_profiles") or {}
    if isinstance(profiles, dict):
        return [(platform, value) for platform, value in profiles.items() if isinstance(value, dict)]
    if isinstance(profiles, list):
        items = []
        for profile in profiles:
            if isinstance(profile, dict):
                platform = str(profile.get("platform") or detect_platform(profile.get("url", "")) or "unknown")
                items.append((platform, profile))
        return items
    return []


def policy_for(config: dict[str, Any], platform: str) -> dict[str, Any]:
    policy = config.get("platform_archive_policy", {}).get(platform, {})
    return {
        "feasibility": policy.get("feasibility", "unknown"),
        "archive_status": policy.get("archive_status", "candidate"),
        "access_method": policy.get("access_method", "review_required"),
        "auth": policy.get("auth", "review_required"),
        "notes": policy.get("notes", ""),
    }


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    for platform, hosts in PLATFORM_HOSTS.items():
        if any(host == candidate or host.endswith("." + candidate) for candidate in hosts):
            return platform
    return ""


def candidate(
    agency: dict[str, Any],
    source_type: str,
    platform: str,
    url: str,
    origin: str,
    config: dict[str, Any],
    **extra: Any,
) -> dict[str, Any]:
    source_policy = policy_for(config, platform or source_type)
    agency_id = agency["agency_id"]
    return {
        "candidate_id": stable_id(agency_id, source_type, platform, url),
        "agency_id": agency_id,
        "agency_name": agency.get("name", ""),
        "agency_type": agency.get("type", ""),
        "portfolio": agency.get("portfolio", ""),
        "official_website": agency.get("official_website", ""),
        "source_type": source_type,
        "platform": platform,
        "url": url,
        "origin": origin,
        "feasibility": source_policy["feasibility"],
        "archive_status": source_policy["archive_status"],
        "access_method": source_policy["access_method"],
        "auth": source_policy["auth"],
        "policy_notes": source_policy["notes"],
        **candidate_confidence(source_type, platform, url, origin, config),
        **extra,
    }


def domain_from_url(url):
    return urlparse(url).netloc.lower().removeprefix("www.")


def domain_trust(url, config):
    domain = domain_from_url(url)
    heuristics = config.get("heuristics", {})
    for suffix in heuristics.get("high_trust_suffixes", []):
        if domain.endswith(suffix.lstrip(".")):
            return "high"
    for suffix in heuristics.get("trusted_domain_suffixes", []):
        if domain.endswith(suffix.lstrip(".")):
            return "medium"
    return "unknown"


def search_queries_for_agency(agency, config):
    website = agency.get("official_website", "")
    domain = domain_from_url(website) if website else ""
    values = {"agency_name": agency.get("name", ""), "agency_id": agency.get("agency_id", ""), "domain": domain}
    queries = []
    for template in config.get("heuristics", {}).get("platform_search_templates", []):
        query = template.get("query", "")
        for key, value in values.items():
            query = query.replace("{" + key + "}", value)
        queries.append({"platform": template.get("platform", ""), "query": query})
    return queries


def candidate_confidence(source_type, platform, url, origin, config):
    trust = domain_trust(url, config)
    score = 0.35
    signals = []
    if origin.startswith("registry"):
        score += 0.35
        signals.append("registry_known")
    if trust == "high":
        score += 0.2
        signals.append("high_trust_domain_suffix")
    elif trust == "medium":
        score += 0.1
        signals.append("trusted_domain_suffix")
    if platform in {"rss", "website_page", "bluesky"}:
        score += 0.1
        signals.append("archive_friendly_platform")
    if source_type == "search_seed":
        score = min(score, 0.45)
        signals.append("unverified_search_seed")
    return {"confidence_score": round(min(score, 0.95), 2), "domain_trust": trust, "trust_signals": signals}


def registry_candidates(agencies: list[dict[str, Any]], config: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for agency in agencies:
        website = agency.get("official_website", "")
        if website:
            found.append(
                candidate(
                    agency,
                    "website_page",
                    "website_page",
                    website,
                    "registry.official_website",
                    config,
                    account=website,
                    status=agency.get("status", ""),
                )
            )
            for suffix in config.get("homepage_probe", {}).get("common_paths", []):
                if suffix == "/":
                    continue
                found.append(
                    candidate(
                        agency,
                        "search_seed",
                        "rss",
                        urljoin(website.rstrip("/") + "/", suffix.lstrip("/")),
                        "configured_common_path",
                        config,
                        account=website,
                        status="needs_probe",
                    )
                )
        for platform, profile in social_profile_items(agency):
            url = profile.get("url", "")
            if not url:
                continue
            found.append(
                candidate(
                    agency,
                    "social_profile",
                    platform,
                    url,
                    "registry.social_profiles",
                    config,
                    account=profile.get("handle", ""),
                    status=profile.get("status", ""),
                    account_classification=profile.get("account_classification", ""),
                    syndication_classification=profile.get("syndication_classification", ""),
                    discovered_at=profile.get("discovered_at", ""),
                )
            )
    return found


def fetch_html(url: str, timeout: int, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get("content-type", "")
        if "html" not in content_type and "xml" not in content_type and content_type:
            return ""
        data = response.read(750_000)
    return data.decode("utf-8", errors="replace")


def probe_url(agency: dict[str, Any], url: str, config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    probe_config = config.get("homepage_probe", {})
    try:
        body = fetch_html(
            url,
            timeout=int(probe_config.get("timeout_seconds", 12)),
            user_agent=probe_config.get("user_agent", "sm-govt-nz-source-discovery/1.0"),
        )
    except Exception as exc:  # noqa: BLE001 - report probe failures without failing the whole run.
        return [], {"url": url, "status": "failed", "error": str(exc)[:240]}
    if not body:
        return [], {"url": url, "status": "skipped", "error": "non-html response"}

    parser = LinkCollector()
    parser.feed(body)
    results: list[dict[str, Any]] = []
    for alternate in parser.alternates:
        href = urljoin(url, alternate["href"])
        results.append(
            candidate(
                agency,
                "rss_feed",
                "rss",
                href,
                "homepage.link_alternate",
                config,
                account=agency.get("official_website", ""),
                link_title=alternate.get("title", ""),
                mime_type=alternate.get("type", ""),
                status="discovered",
            )
        )
    for link in parser.links:
        href = urljoin(url, link["href"])
        lower = f"{href} {link.get('text', '')}".lower()
        platform = detect_platform(href)
        if platform:
            results.append(
                candidate(
                    agency,
                    "social_profile",
                    platform,
                    href,
                    "homepage.link",
                    config,
                    account=link.get("text", ""),
                    status="discovered",
                )
            )
        if any(term in lower for term in FEED_TERMS):
            results.append(
                candidate(
                    agency,
                    "rss_feed",
                    "rss",
                    href,
                    "homepage.link",
                    config,
                    account=agency.get("official_website", ""),
                    link_text=link.get("text", ""),
                    status="discovered",
                )
            )
        if any(term in lower for term in NEWSLETTER_TERMS):
            results.append(
                candidate(
                    agency,
                    "newsletter",
                    "newsletter",
                    href,
                    "homepage.link",
                    config,
                    account=agency.get("official_website", ""),
                    link_text=link.get("text", ""),
                    status="discovered",
                )
            )
    return results, {"url": url, "status": "ok", "links": len(parser.links), "alternates": len(parser.alternates)}


def probe_candidates(agencies: list[dict[str, Any]], config: dict[str, Any], max_agencies: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    found: list[dict[str, Any]] = []
    probe_log: list[dict[str, Any]] = []
    probe_config = config.get("homepage_probe", {})
    max_pages = int(probe_config.get("max_pages_per_agency", 1))
    common_paths = probe_config.get("common_paths", ["/"])
    for agency in agencies[:max_agencies or len(agencies)]:
        base = agency.get("official_website")
        if not base:
            continue
        urls = [urljoin(base.rstrip("/") + "/", suffix.lstrip("/")) for suffix in common_paths[:max_pages]]
        for url in dict.fromkeys(urls):
            candidates, status = probe_url(agency, url, config)
            found.extend(candidates)
            probe_log.append({"agency_id": agency["agency_id"], **status})
    return found, probe_log


def dedupe(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in candidates:
        existing = by_id.get(item["candidate_id"])
        if existing is None:
            by_id[item["candidate_id"]] = item
            continue
        origins = sorted(set((existing.get("origin", "") + "," + item.get("origin", "")).split(",")))
        existing["origin"] = ",".join(origin for origin in origins if origin)
    return sorted(by_id.values(), key=lambda row: (row["agency_id"], row["source_type"], row["platform"], row["url"]))


def source_id(item: dict[str, Any]) -> str:
    return f"{item['agency_id']}-{item['platform']}-{stable_id(item['url'])[:8]}"


def build_manifest(report: dict[str, Any]) -> dict[str, Any]:
    sources = []
    for item in report["candidates"]:
        if item["source_type"] == "search_seed":
            continue
        sources.append(
            {
                "source_id": source_id(item),
                "candidate_id": item["candidate_id"],
                "agency_id": item["agency_id"],
                "agency_name": item["agency_name"],
                "source_type": item["source_type"],
                "platform": item["platform"],
                "url": item["url"],
                "account": item.get("account", ""),
                "feasibility": item["feasibility"],
                "archive_status": item["archive_status"],
                "access_method": item["access_method"],
                "auth": item["auth"],
                "origin": item["origin"],
                "notes": item["policy_notes"],
            }
        )
    return refresh_manifest_summary(
        {
            "generated_at": report["generated_at"],
            "description": "Archive onboarding manifest generated from the government source candidate report.",
            "sources": sources,
        }
    )



def refresh_manifest_summary(manifest: dict[str, Any]) -> dict[str, Any]:
    sources = sorted(manifest.get("sources", []), key=lambda row: (row.get("agency_id", ""), row.get("platform", ""), row.get("url", "")))
    counts = Counter(source.get("archive_status", "unknown") for source in sources)
    manifest["summary"] = {
        "total_sources": len(sources),
        "archive_status_counts": dict(sorted(counts.items())),
    }
    manifest["sources"] = sources
    return manifest


def merge_existing_manifest_sources(
    manifest: dict[str, Any],
    existing_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if not existing_manifest:
        return refresh_manifest_summary(manifest)
    sources = list(manifest.get("sources", []))
    by_source_id = {str(source.get("source_id")): index for index, source in enumerate(sources) if source.get("source_id")}
    by_tuple = {
        (str(source.get("agency_id")), str(source.get("platform")), str(source.get("url"))): index
        for index, source in enumerate(sources)
    }
    for existing in existing_manifest.get("sources", []):
        source_id_key = str(existing.get("source_id"))
        tuple_key = (str(existing.get("agency_id")), str(existing.get("platform")), str(existing.get("url")))
        index = by_source_id.get(source_id_key)
        if index is None:
            index = by_tuple.get(tuple_key)
        if index is None:
            preserved = {**existing, "origin": existing.get("origin", "manual.registration")}
            sources.append(preserved)
            by_source_id[str(preserved.get("source_id"))] = len(sources) - 1
            by_tuple[(str(preserved.get("agency_id")), str(preserved.get("platform")), str(preserved.get("url")))] = len(sources) - 1
            continue
        merged = {**existing, **sources[index]}
        if str(existing.get("origin", "")).startswith("manual"):
            merged["manual_registration"] = True
            merged["manual_registered_at"] = existing.get("created_at") or existing.get("manual_registered_at", "")
        sources[index] = merged
    manifest["sources"] = sources
    return refresh_manifest_summary(manifest)

def summarize(report: dict[str, Any], manifest: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Government Source Discovery Summary",
        "",
        f"Generated: {report['generated_at']}",
        "",
        "## Coverage",
        "",
        f"- Agencies: {summary['agency_count']}",
        f"- Agencies without known social profiles: {summary['agencies_without_social_profiles']}",
        f"- Known registry social profiles: {summary['known_registry_social_profiles']}",
        f"- Candidate records: {summary['candidate_count']}",
        f"- Archive manifest sources: {manifest['summary']['total_sources']}",
        "",
        "## Candidates by Platform",
        "",
    ]
    for platform, count in summary["platform_counts"].items():
        lines.append(f"- {platform}: {count}")
    lines.extend(["", "## Candidates by Archive Status", ""])
    for status, count in manifest["summary"]["archive_status_counts"].items():
        lines.append(f"- {status}: {count}")
    lines.extend(
        [
            "",
            "## Operational Notes",
            "",
            "- RSS, public website pages, and Bluesky are the highest-priority automated archive lanes.",
            "- YouTube is listed as candidate until channel handles are resolved to stable channel feeds.",
            "- Meta platforms should use Graph/Threads APIs or authorized exports; avoid brittle unauthenticated scraping.",
            "- LinkedIn and X are retained in the manifest with lower feasibility so archive work can proceed from approved exports or public archive sources.",
            "- `conductor/govt_source_candidate_report.json` contains the exhaustive candidate-level detail for review and onboarding.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_report(args: argparse.Namespace) -> tuple[dict[str, Any], dict[str, Any]]:
    config = load_json(args.config)
    agencies = normalize_agencies(load_json(args.registry))
    candidates = registry_candidates(agencies, config)
    probe_log: list[dict[str, Any]] = []
    if args.probe_homepages:
        probed, probe_log = probe_candidates(agencies, config, args.max_agencies)
        candidates.extend(probed)
    candidates = dedupe(candidates)
    search_queries = [
        {"agency_id": agency["agency_id"], "agency_name": agency.get("name", ""), "queries": search_queries_for_agency(agency, config)}
        for agency in agencies
    ]

    platform_counts = Counter(item["platform"] for item in candidates)
    source_type_counts = Counter(item["source_type"] for item in candidates)
    feasibility_counts = Counter(item["feasibility"] for item in candidates)
    known_social_count = sum(1 for item in candidates if item["origin"] == "registry.social_profiles")
    report = {
        "generated_at": now_iso(),
        "inputs": {
            "registry": str(args.registry),
            "config": str(args.config),
            "probe_homepages": args.probe_homepages,
            "max_agencies": args.max_agencies,
        },
        "summary": {
            "agency_count": len(agencies),
            "agencies_without_social_profiles": sum(1 for agency in agencies if not social_profile_items(agency)),
            "known_registry_social_profiles": known_social_count,
            "candidate_count": len(candidates),
            "platform_counts": dict(sorted(platform_counts.items())),
            "source_type_counts": dict(sorted(source_type_counts.items())),
            "feasibility_counts": dict(sorted(feasibility_counts.items())),
        },
        "probe_log": probe_log,
        "platform_search_queries": search_queries,
        "candidates": candidates,
    }
    manifest = build_manifest(report)
    existing_manifest = None
    manifest_path = getattr(args, "manifest", None)
    if manifest_path and Path(manifest_path).exists():
        existing_manifest = load_json(Path(manifest_path))
    return report, merge_existing_manifest_sources(manifest, existing_manifest)


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover government public source and archive candidates.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--probe-homepages", action="store_true")
    parser.add_argument("--max-agencies", type=int, default=0)
    args = parser.parse_args()

    report, manifest = build_report(args)
    write_json(args.report, report)
    write_json(args.manifest, manifest)
    args.summary.parent.mkdir(parents=True, exist_ok=True)
    args.summary.write_text(summarize(report, manifest), encoding="utf-8")
    print(
        "Discovered "
        f"{report['summary']['candidate_count']} candidates and "
        f"{manifest['summary']['total_sources']} archive manifest sources."
    )


if __name__ == "__main__":
    main()
