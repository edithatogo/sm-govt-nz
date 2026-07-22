# Bluesky Identity Resolver

Group registered social sources by canonical `agency_id`, preserve distinct public services, generate handle candidates, and emit a nonsecret onboarding packet. Treat the source allowlist and explicit excluded-source URL families as authoritative: distinguish current sources from retired or stale sibling accounts, preserve stale records for archival provenance, but never include them in an ongoing mirror input merely because they share an `agency_id`. Do not store complete email aliases.
