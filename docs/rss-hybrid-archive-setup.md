# RSS Hybrid Archive Setup

RSS uses a hybrid ingestion model:

- WebSub push when a feed advertises a supported hub;
- scheduled RSS checks as the fallback and reconciliation mechanism;
- monthly public corpus release through `Publish Archives`.

## Realtime WebSub path

External WebSub receivers should forward accepted notifications to GitHub as a
repository-dispatch event:

- event type: `rss_websub_notification`
- receiver workflow: `.github/workflows/archive_push_events.yml`

Minimum payload:

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

## Scheduled fallback

Daily RSS/archive checks remain enabled through the existing current-source
archive workflow. Scheduled checks are still required because many RSS feeds do
not advertise WebSub hubs, and because push delivery is not guaranteed.

## Release guardrail

RSS push and daily checks are ingestion only. They must not publish Hugging Face
or Zenodo releases. Public corpus releases remain monthly.
