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
DEFAULT_PARTIES = Path("registry/parties.json")
DEFAULT_PERSONS = Path("registry/persons.json")
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

PLATFORM_SHARE_PATH_PREFIXES = {
    "bluesky": ("/intent/",),
    "facebook": ("/sharer/", "/share.php", "/dialog/"),
    "linkedin": ("/sharearticle", "/sharing/"),
    "threads": ("/intent/",),
    "x": ("/intent/", "/share"),
}

NEWSLETTER_TERMS = ("newsletter", "subscribe", "email updates", "alerts", "mailing list")
FEED_TERMS = ("rss", "atom", "feed.xml", "feed.json", "json feed")
API_TERMS = ("api", "openapi", "swagger", "developer", "data service")
MICROFORMAT_TERMS = ("h-feed", "h-entry", "microformat", "microformats")
ACTIVITYPUB_TERMS = ("activitypub", "mastodon", "fediverse", "webfinger")


class LinkCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[dict[str, str]] = []
        self.alternates: list[dict[str, str]] = []
        self.hubs: list[dict[str, str]] = []
        self.microformats: list[dict[str, str]] = []
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
            if "alternate" in rel and (
                "rss" in typ
                or "atom" in typ
                or "xml" in typ
                or "feed+json" in typ
                or "activity+json" in typ
                or "json" in typ
            ):
                self.alternates.append(
                    {
                        "href": attr["href"],
                        "rel": rel,
                        "title": attr.get("title", ""),
                        "type": typ,
                    }
                )
            if "hub" in rel:
                self.hubs.append({"href": attr["href"], "rel": rel, "type": typ})
        class_value = attr.get("class", "")
        if class_value and any(term in class_value.lower().split() for term in ("h-feed", "h-entry", "h-event")):
            self.microformats.append({"tag": tag, "class": class_value})

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
    with path.open(encoding="utf-8-sig") as handle:
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


def normalize_records(raw: Any, key: str) -> list[dict[str, Any]]:
    if isinstance(raw, dict) and isinstance(raw.get(key), list):
        return [item for item in raw[key] if isinstance(item, dict)]
    if isinstance(raw, dict) and isinstance(raw.get("value"), list):
        return [item for item in raw["value"] if isinstance(item, dict)]
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    return []


def social_profile_items(agency: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    profiles = agency.get("social_profiles") or {}
    if isinstance(profiles, dict):
        return [(platform, value) for platform, value in profiles.items() if isinstance(value, dict)]
    if isinstance(profiles, list):
        items = []
        for profile in profiles:
            if isinstance(profile, dict):
                url = profile.get("url", "")
                platform = str(profile.get("platform") or "").strip().lower()
                if not platform:
                    platform = detect_platform(url) or "unknown"
                if platform == "bluesky":
                    handle = profile.get("handle") or bluesky_handle_from_url(url)
                    if handle:
                        profile = {**profile, "handle": handle}
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
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.lower()
    for platform, hosts in PLATFORM_HOSTS.items():
        if not any(host == candidate or host.endswith("." + candidate) for candidate in hosts):
            continue
        if any(path.startswith(prefix) for prefix in PLATFORM_SHARE_PATH_PREFIXES.get(platform, ())):
            return ""
        if platform == "bluesky":
            return "bluesky" if parsed.path.startswith("/profile/") else ""
        return platform
    return ""


def bluesky_handle_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    if host != "bsky.app" and not host.endswith(".bsky.app"):
        return ""
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "profile":
        return parts[1]
    return ""


def url_path_segments(url: str) -> list[str]:
    return [part.lower() for part in urlparse(url).path.split("/") if part]


def looks_like_feed_url(url: str, text: str = "", mime_type: str = "") -> bool:
    lower_url = url.lower()
    lower_text = text.lower()
    lower_mime = mime_type.lower()
    if "feedback" in lower_url or "what-is-rss" in lower_url:
        return False
    if any(token in lower_mime for token in ("rss", "atom", "xml")):
        return True
    path = urlparse(url).path.lower().rstrip("/")
    segments = url_path_segments(url)
    if path.endswith(("atom.xml", "rss.xml", "feed.xml", "rss-news.xml")):
        return True
    if segments and segments[-1] in {"feed", "rss", "rss2", "atom", "homerss"}:
        return True
    if len(segments) >= 2 and segments[-2:] in (["feed", "news"], ["feed", "rss2"], ["feed", "atom"]):
        return True
    if path.endswith(("/home/changes", "/home/rss")):
        return True
    return any(term in lower_text for term in FEED_TERMS)


def looks_like_json_feed_url(url: str, text: str = "", mime_type: str = "") -> bool:
    lower_url = url.lower()
    lower_text = text.lower()
    lower_mime = mime_type.lower()
    if "wp-json" in lower_url or "oembed" in lower_url:
        return False
    return "feed+json" in lower_mime or lower_url.rstrip("/").endswith("/feed.json") or "json feed" in lower_text


def looks_like_api_url(url: str, text: str = "") -> bool:
    lower_text = text.lower()
    segments = set(url_path_segments(url))
    path = urlparse(url).path.lower()
    if segments.intersection({"api", "apis", "developer", "developers", "swagger"}):
        return True
    if path.endswith(("/openapi.json", "/swagger.json", "/api.json")):
        return True
    return any(term in lower_text for term in (" openapi ", " swagger ", " api ", "developer api", "data service"))

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
    confidence_text = " ".join(
        str(value)
        for value in [
            url,
            agency.get("name", ""),
            agency.get("official_website", ""),
            extra.get("account", ""),
            extra.get("link_text", ""),
            extra.get("link_title", ""),
        ]
        if value
    )
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
        **candidate_confidence(source_type, platform, url, origin, config, agency_id, confidence_text),
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


def learning_entries(config):
    learning_path = config.get("heuristics", {}).get("learning_file")
    if not learning_path:
        return []
    path = Path(learning_path)
    if not path.exists():
        return []
    try:
        learning = load_json(path)
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(learning, dict):
        entries = learning.get("entries", learning.get("records", []))
    else:
        entries = learning
    return entries if isinstance(entries, list) else []


def learning_signal(agency_id, platform, url, config):
    positive = {"accepted", "approved", "confirmed", "official", "true_positive"}
    negative = {"rejected", "false_positive", "unofficial", "exclude", "excluded"}
    for entry in reversed(learning_entries(config)):
        if not isinstance(entry, dict):
            continue
        same_url = str(entry.get("url", "")).rstrip("/") == url.rstrip("/")
        same_agency_platform = entry.get("agency_id") == agency_id and entry.get("platform") == platform
        if not same_url and not same_agency_platform:
            continue
        decision = str(entry.get("decision") or entry.get("label") or entry.get("status") or "").lower()
        if decision in positive:
            return "positive"
        if decision in negative:
            return "negative"
        if decision == "needs_review":
            return "needs_review"
    return ""


def candidate_confidence(source_type, platform, url, origin, config, agency_id="", text=""):
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
    if platform in {"rss", "json_feed", "website_page", "bluesky", "microformat"}:
        score += 0.1
        signals.append("archive_friendly_platform")
    heuristics = config.get("heuristics", {})
    lower_text = text.lower()
    for term in heuristics.get("official_account_terms", []):
        normalized = str(term).strip().lower()
        if normalized and normalized in lower_text:
            score += 0.05
            signals.append(f"official_term:{normalized}")
            break
    for term in heuristics.get("negative_account_terms", []):
        normalized = str(term).strip().lower()
        if normalized and normalized in lower_text:
            score -= 0.25
            signals.append(f"negative_term:{normalized}")
            break
    learned = learning_signal(agency_id, platform, url, config)
    if learned == "positive":
        score += 0.2
        signals.append("learning_positive")
    elif learned == "negative":
        score -= 0.35
        signals.append("learning_negative")
    elif learned == "needs_review":
        score -= 0.05
        signals.append("learning_needs_review")
    if source_type == "search_seed":
        score = min(score, 0.45)
        signals.append("unverified_search_seed")
    return {"confidence_score": round(min(max(score, 0.05), 0.95), 2), "domain_trust": trust, "trust_signals": signals}


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
                    account=profile.get("handle") or bluesky_handle_from_url(url),
                    status=profile.get("status", ""),
                    account_classification=profile.get("account_classification", ""),
                    syndication_classification=profile.get("syndication_classification", ""),
                    discovered_at=profile.get("discovered_at", ""),
                )
            )
    return found


def political_registry_candidates(
    parties: list[dict[str, Any]],
    persons: list[dict[str, Any]],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for party in parties:
        pseudo_agency = {
            "agency_id": f"party-{party.get('party_id', '')}",
            "name": party.get("name", ""),
            "type": "Political Party",
            "portfolio": "Parliament",
            "official_website": party.get("website", ""),
            "status": party.get("status", ""),
            "social_profiles": party.get("social_profiles", {}),
        }
        for platform, profile in social_profile_items(pseudo_agency):
            if platform != "bluesky":
                continue
            url = profile.get("url", "")
            if not url:
                continue
            found.append(
                candidate(
                    pseudo_agency,
                    "social_profile",
                    platform,
                    url,
                    "registry.parties.social_profiles",
                    config,
                    account=profile.get("handle") or bluesky_handle_from_url(url),
                    status=profile.get("status", ""),
                    account_classification=profile.get("account_classification", ""),
                    syndication_classification=profile.get("syndication_classification", ""),
                    registry_record_kind="party",
                    party_id=party.get("party_id", ""),
                )
            )
    for person in persons:
        pseudo_agency = {
            "agency_id": f"person-{person.get('person_id', '')}",
            "name": person.get("full_name", ""),
            "type": "Person",
            "portfolio": "Public Officeholder",
            "official_website": person.get("biography_url", ""),
            "status": "active",
            "social_profiles": person.get("social_profiles", {}),
        }
        for platform, profile in social_profile_items(pseudo_agency):
            if platform != "bluesky":
                continue
            url = profile.get("url", "")
            if not url:
                continue
            found.append(
                candidate(
                    pseudo_agency,
                    "social_profile",
                    platform,
                    url,
                    "registry.persons.social_profiles",
                    config,
                    account=profile.get("handle") or bluesky_handle_from_url(url),
                    status=profile.get("status", ""),
                    account_classification=profile.get("account_classification", ""),
                    syndication_classification=profile.get("syndication_classification", ""),
                    registry_record_kind="person",
                    person_id=person.get("person_id", ""),
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
        mime_type = alternate.get("type", "").lower()
        if looks_like_json_feed_url(href, alternate.get("title", ""), mime_type):
            source_type = "json_feed"
            platform = "json_feed"
        elif "activity+json" in mime_type:
            source_type = "activitypub_profile"
            platform = "activitypub"
        else:
            source_type = "rss_feed"
            platform = "rss"
        results.append(
            candidate(
                agency,
                source_type,
                platform,
                href,
                "homepage.link_alternate",
                config,
                account=agency.get("official_website", ""),
                link_title=alternate.get("title", ""),
                mime_type=alternate.get("type", ""),
                status="discovered",
            )
        )
    for hub in parser.hubs:
        href = urljoin(url, hub["href"])
        results.append(
            candidate(
                agency,
                "websub_hub",
                "websub",
                href,
                "homepage.link_hub",
                config,
                account=agency.get("official_website", ""),
                link_title="WebSub hub",
                mime_type=hub.get("type", ""),
                status="discovered",
            )
        )
    if parser.microformats:
        results.append(
            candidate(
                agency,
                "microformat_feed",
                "microformat",
                url,
                "homepage.microformat_class",
                config,
                account=agency.get("official_website", ""),
                link_text=", ".join(sorted({item["class"] for item in parser.microformats}))[:240],
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
                    account=bluesky_handle_from_url(href) or link.get("text", ""),
                    status="discovered",
                )
            )
        if looks_like_feed_url(href, link.get("text", "")) or looks_like_json_feed_url(href, link.get("text", "")):
            source_type = "json_feed" if looks_like_json_feed_url(href, link.get("text", "")) else "rss_feed"
            platform = "json_feed" if source_type == "json_feed" else "rss"
            results.append(
                candidate(
                    agency,
                    source_type,
                    platform,
                    href,
                    "homepage.link",
                    config,
                    account=agency.get("official_website", ""),
                    link_text=link.get("text", ""),
                    status="discovered",
                )
            )
        if any(term in lower for term in ACTIVITYPUB_TERMS):
            results.append(
                candidate(
                    agency,
                    "activitypub_profile",
                    "activitypub",
                    href,
                    "homepage.link",
                    config,
                    account=link.get("text", ""),
                    link_text=link.get("text", ""),
                    status="discovered",
                )
            )
        if looks_like_api_url(href, f" {link.get('text', '')} "):
            results.append(
                candidate(
                    agency,
                    "api_endpoint",
                    "api",
                    href,
                    "homepage.link",
                    config,
                    account=agency.get("official_website", ""),
                    link_text=link.get("text", ""),
                    status="discovered",
                )
            )
        if any(term in lower for term in MICROFORMAT_TERMS):
            results.append(
                candidate(
                    agency,
                    "microformat_feed",
                    "microformat",
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
                "registry_record_kind": item.get("registry_record_kind", "agency"),
                "person_id": item.get("person_id", ""),
                "party_id": item.get("party_id", ""),
            }
        )
    return refresh_manifest_summary(
        {
            "generated_at": report["generated_at"],
            "description": "Archive onboarding manifest generated from the government source candidate report.",
            "sources": sources,
        }
    )


def should_preserve_existing_manifest_source(source: dict[str, Any]) -> bool:
    source_type = str(source.get("source_type") or "")
    platform = str(source.get("platform") or "")
    url = str(source.get("url") or "")
    if source_type == "social_profile" and platform in PLATFORM_HOSTS:
        return detect_platform(url) == platform
    return True



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
        if not should_preserve_existing_manifest_source(existing):
            continue
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
            "- Atom, JSON Feed, WebSub hubs, ActivityPub/WebFinger, public APIs, and microformats are now explicitly detected as reviewable source candidates.",
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
    parties_path = getattr(args, "parties", None)
    persons_path = getattr(args, "persons", None)
    parties = normalize_records(load_json(parties_path), "parties") if parties_path and parties_path.exists() else []
    persons = normalize_records(load_json(persons_path), "persons") if persons_path and persons_path.exists() else []
    candidates = registry_candidates(agencies, config)
    candidates.extend(political_registry_candidates(parties, persons, config))
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
            "parties": str(parties_path or ""),
            "persons": str(persons_path or ""),
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
    parser.add_argument("--parties", type=Path, default=DEFAULT_PARTIES)
    parser.add_argument("--persons", type=Path, default=DEFAULT_PERSONS)
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

