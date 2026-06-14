import json

REGISTRY_PATH = "registry/agencies.json"


def load_registry():
    with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_follow_matrix(registry):
    """
    Generates a matrix of required follows per platform.
    Returns: { platform: [ (follower_handle, target_handle), ... ] }
    """
    matrix = {}

    # Group active handles by platform
    platform_handles = {}
    for agency in registry:
        profiles = agency.get("social_profiles", {})
        for platform, profile in profiles.items():
            if profile.get("status") == "active":
                if platform not in platform_handles:
                    platform_handles[platform] = []
                platform_handles[platform].append(profile["handle"])

    # Generate bi-directional follows for each platform
    for platform, handles in platform_handles.items():
        matrix[platform] = []
        for follower in handles:
            for target in handles:
                if follower != target:
                    matrix[platform].append((follower, target))

    return matrix


def test_follow_matrix_generation():
    registry = load_registry()
    matrix = generate_follow_matrix(registry)

    assert "bluesky" in matrix
    # Based on current registry/agencies.json, we have 4 active bluesky accounts:
    # 1. courtsofnz.bsky.social
    # 2. health.govt.nz
    # 3. healthnz.govt.nz
    # 4. beehivenz.bsky.social

    bluesky_follows = matrix["bluesky"]
    assert len(bluesky_follows) == 4 * 3  # Each of 4 follows the other 3

    # Check for specific expected follows
    expected = ("courtsofnz.bsky.social", "health.govt.nz")
    assert expected in bluesky_follows

    # Ensure no self-follows
    for follower, target in bluesky_follows:
        assert follower != target


def test_no_duplicate_follows():
    registry = load_registry()
    matrix = generate_follow_matrix(registry)

    for platform, follows in matrix.items():
        assert len(follows) == len(set(follows))
