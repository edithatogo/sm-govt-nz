import json

from scripts.archive_x_history import TweetCapture, archive_x_history, parse_tweet_html


def test_parse_tweet_html_extracts_text_and_date():
    text, created_at = parse_tweet_html(
        '<blockquote><p lang="en">Judgment published <a href="https://t.co/x">https://t.co/x</a></p>'
        '&mdash; Courts of New Zealand (@CourtsofNZ) <a>May 15, 2024</a></blockquote>'
    )

    assert text == "Judgment published https://t.co/x"
    assert created_at == "2024-05-15T00:00:00+00:00"


def test_archive_x_history_writes_raw_normalized_and_report(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.archive_x_history.fetch_cdx_captures",
        lambda: [
            TweetCapture(
                tweet_id="123",
                original_url="https://twitter.com/CourtsofNZ/status/123",
                snapshot_timestamp="20240515000000",
                digest="abc",
            )
        ],
    )
    monkeypatch.setattr(
        "scripts.archive_x_history.fetch_oembed",
        lambda _tweet_id: {
            "url": "https://x.com/CourtsofNZ/status/123",
            "html": (
                '<blockquote><p>Judgment published</p>&mdash; Courts of New Zealand '
                "(@CourtsofNZ) <a>May 15, 2024</a></blockquote>"
            ),
        },
    )

    report = archive_x_history(
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        report_path=tmp_path / "report.json",
    )

    assert report["archived_count"] == 1
    assert (tmp_path / "raw" / "2024-05" / "123.json").exists()
    normalized = (tmp_path / "normalized" / "2024-05.jsonl").read_text(encoding="utf-8")
    assert json.loads(normalized)["cross_source_ids"]["tweet_id"] == "123"
    assert json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))["failure_count"] == 0


def test_archive_x_history_reuses_existing_raw_payload(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "scripts.archive_x_history.fetch_cdx_captures",
        lambda: [
            TweetCapture(
                tweet_id="123",
                original_url="https://twitter.com/CourtsofNZ/status/123",
                snapshot_timestamp="20240515000000",
                digest="abc",
            )
        ],
    )

    def fail_fetch(_tweet_id):
        raise AssertionError("should reuse raw payload")

    monkeypatch.setattr("scripts.archive_x_history.fetch_oembed", fail_fetch)
    raw_path = tmp_path / "raw" / "2024-05" / "123.json"
    raw_path.parent.mkdir(parents=True)
    raw_path.write_text(
        json.dumps(
            {
                "capture": {"tweet_id": "123"},
                "oembed": {
                    "url": "https://x.com/CourtsofNZ/status/123",
                    "html": (
                        '<blockquote><p>Judgment published</p>&mdash; Courts of New Zealand '
                        "(@CourtsofNZ) <a>May 15, 2024</a></blockquote>"
                    ),
                },
            }
        ),
        encoding="utf-8",
    )

    report = archive_x_history(
        raw_root=tmp_path / "raw",
        normalized_root=tmp_path / "normalized",
        report_path=tmp_path / "report.json",
    )

    assert report["reused_raw_count"] == 1
    assert report["fetched_oembed_count"] == 0
