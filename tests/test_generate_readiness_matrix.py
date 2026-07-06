from scripts.generate_readiness_matrix import classify_archive_mode, build_summary


def test_medium_and_substack_are_treated_as_archive_only_platforms() -> None:
    assert classify_archive_mode("medium", "resolver_ok") == "archive_only"
    assert classify_archive_mode("substack", "published_ok") == "archive_only"


def test_noncredential_medium_and_substack_count_as_capturable_without_credentials() -> None:
    summary = build_summary(
        [
            {"readiness": "resolver_ok", "platform": "medium", "source_type": "social_profile"},
            {"readiness": "published_ok", "platform": "substack", "source_type": "social_profile"},
            {"readiness": "blocked_credential", "platform": "linkedin", "source_type": "social_profile"},
        ]
    )

    assert summary["archive_mode_counts"] == {"archive_only": 3}
    assert summary["capturable_without_credentials"] == 2
    assert summary["credential_gated_blocked"] == 1
