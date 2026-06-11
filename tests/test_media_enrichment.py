from src.media_enrichment import YtDlpClient, metadata_from_payload


def test_metadata_from_payload_normalizes_yt_dlp_output() -> None:
    metadata = metadata_from_payload(
        "https://video.example/watch",
        {
            "title": "Public briefing",
            "channel": "Agency channel",
            "duration": "42",
            "webpage_url": "https://video.example/watch",
            "thumbnail": "https://video.example/thumb.jpg",
        },
    )

    assert metadata.title == "Public briefing"
    assert metadata.uploader == "Agency channel"
    assert metadata.duration == 42.0


def test_yt_dlp_client_invokes_metadata_only_command(monkeypatch) -> None:
    calls = []

    def fake_run(args, capture_output, text, check):
        calls.append(args)

        class Completed:
            returncode = 0
            stdout = '{"title":"Video","uploader":"Agency","duration":1}\n'
            stderr = ""

        return Completed()

    monkeypatch.setattr("src.media_enrichment.subprocess.run", fake_run)

    metadata = YtDlpClient(command="yt-dlp-test").extract_metadata("https://example.test/video")

    assert calls[0][:4] == ["yt-dlp-test", "--dump-json", "--skip-download", "--no-playlist"]
    assert metadata.title == "Video"
