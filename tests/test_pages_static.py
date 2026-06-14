from pathlib import Path


def test_index_exposes_archive_source_health_dashboard() -> None:
    html = Path("index.html").read_text(encoding="utf-8")

    assert 'id="archive-health"' in html
    assert "conductor/archive_source_health.json" in html
    assert "renderArchiveHealth" in html
