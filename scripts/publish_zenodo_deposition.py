import argparse
import json
import os
from pathlib import Path
from typing import Any, Callable
from urllib.request import Request, urlopen


DEFAULT_API_URL = "https://zenodo.org/api/deposit/depositions"
DEFAULT_REPORT_PATH = Path("conductor/archive_publication_report_20260614.json")
CONFIRMATION = "publish-zenodo-doi"


def publish_deposition(
    *,
    deposition_id: str,
    token: str,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    api_url: str = DEFAULT_API_URL,
    opener: Callable[..., Any] = urlopen,
) -> dict[str, Any]:
    if not token:
        raise ValueError("ZENODO_TOKEN is required.")

    publish_url = f"{api_url.rstrip('/')}/{deposition_id}/actions/publish"
    request = Request(
        publish_url,
        data=b"",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with opener(request, timeout=60) as response:
        body = response.read().decode("utf-8")
    payload = json.loads(body) if body else {}
    return update_publication_report(
        report_path=report_path,
        deposition_id=deposition_id,
        publish_response=payload,
    )


def update_publication_report(
    *,
    report_path: str | Path,
    deposition_id: str,
    publish_response: dict[str, Any],
) -> dict[str, Any]:
    path = Path(report_path)
    report = _load_json(path)
    zenodo = report.setdefault("zenodo", {})
    links = publish_response.get("links", {}) if isinstance(publish_response, dict) else {}
    metadata = publish_response.get("metadata", {}) if isinstance(publish_response, dict) else {}

    zenodo.update(
        {
            "deposition_id": int(deposition_id) if str(deposition_id).isdigit() else deposition_id,
            "status": "published_with_doi",
            "doi": publish_response.get("doi") or metadata.get("doi") or "",
            "conceptdoi": publish_response.get("conceptdoi") or metadata.get("conceptdoi") or "",
            "published_url": links.get("html") or publish_response.get("html_url") or "",
            "latest_publish_response": publish_response,
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object.")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish an existing Zenodo draft deposition.")
    parser.add_argument("--deposition-id", required=True)
    parser.add_argument("--api-url", default=DEFAULT_API_URL)
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()

    if args.confirm != CONFIRMATION:
        raise SystemExit(f"Refusing to publish without --confirm {CONFIRMATION!r}.")

    report = publish_deposition(
        deposition_id=args.deposition_id,
        token=os.getenv("ZENODO_TOKEN", ""),
        report_path=args.report,
        api_url=args.api_url,
    )
    print(json.dumps(report.get("zenodo", {}), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
