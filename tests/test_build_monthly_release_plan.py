import json
from pathlib import Path

import pytest

from scripts.build_monthly_release_plan import _iter_normalized_records


def test_iter_normalized_records_skips_unhydrated_git_lfs_pointer(tmp_path: Path) -> None:
    source_dir = tmp_path / "rss"
    source_dir.mkdir()
    (source_dir / "pointer.jsonl").write_text(
        "version https://git-lfs.github.com/spec/v1\n"
        "oid sha256:0123456789abcdef\n"
        "size 1234\n",
        encoding="utf-8",
    )
    expected = {"id": "rss:1", "captured_at": "2026-07-01T00:00:00Z"}
    (source_dir / "records.jsonl").write_text(
        json.dumps(expected) + "\n",
        encoding="utf-8",
    )

    assert _iter_normalized_records(tmp_path) == [("rss", expected)]


def test_iter_normalized_records_rejects_malformed_jsonl(tmp_path: Path) -> None:
    source_dir = tmp_path / "rss"
    source_dir.mkdir()
    (source_dir / "records.jsonl").write_text("not-json\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid JSONL"):
        _iter_normalized_records(tmp_path)
