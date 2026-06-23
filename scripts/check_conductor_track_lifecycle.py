import json 
from pathlib import Path 
ROOT = Path(__file__).resolve().parents[1] 
errors = [] 
setup = json.loads((ROOT / 'conductor/setup_state.json').read_text(encoding='utf-8')) 
manifest = json.loads((ROOT / 'conductor/track_lifecycle_manifest.json').read_text(encoding='utf-8')) 
track_dirs = {p.name for p in (ROOT / 'conductor/tracks').iterdir() if p.is_dir()} 
setup_ids = {item['id'] for item in setup} 
manifest_ids = {item['track_id'] for item in manifest.get('tracks', [])} 
if setup_ids != track_dirs: 
    errors.append({'kind': 'setup_track_dir_mismatch', 'missing_from_setup': sorted(track_dirs - setup_ids), 'missing_dirs': sorted(setup_ids - track_dirs)}) 
if setup_ids != manifest_ids: 
    errors.append({'kind': 'manifest_mismatch', 'missing_from_manifest': sorted(setup_ids - manifest_ids), 'unknown_manifest_tracks': sorted(manifest_ids - setup_ids)}) 
for item in setup: 
    if item.get('status') != 'completed' or item.get('done') != item.get('total') or item.get('pending') != int(0) or item.get('inprogress') != int(0) or item.get('blockers') != 'None': 
        errors.append({'kind': 'incomplete_setup_state', 'track_id': item.get('id'), 'state': item})
for entry in manifest.get('tracks', []): 
    if not (entry.get('implemented') and entry.get('reviewed') and entry.get('archived')): 
        errors.append({'kind': 'incomplete_lifecycle', 'track_id': entry.get('track_id'), 'entry': entry}) 
paths = [ROOT / 'conductor/tracks.md'] + sorted((ROOT / 'conductor/tracks').glob('*/plan.md')) 
for path in paths: 
    text = path.read_text(encoding='utf-8') 
    if '[~]' in text or '[ ]' in text: 
        errors.append({'kind': 'open_task_marker', 'path': str(path.relative_to(ROOT))}) 
result = {'complete': not errors, 'track_count': len(setup), 'errors': errors} 
print(json.dumps(result, indent=2)) 
raise SystemExit(1 if errors else 0)
