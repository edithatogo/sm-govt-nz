import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


PUBLIC_API_BASE = "https://public.api.bsky.app"


def archive_profiles(
    handles: list[str],
    *,
    output_dir: str | Path,
    api_base_url: str = PUBLIC_API_BASE,
) -> list[Path]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    captured_at = datetime.now(UTC).isoformat()

    for handle in handles:
        profile = fetch_profile(handle, api_base_url=api_base_url)
        profile["captured_at"] = captured_at
        profile["source_api"] = "app.bsky.actor.getProfile"
        prefix = safe_name(handle)
        json_path = root / f"{prefix}-profile.json"
        json_path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(json_path)

        for field, suffix in (("avatar", "avatar"), ("banner", "banner")):
            url = str(profile.get(field, ""))
            if not url:
                continue
            asset_path = root / f"{prefix}-{suffix}{extension_from_url(url)}"
            download_asset(url, asset_path)
            written.append(asset_path)

    return written


def fetch_profile(handle: str, *, api_base_url: str = PUBLIC_API_BASE) -> dict:
    query = urlencode({"actor": handle})
    request = Request(
        f"{api_base_url.rstrip('/')}/xrpc/app.bsky.actor.getProfile?{query}",
        headers={"Accept": "application/json"},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def download_asset(url: str, output_path: Path) -> None:
    request = Request(url, headers={"Accept": "*/*", "User-Agent": "sm-govt-nz-archive/1.0"})
    with urlopen(request, timeout=30) as response:
        output_path.write_bytes(response.read())


def safe_name(value: str) -> str:
    return "".join(char if char.isalnum() else "-" for char in value.lower()).strip("-")


def extension_from_url(url: str) -> str:
    suffix = Path(urlparse(url).path).suffix
    return suffix if suffix else ".bin"


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive public Bluesky profile metadata and assets.")
    parser.add_argument("handles", nargs="+")
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    output_dir = args.output_dir or f"profile_archive/courts-nz/{datetime.now(UTC).date().isoformat()}"
    written = archive_profiles(args.handles, output_dir=output_dir)
    for path in written:
        print(path)


if __name__ == "__main__":
    main()
