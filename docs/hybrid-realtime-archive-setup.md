# Hybrid Realtime Archive Setup

RSS and Bluesky use a hybrid archive model:

- realtime push is preferred when a source or bridge can provide it;
- daily scheduled checks remain enabled as reconciliation/backfill;
- public Hugging Face and Zenodo corpus releases remain monthly.

## Repository receiver

Workflow: `.github/workflows/archive_push_events.yml`

Supported `repository_dispatch` event types:

- `rss_websub_notification`
- `bluesky_realtime_event`
- `atproto_realtime_event`

The workflow stores push payloads in:

- `historical_archive_raw/push/<platform>/...`
- `historical_archive_normalized/push/<platform>/...`
- `conductor/archive_push_state.json`
- `conductor/archive_push_health.json`

Those files are included in the normal monthly corpus bundle.

## RSS realtime path

Use WebSub where a feed advertises a hub.

Bridge responsibilities:

- discover `rel=hub` and `rel=self` links from RSS/Atom feeds;
- subscribe with the hub using a public callback URL;
- verify hub challenges;
- receive content distribution POSTs;
- forward each notification to GitHub as `repository_dispatch` type
  `rss_websub_notification`.

Minimum GitHub dispatch payload:

```json
{
  "event_type": "rss_websub_notification",
  "client_payload": {
    "platform": "rss",
    "feed_url": "https://example.govt.nz/rss.xml",
    "url": "https://example.govt.nz/news/item",
    "title": "Item title",
    "published": "2026-06-28T00:00:00Z",
    "content": "Optional item content"
  }
}
```

Daily RSS polling remains required for:

- feeds without WebSub hubs;
- missed hub deliveries;
- source health checks;
- historical/backfill coverage.

## Bluesky realtime path

Use the AT Protocol firehose (`com.atproto.sync.subscribeRepos`) from a small
always-on bridge. The bridge should filter events to known NZ government DIDs or
handles, then forward matching records to GitHub as `repository_dispatch` type
`bluesky_realtime_event`.

Minimum GitHub dispatch payload:

```json
{
  "event_type": "bluesky_realtime_event",
  "client_payload": {
    "platform": "bluesky",
    "did": "did:plc:example",
    "handle": "agency.govt.nz",
    "uri": "at://did:plc:example/app.bsky.feed.post/...",
    "cid": "baf...",
    "text": "Post text",
    "createdAt": "2026-06-28T00:00:00Z"
  }
}
```

Daily Bluesky archiving remains required for:

- firehose bridge downtime;
- cursor/replay gaps;
- source inventory reconciliation;
- source health checks.

## GitHub dispatch authentication

Realtime bridges need a GitHub token with permission to call:

`POST /repos/edithatogo/sm-govt-nz/dispatches`

Keep that token outside the archive repository where possible, for example in
the bridge host's secret store.

## Release guardrail

Realtime push ingestion must not publish Hugging Face or Zenodo releases.
Monthly public corpus release remains owned by `Publish Archives`.
