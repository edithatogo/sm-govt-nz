#!/usr/bin/env python3
import json
from pathlib import Path

setup = json.load(open('conductor/setup_state.json'))

print("=== TRACK 1 STATUS (govt_archive_per_agency_configs_20260626) ===")
track1 = [t for t in setup if t['id'] == 'govt_archive_per_agency_configs_20260626'][0]
print(f"Status: {ntrack1['status']}")
print(f"Tasks completed: {ntrack1['done']}/{ntrack1['total']}")

config_files = list(Path('config').glob('*.json'))
print(f"Config files generated: {len(config_files)}")

print()
print("=== NEXT TRACKS STATUS ===")
for tid in ['govt_archive_rss_onboarding_20260626', 'govt_archive_bluesky_onboarding_20260626', 'govt_archive_website_onboarding_20260626', 'govt_archive_youtube_onboarding_20260626', 'govt_archive_scheduled_multisource_20260626']:
    ntrack = [t for t in setup if t['id'] == tid][0]
    print(f"{tid}: {ntrack['status']} ({ntrack['done']}/{ntrack['total']})")
