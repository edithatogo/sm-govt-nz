"""Validate the social-media corpus registry readiness contract."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs" / "registry-readiness.md"
PUBLICATION = ROOT / "docs" / "corpus-social-media-government-nz-publication.md"
TARGETS = ROOT / "docs" / "publication-target-setup.md"


def check() -> None:
    text = DOC.read_text(encoding="utf-8") if DOC.is_file() else ""
    required = (
        "published_evidence_verified_metadata_sync_pending",
        "license: other",
        "#32",
        "#33",
        "#34",
        "Hugging Face Croissant",
        "10.5281/zenodo.21383327",
        "repository owner has approved",
        "externally synchronized",
    )
    missing = [fragment for fragment in required if fragment not in text]
    if missing:
        raise AssertionError("Archive registry readiness document missing: " + ", ".join(missing))
    for path, fragments in ((PUBLICATION, ("artifact-only", "Zenodo", "Hugging Face", "source-specific")), (TARGETS, ("license: other", "Zenodo"))):
        source = path.read_text(encoding="utf-8")
        missing = [fragment for fragment in fragments if fragment.lower() not in source.lower()]
        if missing:
            raise AssertionError(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")


if __name__ == "__main__":
    check()
    print("Social-media corpus registry readiness contract passed.")
