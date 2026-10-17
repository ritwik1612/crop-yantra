"""Verify the official archive and record a photo-free acquisition inventory."""
import csv
import hashlib
import io
import json
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
archive = ROOT / 'DATASET/images/source/paddy-disease-classification.zip'
prepared = ROOT / 'DATASET/images/prepared/paddy_doctor_4class'
manifest = json.loads((prepared / 'manifest.json').read_text(encoding='utf8'))
with zipfile.ZipFile(archive) as source:
    bad_member = source.testzip()
    if bad_member:
        raise ValueError(f'Archive CRC check failed: {bad_member}')
    labels = list(csv.DictReader(io.StringIO(source.read('train.csv').decode('utf-8-sig'))))
    member_count = len(source.namelist())
with archive.open('rb') as stream:
    archive_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
if archive_hash != manifest['archive_sha256']:
    raise ValueError('Prepared data does not match the current source archive')
report = {
    'recorded_utc': datetime.now(timezone.utc).isoformat(),
    'source': manifest['source'], 'source_url': manifest['source_url'],
    'archive_bytes': archive.stat().st_size, 'archive_sha256': archive_hash,
    'archive_crc_check': 'passed', 'archive_member_count': member_count,
    'source_labelled_images': len(labels),
    'source_class_counts': dict(Counter(row['label'] for row in labels)),
    'selected_classes': manifest['classes'], 'selected_images': len(manifest['images']),
    'selected_image_bytes': manifest['bytes'],
    'prepared_total_bytes': sum(p.stat().st_size for p in prepared.rglob('*') if p.is_file()),
    'selected_class_counts': dict(Counter(row['class'] for row in manifest['images'])),
    'split_counts': manifest['split_counts'],
    'candidate_images': manifest['candidate_images'],
    'perceptual_groups': manifest['duplicate_groups'],
    'conflicting_groups_excluded': manifest['conflicting_groups_excluded'],
    'exclusion_reasons': dict(Counter(row['reason'] for row in manifest['excluded'])),
    'deduplication': manifest['deduplication'],
    'manifest_sha256': hashlib.sha256((prepared / 'manifest.json').read_bytes()).hexdigest(),
    'reported_collection_region': manifest['reported_collection_region'],
    'regional_validation_complete': False, 'paired_with_yield_rows': False,
    'training_started': False,
    'limitation': manifest['limitation'],
}
target = ROOT / 'APP/training/images/dataset_inventory.json'
target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
print(json.dumps(report, indent=2))
