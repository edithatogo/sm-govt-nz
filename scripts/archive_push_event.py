import gzip
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def main() -> None:
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    if not event_path.exists():
        raise SystemExit("GITHUB_EVENT_PATH is missing or does not exist.")

    event = json.loads(event_path.read_text(encoding="utf-8"))
    payload = event.get("client_payload") or {}
    if not isinstance(payload, dict):
        raise SystemExit("repository_dispatch client_payload must be an object.")

    event_type = str(
        event.get("event_type")
        or event.get("action")
        or _manual_event_type_from_payload(payload)
        or "push_event"
    )
    platform = _platform_from_event(event_type, payload)
    now = datetime.now(timezone.utc)
    record_id = _record_id(platform, payload, now)
    raw_path = _raw_path(platform, now, record_id)
    normalized_path = _normalized_path(platform, now)

    raw_path.parent.mkdir(parents=True, exist_ok=True)
    normalized_path.parent.mkdir(parents=True, exist_ok=True)

    raw_record = {
        "event_type": event_type,
        "platform": platform,
        "received_at": now.isoformat(),
        "payload": payload,
    }
    raw_path.write_text(json.dumps(raw_record, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    normalized = _normalized_record(
        platform=platform,
        event_type=event_type,
        payload=payload,
        raw_path=raw_path,
        received_at=now,
        record_id=record_id,
    )
    with normalized_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(normalized, sort_keys=True, ensure_ascii=False) + "\n")

    _append_health(platform, event_type, record_id, raw_path, normalized_path, now)
    _update_state(platform, record_id, now)


def _platform_from_event(event_type: str, payload: dict[str, Any]) -> str:
    platform = str(payload.get("platform") or "").strip().lower()
    if platform in {"rss", "bluesky"}:
        return platform
    if "rss" in event_type or "websub" in event_type:
        return "rss"
    if "bluesky" in event_type or "bsky" in event_type or "atproto" in event_type:
        return "bluesky"
    raise SystemExit(f"Unsupported push archive event type: {event_type}")


def _manual_event_type_from_payload(payload: dict[str, Any]) -> str:
    platform = str(payload.get("platform") or "").strip().lower()
    if platform == "rss":
        return "rss_manual_push_event"
    if platform == "bluesky":
        return "bluesky_manual_push_event"
    return ""


def _record_id(platform: str, payload: dict[str, Any], received_at: datetime) -> str:
    candidates = [
        payload.get("record_id"),
        payload.get("uri"),
        payload.get("cid"),
        payload.get("url"),
        payload.get("link"),
        payload.get("guid"),
        payload.get("id"),
    ]
    for candidate in candidates:
        if candidate:
            return f"{platform}:push:{_safe_digest(str(candidate))}"
    body = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return f"{platform}:push:{received_at.strftime('%Y%m%d%H%M%S')}:{_safe_digest(body)}"


def _raw_path(platform: str, received_at: datetime, record_id: str) -> Path:
    return (
        Path("historical_archive_raw")
        / "push"
        / platform
        / received_at.strftime("%Y")
        / received_at.strftime("%m")
        / f"{_safe_filename(record_id)}.json"
    )


def _normalized_path(platform: str, received_at: datetime) -> Path:
    return (
        Path("historical_archive_normalized")
        / "push"
        / platform
        / received_at.strftime("%Y")
        / f"{received_at.strftime('%m')}.jsonl"
    )


def _normalized_record(
    *,
    platform: str,
    event_type: str,
    payload: dict[str, Any],
    raw_path: Path,
    received_at: datetime,
    record_id: str,
) -> dict[str, Any]:
    text = _first_string(payload, ["text", "content", "title", "summary", "description"])
    source_url = _first_string(payload, ["url", "link", "source_url", "uri"])
    source_account = _first_string(payload, ["handle", "did", "feed_url", "source_account"])
    original_created_at = _first_string(
        payload,
        ["created_at", "createdAt", "published", "updated", "indexedAt"],
    )
    if not original_created_at:
        original_created_at = received_at.isoformat()
    return {
        "record_id": record_id,
        "source_platform": platform,
        "source_account": source_account,
        "source_url": source_url,
        "canonical_url": source_url,
        "text": text,
        "original_created_at": original_created_at,
        "captured_at": received_at.isoformat(),
        "capture_method": "push",
        "event_type": event_type,
        "raw_path": str(raw_path).replace("\\", "/"),
        "content_hash": _safe_digest(json.dumps(payload, sort_keys=True, ensure_ascii=False)),
    }


def _first_string(payload: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = payload.get(key)
        if value is not None:
            return str(value)
    return ""


def _append_health(
    platform: str,
    event_type: str,
    record_id: str,
    raw_path: Path,
    normalized_path: Path,
    received_at: datetime,
) -> None:
    path = Path("conductor/archive_push_health.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = []
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
    data.append(
        {
            "platform": platform,
            "event_type": event_type,
            "record_id": record_id,
            "received_at": received_at.isoformat(),
            "raw_path": str(raw_path).replace("\\", "/"),
            "normalized_path": str(normalized_path).replace("\\", "/"),
            "status": "archived",
        }
    )
    path.write_text(json.dumps(data[-500:], indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _update_state(platform: str, record_id: str, received_at: datetime) -> None:
    path = Path("conductor/archive_push_state.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {}
    if path.exists():
        state = json.loads(path.read_text(encoding="utf-8"))
    state[platform] = {
        "last_record_id": record_id,
        "last_received_at": received_at.isoformat(),
    }
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _safe_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]


def _safe_filename(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)


if __name__ == "__main__":
    main()
