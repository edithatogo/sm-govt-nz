from scripts.post_missing_courts_mirror_posts import _clear_pending


def test_clear_pending_removes_delivered_post_and_empty_parents():
    state = {
        "pending_post_ids": {
            "threads": {
                "courtsofnz.bsky.social": ["post-1"],
            },
        },
    }

    _clear_pending(state, "threads", "courtsofnz.bsky.social", "post-1")

    assert state == {"pending_post_ids": {}}


def test_clear_pending_preserves_other_pending_posts():
    state = {
        "pending_post_ids": {
            "threads": {
                "courtsofnz.bsky.social": ["post-1", "post-2"],
            },
        },
    }

    _clear_pending(state, "threads", "courtsofnz.bsky.social", "post-1")

    assert state["pending_post_ids"]["threads"]["courtsofnz.bsky.social"] == ["post-2"]
