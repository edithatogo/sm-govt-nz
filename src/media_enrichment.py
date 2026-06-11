import json
import subprocess
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class MediaMetadata:
    source_url: str
    title: str
    uploader: str
    duration: float | None
    webpage_url: str
    thumbnail: str


class YtDlpClient:
    """Metadata-only wrapper around yt-dlp for public video/media URLs."""

    def __init__(self, command: str = "yt-dlp") -> None:
        self.command = command

    def extract_metadata(self, url: str) -> MediaMetadata:
        completed = subprocess.run(
            [
                self.command,
                "--dump-json",
                "--skip-download",
                "--no-playlist",
                url,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError((completed.stderr or completed.stdout).strip())
        payload = json.loads(completed.stdout.splitlines()[-1])
        return metadata_from_payload(url, payload)


def metadata_from_payload(source_url: str, payload: dict[str, Any]) -> MediaMetadata:
    return MediaMetadata(
        source_url=source_url,
        title=str(payload.get("title") or ""),
        uploader=str(payload.get("uploader") or payload.get("channel") or ""),
        duration=_optional_float(payload.get("duration")),
        webpage_url=str(payload.get("webpage_url") or source_url),
        thumbnail=str(payload.get("thumbnail") or ""),
    )


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
