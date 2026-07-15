# NZ Government Archive Completion Matrix

Generated: 2026-07-15T11:36:35+00:00

## Completion

| Metric | Count |
| --- | ---: |
| Total candidates | 5602 |
| Registered sources | 5602 |
| Archived sources | 2157 |
| Terminal evidence sources | 3428 |
| Incomplete actionable sources | 17 |
| Automation faults | 11 |
| Completion | 99.7% |

## Lifecycle states

| State | Count |
| --- | ---: |
| `archived` | 2157 |
| `automation_fault` | 11 |
| `scheduled` | 6 |
| `terminal_deleted` | 120 |
| `terminal_empty` | 1692 |
| `terminal_external_access` | 1037 |
| `terminal_invalid` | 579 |

## Next work

| Rank | Platform | Agency | Source | Action |
| ---: | --- | --- | --- | --- |
| 1 | `website_page` | `education-review-office` | `education-review-office-website_page-bd13cf94` | `retry_public_website_capture` |
| 2 | `website_page` | `ministry-of-education` | `3d96533a759ca232` | `retry_public_website_capture` |
| 3 | `website_page` | `porirua-city-council` | `porirua-city-council-website_page-dedfde72` | `retry_public_website_capture` |
| 4 | `website_page` | `predator-free-2050` | `predator-free-2050-website_page-fb3a8c52` | `retry_public_website_capture` |
| 5 | `website_page` | `selwyn-district-council` | `selwyn-district-council-website_page-ce27b442` | `retry_public_website_capture` |
| 6 | `website_page` | `te-mangai-paho` | `2fb4e37a2d9d0551` | `retry_public_website_capture` |
| 7 | `website_page` | `te-mangai-paho` | `52524d2842b1897f` | `retry_public_website_capture` |
| 8 | `website_page` | `te-mangai-paho` | `743298f0a7fa4e8d` | `retry_public_website_capture` |
| 9 | `website_page` | `te-mangai-paho` | `90c9ddd4cf6de8cc` | `retry_public_website_capture` |
| 10 | `website_page` | `te-mangai-paho` | `debaf37a55dde1a0` | `retry_public_website_capture` |
| 11 | `website_page` | `te-mangai-paho` | `f4d8fe95d6e773b4` | `retry_public_website_capture` |
| 12 | `website_page` | `tourism-nz` | `tourism-nz-website_page-1c93446d` | `retry_public_website_capture` |
| 13 | `rss` | `kawerau-district-council` | `21fcb81fa4c3c580` | `run_registered_source_adapter` |
| 14 | `rss` | `kawerau-district-council` | `c194b53bc0b69b11` | `run_registered_source_adapter` |
| 15 | `api` | `victoria-university-of-wellington` | `b21a114650cf7c1f` | `run_registered_source_adapter` |
| 16 | `rss` | `whakatane-district-council` | `1359e749adf17233` | `run_registered_source_adapter` |
| 17 | `rss` | `whakatane-district-council` | `bd0270e877bc7fa5` | `run_registered_source_adapter` |

The full deterministic queue is in `conductor/archive_completion_work_queue.json`.
