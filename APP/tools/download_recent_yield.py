"""Download an attributed UPAg/DES source mirror, retaining its original CSV.

Resolve rotating CKAN resource IDs. Do not replace existing training data/models.
"""
import csv
import hashlib
import json
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE_URL = 'https://ckandev.indiadataportal.com/api/3/action/package_show?id=area-production-yield-apy'
STATES = {'Andhra Pradesh', 'Karnataka', 'Tamil Nadu', 'Telangana'}


def main():
    with urllib.request.urlopen(PACKAGE_URL, timeout=45) as response:
        package = json.load(response)['result']
    resources = [r for r in package['resources'] if '(UPAG)' in r['name'].upper() and r['format'].upper() == 'CSV']
    if len(resources) != 1:
        raise ValueError('Ambiguous UPAg CSV resource')
    resource = resources[0]
    out = ROOT / 'DATASET/raw/government/upag'
    out.mkdir(parents=True, exist_ok=True)
    path = out / 'cropwise_area_production_yield.csv'
    if not path.exists():
        with urllib.request.urlopen(resource['url'], timeout=90) as response:
            content = response.read()
        header = content.decode('utf-8-sig').splitlines()[0]
        if 'crop_name' not in header or 'production' not in header:
            raise ValueError('Download is not the expected source CSV')
        path.write_bytes(content)
    with path.open(newline='', encoding='utf-8-sig') as handle:
        rows = [r for r in csv.DictReader(handle) if r['state_name'] in STATES and r['crop_name'] == 'Rice']
    counts = Counter((r['state_name'], r['year']) for r in rows)
    with urllib.request.urlopen('https://ckandev.indiadataportal.com/api/3/action/datastore_search?resource_id=' + resource['id'] + '&limit=1', timeout=45) as response:
        metadata = json.load(response)['result']
    units = {f['id']: f.get('info', {}).get('units') for f in metadata['fields']}
    if units.get('area') != 'Hectares' or units.get('production') != 'Tonnes' or units.get('yield') != 'Kg per Hectare':
        raise ValueError('Source units changed; conversion requires review')
    provenance = {'retrieved_utc': datetime.now(timezone.utc).isoformat(),
                  'publisher': 'India Data Portal; source DES district data via UPAg, Ministry of Agriculture and Farmers Welfare',
                  'package_url': PACKAGE_URL, 'resource': resource,
                  'license': package['license_title'], 'license_id': package['license_id'],
                  'package_notes': package['notes'], 'units': units,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'bytes': path.stat().st_size, 'four_state_rice_rows': len(rows),
                  'counts': [{'state': s, 'agricultural_year': y, 'rows': n} for (s, y), n in sorted(counts.items())],
                  'training_status': 'source acquired; district, seasonal-calendar and weather joins require validation; deployed data unchanged'}
    (out / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(json.dumps({'bytes': path.stat().st_size, 'rice_rows': len(rows), 'counts': provenance['counts']}, indent=2))


if __name__ == '__main__':
    main()
