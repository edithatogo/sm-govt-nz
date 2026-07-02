import argparse
import json
from email import policy
from email.parser import BytesParser
from pathlib import Path
from typing import Any

from scripts.archive_email_payload import archive_email_payload
from scripts.archive_registered_sources import DEFAULT_MANIFEST, load_json, source_result, write_json

DEFAULT_INPUT_DIR = Path("manual_archive_seeds/newsletter_payloads")
DEFAULT_REPORT = Path("conductor/newsletter_payload_archive_report.json")
DEFAULT_RAW_ROOT = Path("historical_archive_raw/newsletter_email")
DEFAULT_NORMALIZED_ROOT = Path("historical_archive_normalized/newsletter")


def newsletter_sources(manifest: dict[str, Any], agency_id: str = "") -> list[dict[str, Any]]:
    sources = []
    for source in manifest.get("sources", []):
        if not isinstance(source, dict):
            continue
        if source.get("platform") != "newsletter" and source.get("source_type") not in {"newsletter", "email_subscription"}:
            continue
        if agency_id and source.get("agency_id") != agency_id:
            continue
        sources.append(source)
    return sources


def load_newsletter_payloads(input_dir: Path) -> list[dict[str, Any]]:
    if not input_dir.exists():
        return []
    payloads: list[dict[str, Any]] = []
    for path in sorted(input_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() == ".json":
            loaded = json.loads(path.read_text(encoding="utf-8"))
            items = loaded.get("payloads", [loaded]) if isinstance(loaded, dict) else loaded
            if not isinstance(items, list):
                raise ValueError(f"newsletter payload JSON must be an object or list: {path}")
            for item in items:
                if not isinstance(item, dict):
                    raise ValueError(f"newsletter payload item must be an object: {path}")
                item = dict(item)
                item.setdefault("payload_path", str(path).replace("\\", "/"))
                payloads.append(item)
        elif path.suffix.lower() == ".eml":
            payloads.append(load_eml_payload(path))
    return payloads


def load_eml_payload(path: Path) -> dict[str, Any]:
    message = BytesParser(policy=policy.default).parsebytes(path.read_bytes())
    text = ""
    html = ""
    if message.is_multipart():
        for part in message.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain" and not text:
                text = str(part.get_content())
            elif content_type == "text/html" and not html:
                html = str(part.get_content())
    else:
        if message.get_content_type() == "text/html":
            html = str(message.get_content())
        else:
            text = str(message.get_content())
    return {
        "message_id": str(message.get("Message-ID") or ""),
        "from": str(message.get("From") or ""),
        "to": str(message.get("To") or ""),
        "subject": str(message.get("Subject") or ""),
        "received_at": str(message.get("Date") or ""),
        "text": text,
        "html": html,
        "raw_mime": path.read_text(encoding="utf-8", errors="replace"),
        "payload_path": str(path).replace("\\", "/"),
    }


def payload_key(payload: dict[str, Any]) -> tuple[str, str]:
    return str(payload.get("source_id") or ""), str(payload.get("agency_id") or "")


def payloads_for_source(source: dict[str, Any], payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_id = str(source.get("source_id") or "")
    agency_id = str(source.get("agency_id") or "")
    matched = []
    for payload in payloads:
        payload_source_id, payload_agency_id = payload_key(payload)
        if payload_source_id and payload_source_id == source_id:
            matched.append(payload)
        elif payload_agency_id and payload_agency_id == agency_id:
            matched.append(payload)
    return matched


def archive_newsletter_payloads(
    *,
    manifest_path: Path = DEFAULT_MANIFEST,
    input_dir: Path = DEFAULT_INPUT_DIR,
    raw_root: Path = DEFAULT_RAW_ROOT,
    normalized_root: Path = DEFAULT_NORMALIZED_ROOT,
    agency_id: str = "",
) -> dict[str, Any]:
    manifest = load_json(manifest_path)
    sources = newsletter_sources(manifest, agency_id=agency_id)
    results: list[dict[str, Any]] = []
    try:
        payloads = load_newsletter_payloads(input_dir)
    except (json.JSONDecodeError, ValueError) as exc:
        payloads = []
        results.append(
            {
                "source_id": "",
                "agency_id": agency_id,
                "platform": "newsletter",
                "source_type": "email_subscription",
                "status": "payload_invalid",
                "reason": str(exc)[:300],
            }
        )
    for source in sources:
        matched = payloads_for_source(source, payloads)
        if not matched:
            results.append(source_result(source, "missing_payload", f"no newsletter payload matched {source.get('source_id') or source.get('agency_id')}"))
            continue
        for payload in matched:
            enriched = dict(payload)
            enriched.setdefault("source_id", source.get("source_id"))
            enriched.setdefault("agency_id", source.get("agency_id"))
            enriched.setdefault("source_account", source.get("account") or source.get("url") or "newsletter")
            enriched.setdefault("source_kind", source.get("source_type") or "email_subscription")
            enriched.setdefault("source_platform", "newsletter")
            enriched.setdefault("platform", "newsletter")
            try:
                record = archive_email_payload(
                    enriched,
                    raw_root=raw_root,
                    normalized_root=normalized_root,
                )
            except (ValueError, OSError, TypeError) as exc:
                results.append(source_result(source, "payload_invalid", str(exc)[:300]))
                continue
            result = source_result(source, "captured", f"archived newsletter payload {record['record_id']}")
            result["record_id"] = record["record_id"]
            result["raw_path"] = record["raw_path"]
            results.append(result)
    status_counts: dict[str, int] = {}
    for row in results:
        status = str(row.get("status") or "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
    return {
        "inputs": {
            "manifest": str(manifest_path),
            "input_dir": str(input_dir),
            "agency_id": agency_id,
            "raw_root": str(raw_root),
            "normalized_root": str(normalized_root),
        },
        "summary": {
            "selected_sources": len(sources),
            "payload_count": len(payloads),
            "platform_counts": {"newsletter": len(sources)},
            "status_counts": dict(sorted(status_counts.items())),
            "status_by_platform": {"newsletter": dict(sorted(status_counts.items()))},
        },
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive operator-provided newsletter JSON or EML payloads.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--raw-root", type=Path, default=DEFAULT_RAW_ROOT)
    parser.add_argument("--normalized-root", type=Path, default=DEFAULT_NORMALIZED_ROOT)
    parser.add_argument("--agency-id", default="")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    report = archive_newsletter_payloads(
        manifest_path=args.manifest,
        input_dir=args.input_dir,
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
        agency_id=args.agency_id,
    )
    write_json(args.report, report)
    print(f"Archived newsletter payloads: {report['summary']['status_counts']}")


if __name__ == "__main__":
    main()
