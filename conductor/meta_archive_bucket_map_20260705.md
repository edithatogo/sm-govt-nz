# Meta archive bucket map - 2026-07-05

This report classifies the Meta government sources currently present in `conductor/govt_archive_source_manifest.json`.

## Summary

- Meta sources in manifest: 504
- Archive now via public snapshot: 501 (319 Facebook, 182 Instagram)
- Seed/API needed: 3 Threads
- Deferred business-account work: Threads authenticated API, Instagram authenticated API, Facebook authenticated API

## Bucket 1: archive now via public snapshot

- Instagram and Facebook Page/profile sources in the manifest can be archived via public-profile/page snapshots without creating a business account.
- This is archive-only capture, not mirroring.

## Bucket 2: seed/API needed

- Threads currently needs either approved API access or operator-authorized seed exports for complete coverage.
- The repo has a working read-only/API lane for Threads, but current app permissions still block live capture for the registered government sources.

## Bucket 3: deferred business-account work

- Any authenticated Meta API expansion for Instagram, Facebook, or full Threads coverage remains deferred until a later business-account decision.

## Examples

### instagram
- `accident-compensation-corporation-instagram-ebbf541a`: https://www.instagram.com/accnewzealand
- `accident-compensation-corporation-instagram-41dd3f71`: https://www.instagram.com/accnewzealand/
- `airways-nz-instagram-424df104`: https://www.instagram.com/airwaysnz/?hl=en
- `antarctica-nz-instagram-6ead4fe3`: https://www.instagram.com/antarctica.nz/
- `antarctica-nz-instagram-e4af56d7`: https://www.instagram.com/antarcticanz
- `ara-institute-of-canterbury-instagram-320deb41`: https://www.instagram.com/AraCanterbury/
- `ara-institute-of-canterbury-instagram-c465254c`: https://www.instagram.com/arainstitute
- `asurequality-instagram-e3f3ee93`: https://www.instagram.com/asurequality/?hl=en
- `auckland-council-instagram-ffa626d3`: https://www.instagram.com/aklcouncil/
- `auckland-council-instagram-920e5d51`: https://www.instagram.com/aklcouncil/?hl=en

### facebook
- `accident-compensation-corporation-facebook-a4eafd5a`: https://www.facebook.com/ACCNewZealand
- `airways-nz-facebook-2e76afae`: https://www.facebook.com/AirwaysNZ/
- `antarctica-nz-facebook-6494d1ed`: https://www.facebook.com/Antarctica.New.Zealand/
- `antarctica-nz-facebook-d81b995d`: https://www.facebook.com/AntarcticaNZ
- `ara-institute-of-canterbury-facebook-6ce26c93`: https://www.facebook.com/AraCanterbury
- `ara-institute-of-canterbury-facebook-0e0a7645`: https://www.facebook.com/AraInstitute
- `ashburton-district-council-facebook-60947088`: https://www.facebook.com/AshburtonDistrictCouncil
- `asurequality-facebook-602ae22f`: https://www.facebook.com/AsureQualityLtd
- `auckland-council-facebook-f66931c1`: https://www.facebook.com/aklcouncil
- `aut-university-facebook-0fb9a4b1`: https://www.facebook.com/AUTUniversity

### threads
- `nz-police-threads-newzealandpolice`: https://www.threads.net/@newzealandpolice
- `nzte-threads-nzte`: https://www.threads.net/@nzte
- `wellington-city-libraries-threads-wcl-library`: https://www.threads.net/@wcl_library
