import json

from scripts.publish_zenodo_deposition import publish_deposition, update_publication_report


class FakeResponse:
    def __init__(self, payload: dict) -> None:
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_update_publication_report_records_published_doi(tmp_path) -> None:
    report_path = tmp_path / "publication.json"
    report_path.write_text(
        json.dumps({"zenodo": {"status": "draft_uploaded_pending_review_and_publish"}}),
        encoding="utf-8",
    )

    report = update_publication_report(
        report_path=report_path,
        deposition_id="20690547",
        publish_response={
            "doi": "10.5281/zenodo.20690547",
            "conceptdoi": "10.5281/zenodo.20690546",
            "links": {"html": "https://zenodo.org/records/20690547"},
        },
    )

    assert report["zenodo"]["status"] == "published_with_doi"
    assert report["zenodo"]["deposition_id"] == 20690547
    assert report["zenodo"]["doi"] == "10.5281/zenodo.20690547"
    assert report["zenodo"]["published_url"] == "https://zenodo.org/records/20690547"


def test_publish_deposition_posts_to_zenodo_publish_action(tmp_path) -> None:
    seen = {}

    def opener(request, timeout):
        seen["url"] = request.full_url
        seen["authorization"] = request.headers["Authorization"]
        seen["method"] = request.get_method()
        return FakeResponse({"doi": "10.5281/zenodo.1", "links": {"html": "https://z.test/1"}})

    report = publish_deposition(
        deposition_id="1",
        token="zen-token",
        report_path=tmp_path / "report.json",
        api_url="https://zenodo.example/api/deposit/depositions",
        opener=opener,
    )

    assert seen == {
        "url": "https://zenodo.example/api/deposit/depositions/1/actions/publish",
        "authorization": "Bearer zen-token",
        "method": "POST",
    }
    assert report["zenodo"]["status"] == "published_with_doi"
