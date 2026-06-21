import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import sys
from email.message import EmailMessage
from email.utils import format_datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.archive_schema import NormalizedArchiveRecord, build_normalized_record


URL_RE = re.compile(r"https?://[^\s<>\"]+")


def archive_email_payload(
    payload: dict[str, Any],
    *,
    raw_root: str | Path = "historical_archive_raw/email",
    normalized_root: str | Path = "historical_archive_normalized/email",
) -> NormalizedArchiveRecord:
    captured_at = _utc_now()
    received_at = _coerce_datetime(str(payload.get("received_at") or payload.get("date") or captured_at))
    message_id = _message_id(payload)
    record_id = _safe_id(message_id)
    month = received_at[:7]
    raw_path = Path(raw_root) / month / f"{record_id}.eml"
    raw_bytes = _raw_email_bytes(payload, received_at=received_at, message_id=message_id)
    _write_bytes_once(raw_path, raw_bytes)
    normalized_path = Path(normalized_root) / f"{month}.jsonl"
    existing_record = _existing_normalized_record(f"email:{record_id}", normalized_path)

    record = build_normalized_record(
        record_id=f"email:{record_id}",
        agency_id="courts-nz",
        source_platform="email",
        source_account="judgments-of-public-interest-subscription",
        source_kind="judgments_subscription",
        source_url=_canonical_url(payload),
        canonical_url=_canonical_url(payload),
        original_created_at=received_at,
        captured_at=str(existing_record.get("captured_at") or captured_at),
        content=_normalized_content(payload),
        raw_path=str(raw_path).replace("\\", "/"),
        extraction_method=str(
            payload.get("extraction_method") or "cloudflare_email_routing_worker"
        ),
        media_refs=[],
        cross_source_ids={"message_id": message_id},
    )
    _upsert_normalized_record(record, Path(normalized_root))
    return record


def load_payload(path: str | Path | None, payload_json: str | None) -> dict[str, Any]:
    if payload_json:
        payload = json.loads(payload_json)
    elif path:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    else:
        payload = json.loads(sys.stdin.read())
    if not isinstance(payload, dict):
        raise ValueError("Email payload must be a JSON object.")
    return payload


def _message_id(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("message_id") or payload.get("Message-ID") or "").strip()
    if explicit:
        return explicit
    digest = hashlib.sha256(_normalized_content(payload).encode("utf-8")).hexdigest()[:24]
    return f"generated-{digest}"


def _raw_email_bytes(payload: dict[str, Any], *, received_at: str, message_id: str) -> bytes:
    raw_base64 = payload.get("raw_mime_base64")
    if isinstance(raw_base64, str) and raw_base64.strip():
        return base64.b64decode(raw_base64)
    raw_mime = payload.get("raw_mime")
    if isinstance(raw_mime, str) and raw_mime.strip():
        return raw_mime.encode("utf-8")

    message = EmailMessage()
    message["From"] = str(payload.get("from") or "")
    message["To"] = str(payload.get("to") or "")
    message["Subject"] = str(payload.get("subject") or "")
    message["Message-ID"] = message_id
    message["Date"] = format_datetime(_parse_datetime(received_at))
    text = str(payload.get("text") or "")
    html = str(payload.get("html") or "")
    if html and text:
        message.set_content(text)
        message.add_alternative(html, subtype="html")
    elif html:
        message.add_alternative(html, subtype="html")
    else:
        message.set_content(text)
    return message.as_bytes()


def _normalized_content(payload: dict[str, Any]) -> str:
    subject = str(payload.get("subject") or "").strip()
    text = str(payload.get("text") or "").strip()
    html = str(payload.get("html") or "").strip()
    body = text or _html_to_text(html)
    return "\n\n".join(part for part in [subject, body] if part).strip()


def _canonical_url(payload: dict[str, Any]) -> str:
    links = payload.get("links")
    if isinstance(links, list):
        for link in links:
            if isinstance(link, str) and link.startswith(("http://", "https://")):
                return link
    content = _normalized_content(payload)
    match = URL_RE.search(content)
    return match.group(0).rstrip(").,]") if match else ""


def _html_to_text(value: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", value)
    return " ".join(without_tags.split())


def _upsert_normalized_record(record: NormalizedArchiveRecord, normalized_root: Path) -> None:
    month = _coerce_datetime(record["original_created_at"])[:7]
    shard_path = normalized_root / f"{month}.jsonl"
    existing: dict[str, dict[str, Any]] = {}
    if shard_path.exists():
        for line in shard_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            payload = json.loads(line)
            existing[str(payload["record_id"])] = payload
    existing[record["record_id"]] = dict(record)
    shard_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(existing[key], ensure_ascii=False, sort_keys=True)
        for key in sorted(existing)
    ]
    shard_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _existing_normalized_record(record_id: str, shard_path: Path) -> dict[str, Any]:
    if not shard_path.exists():
        return {}
    for line in shard_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("record_id") == record_id:
            return payload
    return {}


def _write_bytes_once(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    path.write_bytes(content)


def _coerce_datetime(value: str) -> str:
    parsed = _parse_datetime(value)
    return parsed.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_datetime(value: str) -> dt.datetime:
    cleaned = value.strip().replace("Z", "+00:00")
    try:
        parsed = dt.datetime.fromisoformat(cleaned)
    except ValueError:
        parsed = dt.datetime.now(dt.timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "-", value.strip("<> ")).strip("-")
    if cleaned:
        return cleaned[:80]
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive a Courts of NZ judgment email payload.")
    parser.add_argument("--payload-file")
    parser.add_argument("--payload-json")
    parser.add_argument("--raw-root", default="historical_archive_raw/email")
    parser.add_argument("--normalized-root", default="historical_archive_normalized/email")
    args = parser.parse_args()

    record = archive_email_payload(
        load_payload(args.payload_file, args.payload_json),
        raw_root=args.raw_root,
        normalized_root=args.normalized_root,
    )
    print(json.dumps(record, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
