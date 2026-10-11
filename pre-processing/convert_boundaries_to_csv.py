"""Convert GADM ZIP to district and ordered boundary-vertex CSVs; verify all values."""
import csv
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def convert(folder):
    with zipfile.ZipFile(folder / 'india_districts.geojson.zip') as archive:
        with archive.open(next(n for n in archive.namelist() if n.endswith('.json'))) as handle:
            features = json.load(handle)['features']
    properties = list(features[0]['properties'])
    districts, expected = [], []
    for feature in features:
        props, geometry = feature['properties'], feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        points = []
        for pi, polygon in enumerate(polygons):
            for ri, ring in enumerate(polygon):
                for vi, point in enumerate(ring):
                    assert len(point) == 2
                    expected.append([props['GID_2'], pi, ri, vi, *point])
                    points.append(point)
        districts.append({**props, 'GEOMETRY_TYPE': geometry['type'],
                          'CENTROID_X': sum(p[0] for p in points) / len(points),
                          'CENTROID_Y': sum(p[1] for p in points) / len(points),
                          'VERTEX_COUNT': len(points)})
    for filename, rows, fields in [
        ('india_districts.csv', districts, properties + ['GEOMETRY_TYPE','CENTROID_X','CENTROID_Y','VERTEX_COUNT']),
        ('boundary_coordinates.csv', expected, ['GID_2','POLYGON_INDEX','RING_INDEX','VERTEX_INDEX','LONGITUDE','LATITUDE'])]:
        with (folder / filename).open('w', newline='', encoding='utf-8') as handle:
            if filename == 'india_districts.csv':
                writer = csv.DictWriter(handle, fieldnames=fields)
                writer.writeheader(); writer.writerows(rows)
            else:
                writer = csv.writer(handle); writer.writerow(fields); writer.writerows(rows)
        with (folder / filename).open(newline='', encoding='utf-8') as handle:
            reader = csv.reader(handle)
            assert next(reader) == fields
            for row in rows:
                values = [row[k] for k in fields] if isinstance(row, dict) else row
                assert next(reader) == [str(v) for v in values]
            assert next(reader, None) is None
    print(f'Verified {len(districts)} districts and {len(expected):,} boundary vertices')

if __name__ == '__main__':
    convert(ROOT / 'DATASET/raw/boundaries')
