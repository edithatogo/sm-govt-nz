import json
print('Starting validation...')
config_dir = 'config'
manifest_path = 'conductor/govt_archive_source_manifest.json'
manifest = json.load(open(manifest_path))
print('Manifest loaded with', len(manifest['sources']), 'sources')
import os
config_files = [f for f in os.listdir(config_dir) if f.endswith('_sources.json')]
print('Found', len(config_files), 'agent configs')
valid=0
for cf in list(config_files)[:3]:  # Just test first 3
    try:
        data = json.load(open(os.path.join(config_dir, cf)))
        print('  '+cf+':', len(data.get('contracts', [])), 'contracts')
        valid += 1
    except Exception as e:
        print('  '+cf+': ERROR -', e)
print('Valid configs:', str(valid)+'/'+str(min(3, len(config_files))))