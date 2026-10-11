"""Rebuild the single master CSV from the three preserved raw sources.

Intermediate join tables exist only inside a TemporaryDirectory; users manage
only raw/, merged/ and training/. No simulated observations are added.
"""
from __future__ import annotations
import argparse
import csv
import math
import re
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

STATES = ('Andhra Pradesh', 'Karnataka', 'Tamil Nadu', 'Telangana')
ROOT = Path(__file__).resolve().parents[1]

def key(value):
    return re.sub(r'[^A-Z0-9]', '', ' '.join(value.strip().upper().replace('&','AND').split()))

def write_csv(path, rows):
    if not rows:
        raise ValueError(f'No rows available for {path.name}')
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dataset-dir',type=Path,default=ROOT/'DATASET')
    args=ap.parse_args(); raw=args.dataset_dir/'raw'; merged=args.dataset_dir/'merged'
    merged.mkdir(parents=True,exist_ok=True)
    source=[]
    with (raw/'government/crop_statistics.csv').open(newline='',encoding='utf-8-sig') as f:
        for row in csv.DictReader(f):
            state=row['State'].strip()
            if state not in STATES: continue
            try:
                area=float(row['Area ']); production=float(row['Production']); year=int(row['Crop_Year'])
            except (ValueError,TypeError): continue
            if not math.isfinite(area) or not math.isfinite(production) or area<=0 or production<0: continue
            source.append(dict(STATE=state,DISTRICT=row['District '].strip(),CROP=row['Crop'].strip(),
                               FYEAR=year,SEASON=row['Season'].strip(),CROP_AREA_HA=area,PRODUCTION_TONNES=production))
    source.sort(key=lambda r:(r['STATE'],r['DISTRICT'],r['CROP'],r['FYEAR'],r['SEASON']))
    with (raw/'boundaries/india_districts.csv').open(newline='',encoding='utf-8-sig') as f:
        boundaries=list(csv.DictReader(f))
    state_keys={key(s):s for s in STATES}; gadm={}; district_keys=defaultdict(list)
    for props in boundaries:
        state=state_keys.get(key(props.get('NAME_1',''))); district=props.get('NAME_2')
        if state not in STATES or not district: continue
        gadm[(state,key(district))]=(district,float(props['CENTROID_X']),float(props['CENTROID_Y']))
    for state,district_key in gadm: district_keys[district_key].append((state,district_key))
    centroids=[]
    for state,district in sorted({(r['STATE'],r['DISTRICT']) for r in source}):
        match=gadm.get((state,key(district))); status='exact_normalised'
        if not match and len(district_keys[key(district)])==1:
            match=gadm[district_keys[key(district)][0]]; status='historical_state_crosswalk'
        if match:
            name,lon,lat=match
            centroids.append(dict(IDREGION=f'IND_{key(state)}_{key(district)}',STATE=state,DISTRICT=district,
                                  GADM_DISTRICT=name,CENTROID_X=round(lon,6),CENTROID_Y=round(lat,6),MATCH_STATUS=status))
    rice=[r for r in source if r['CROP'].strip().lower() in {'rice','paddy'}]
    totals=defaultdict(float)
    for r in rice: totals[(r['STATE'],r['FYEAR'],r['SEASON'])]+=r['CROP_AREA_HA']
    labels=[]; areas=[]; fractions=[]
    for r in rice:
        region=f"IND_{key(r['STATE'])}_{key(r['DISTRICT'])}"
        context=dict(IDREGION=region,FYEAR=r['FYEAR'],SEASON=r['SEASON'])
        labels.append(dict(CROP='Rice',**context,YIELD=round(r['PRODUCTION_TONNES']/r['CROP_AREA_HA'],6),PRODUCTION_TONNES=r['PRODUCTION_TONNES']))
        areas.append(dict(CROP_ID='Rice',**context,CROP_AREA=r['CROP_AREA_HA']))
        fractions.append(dict(CROP_ID='Rice',**context,FRACTION=round(r['CROP_AREA_HA']/totals[(r['STATE'],r['FYEAR'],r['SEASON'])],8)))
    with tempfile.TemporaryDirectory(prefix='rice-join-') as temp:
        stage=Path(temp)
        for filename,rows in [('YIELD_NUTS2_SOUTH_INDIA_RICE.csv',labels),('CROP_AREA_NUTS2_SOUTH_INDIA_RICE.csv',areas),
                              ('AREA_FRACTIONS_NUTS2_SOUTH_INDIA_RICE.csv',fractions),('CENTROIDS_NUTS2_SOUTH_INDIA.csv',centroids)]:
            write_csv(stage/filename,rows)
        # A read-only hard link avoids copying the 57 MB weather extract.
        weather_stage=stage/'METEO_DAILY_NUTS2_SOUTH_INDIA.csv'
        try:
            weather_stage.hardlink_to(raw/'weather/daily_weather.csv')
        except OSError:
            shutil.copy2(raw/'weather/daily_weather.csv',weather_stage)
        subprocess.run([sys.executable,str(Path(__file__).parent/'internal/merge_seasonal.py'),
                        '--data-dir',str(stage),'--output-dir',str(merged)],check=True)
        generated=merged/'south_india_rice_master_training.csv'
        destination=merged/'rice_master.csv'
        if destination.exists() and generated.read_bytes()==destination.read_bytes():
            generated.unlink()
        else:
            generated.replace(destination)
    print(f"Sources: 3 | valid four-state crop rows: {len(source)} | rice labels: {len(labels)}")

if __name__=='__main__': main()
