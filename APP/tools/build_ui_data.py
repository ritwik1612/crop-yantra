"""Render preserved GADM rings for the UI; never change sources or train models."""
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'OTHER/runtime_dependencies'))
from shapely.geometry import Polygon
from shapely.ops import unary_union
from shapely import make_valid
STATES = {'AndhraPradesh': 'Andhra Pradesh', 'Karnataka': 'Karnataka',
          'TamilNadu': 'Tamil Nadu', 'Telangana': 'Telangana',
          'Kerala': 'Kerala', 'Puducherry': 'Puducherry'}

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as handle:
        return list(csv.DictReader(handle))

def main():
    districts = {r['GID_2']: r for r in read(ROOT/'DATASET/raw/boundaries/india_districts.csv') if r['NAME_1'] in STATES}
    rings = defaultdict(lambda: defaultdict(list))
    for r in read(ROOT/'DATASET/raw/boundaries/boundary_coordinates.csv'):
        if r['GID_2'] in districts:
            rings[r['GID_2']][(int(r['POLYGON_INDEX']), int(r['RING_INDEX']))].append(
                (int(r['VERTEX_INDEX']), float(r['LONGITUDE']), float(r['LATITUDE'])))
    observed = defaultdict(list)
    for r in read(ROOT/'DATASET/merged/rice_master.csv'):
        observed[(round(float(r['CENTROID_X']), 6), round(float(r['CENTROID_Y']), 6))].append(r)
    features, lookup, state_polygons = [], {}, defaultdict(list)
    for gid, props in districts.items():
        records = observed.get((round(float(props['CENTROID_X']), 6), round(float(props['CENTROID_Y']), 6)), [])
        paths = []
        for ring in rings[gid].values():
            points = [(round((lon-74)*88, 2), round((20-lat)*86, 2)) for _, lon, lat in sorted(ring)]
            paths.append('M'+'L'.join(f'{x},{y}' for x,y in points)+'Z')
        polygons = defaultdict(dict)
        for (polygon_index,ring_index),ring in rings[gid].items():
            polygons[polygon_index][ring_index]=[(lon,lat) for _,lon,lat in sorted(ring)]
        for polygon in polygons.values():
            state_polygons[STATES[props['NAME_1']]].append(make_valid(Polygon(polygon[0],[points for index,points in sorted(polygon.items()) if index!=0])))
        features.append({'id':gid, 'name':props['NAME_2'], 'state':STATES[props['NAME_1']],
                         'x':round((float(props['CENTROID_X'])-74)*88,2),
                         'y':round((20-float(props['CENTROID_Y']))*86,2),
                         'path':''.join(paths), 'records':len(records),
                         'years':sorted({int(r['FYEAR']) for r in records}),
                         'historicalStates':sorted({r['STATE'] for r in records})})
        lookup[gid] = [{k:(r[k] if k in {'STATE','DISTRICT','SEASON'} else float(r[k]))
                        for k in ['STATE','DISTRICT','FYEAR','SEASON','YIELD','CROP_AREA','TAVG_MEAN','PREC_TOTAL','GDD_BASE10']}
                       for r in records]
    state_shapes={}
    for state,polygons in state_polygons.items():
        dissolved=unary_union(polygons)
        pieces=[dissolved] if dissolved.geom_type=='Polygon' else list(dissolved.geoms)
        state_paths=[]
        for piece in pieces:
            if piece.geom_type!='Polygon': continue
            for ring in [piece.exterior,*piece.interiors]:
                state_paths.append('M'+'L'.join(f'{(lon-74)*88:.2f},{(20-lat)*86:.2f}' for lon,lat in ring.coords)+'Z')
        state_shapes[state]=''.join(state_paths)
    data = {'source':'GADM 4.1 level 2; converted project boundary CSVs',
            'boundaryVintage':'GADM 4.1 (not a current district registry)',
            'districts':sorted(features,key=lambda f:(f['state'],f['name'])), 'history':lookup, 'stateShapes':state_shapes,
            'manifest':json.loads((ROOT/'DATASET/training/manifest.json').read_text())}
    assert all(f['path'] for f in features)
    (ROOT/'APP/prototype/data.js').write_text('window.RYP_DATA = '+json.dumps(data,separators=(',',':'))+';\n',encoding='utf-8')
    print(f'{len(features)} selectable districts; {sum(bool(f["records"]) for f in features)} with historical rows. No datasets modified.')

if __name__=='__main__': main()
