"""Stage measured recent rice labels and matching NASA weather; never activate.

Agricultural year is the START year: Kharif June-November; Rabi November-April
across years. These are documented seasonal proxies, not observed sowing dates.
Old source labels are preserved; all candidate weather joins use this convention.
Unmatched district names are excluded, never filled using neighbouring labels.
"""
import concurrent.futures
import csv
import hashlib
import json
import math
import re
import time
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'DATASET'
OUT = DATA / 'candidates/recent_yield'
STATES = {'Andhra Pradesh', 'Karnataka', 'Tamil Nadu', 'Telangana'}
MONTHS = {'Kharif': {6,7,8,9,10,11}, 'Rabi': {11,12,1,2,3,4},
          'Summer': {3,4,5,6}, 'Autumn': {9,10,11,12}, 'Winter': {12,1,2,3}, 'Whole Year': set(range(1,13))}
PARAMS = {'TMAX':'T2M_MAX','TMIN':'T2M_MIN','TAVG':'T2M','RELH':'RH2M','WSPD':'WS2M',
          'PREC':'PRECTOTCORR','ET0':'EVLAND','RAD':'ALLSKY_SFC_SW_DWN','PS':'PS'}


def key(value):
    return re.sub('[^A-Z0-9]', '', str(value).upper())


def read(path):
    with path.open(newline='', encoding='utf-8-sig') as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def weather_request(item):
    gid, lon, lat, start, end = item
    cache = DATA / 'raw/weather/nasa_recent' / f'{gid}_{start}_{end}.json'
    cache.parent.mkdir(parents=True, exist_ok=True)
    url = 'https://power.larc.nasa.gov/api/temporal/daily/point?' + urllib.parse.urlencode({
        'parameters': ','.join(PARAMS.values()), 'community':'RE', 'longitude':lon, 'latitude':lat,
        'start':str(start)+'0101', 'end':str(end)+'1231', 'format':'JSON'})
    if cache.exists():
        blob = json.loads(cache.read_text(encoding='utf-8'))
    else:
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=100) as response:
                    blob = json.load(response)
                if not all(p in blob.get('properties', {}).get('parameter', {}) for p in PARAMS.values()):
                    raise ValueError('NASA response missing parameters')
                cache.write_text(json.dumps(blob), encoding='utf-8')
                break
            except Exception:
                if attempt == 2: raise
                time.sleep(2 + attempt * 2)
    print(f'Weather ready: {gid} {start}-{end}', flush=True)
    return item, blob


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    state_names = {key(s):s for s in STATES}
    boundaries = {(state_names[key(r['NAME_1'])], key(r['NAME_2'])): r for r in read(DATA/'raw/boundaries/india_districts.csv') if key(r['NAME_1']) in state_names}
    old = read(DATA/'raw/government/crop_statistics.csv')
    recent = read(DATA/'raw/government/upag/cropwise_area_production_yield.csv')
    labels, rejected = [], []
    for source, rows in [('original', old), ('upag', recent)]:
        for r in rows:
            if source == 'original':
                state, district, crop, year, season = r['State'], r['District '], r['Crop'], int(r['Crop_Year']), r['Season'].strip()
                av, pv = r['Area '], r['Production']
                if year > 2019 or year < 2001: continue
            else:
                state, district, crop, year, season = r['state_name'], r['district_name'], r['crop_name'], int(r['year'][:4]), r['season'].strip()
                av, pv = r['area'], r['production']
                if year <= 2019: continue
            if state not in STATES or crop.strip().lower() not in {'rice','paddy'} or season not in MONTHS: continue
            try: area, production = float(av), float(pv)
            except (ValueError, TypeError): continue
            if not all(math.isfinite(v) for v in (area, production)) or area <= 0 or production < 0: continue
            match = boundaries.get((state, key(district)))
            # Match only exact normalized same-state names. Do not transfer a
            # historic parent district's label onto a newly split child district.
            if not match:
                rejected.append({'state':state,'district':district,'year':year,'season':season,'reason':'no_same_state_exact_boundary_match'})
                continue
            labels.append({'CROP':'Rice','IDREGION':match['GID_2'],'STATE':state,'DISTRICT':key(match['NAME_2']),
                           'FYEAR':year,'SEASON':season,'YIELD':production/area,'PRODUCTION_TONNES':production,
                           'CROP_AREA':area,'CENTROID_X':float(match['CENTROID_X']),'CENTROID_Y':float(match['CENTROID_Y']),
                           'SOURCE':source,'MATCH_STATUS':'exact_normalised'})
    identifiers = [(r['IDREGION'],r['FYEAR'],r['SEASON']) for r in labels]
    if len(identifiers) != len(set(identifiers)): raise ValueError('Duplicate district/year/season labels')
    # Existing weather IDs are linked by coordinates, not by loose district names.
    coordinate_ids = {(round(float(r['CENTROID_X']),6),round(float(r['CENTROID_Y']),6)):r['IDREGION'] for r in read(DATA/'merged/rice_master.csv')}
    by_region = {r['IDREGION']:r for r in labels}
    requests = []
    for gid,r in by_region.items():
        known = (round(r['CENTROID_X'],6),round(r['CENTROID_Y'],6)) in coordinate_ids
        years = [x['FYEAR'] for x in labels if x['IDREGION']==gid]
        start, end = (2024 if known else min(years)), max(years)+1
        if start <= end:
            requests.append((gid,r['CENTROID_X'],r['CENTROID_Y'],start,end))
    # Only missing weather is downloaded; immutable original weather stays intact.
    weather = defaultdict(dict)
    old_to_new = {old_id:gid for gid,r in by_region.items()
                  if (old_id:=coordinate_ids.get((round(r['CENTROID_X'],6),round(r['CENTROID_Y'],6))))}
    for r in read(DATA/'raw/weather/daily_weather.csv'):
        gid = old_to_new.get(r['IDREGION'])
        if gid: weather[gid][r['DATE']] = {n:float(r[n]) for n in (*PARAMS,'VPRES')}
    print(f'{len(labels)} candidate labels, {len(by_region)} matched districts; fetching {len(requests)} weather locations', flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for item, blob in pool.map(weather_request, requests):
            gid = item[0]; params = blob['properties']['parameter']
            for day in params['T2M']:
                values = {name:params[param][day] for name,param in PARAMS.items()}
                if not all(isinstance(v,(float,int)) and math.isfinite(v) and v != -999 for v in values.values()): continue
                values['VPRES'] = 6.108 * math.exp(17.27*values['TAVG']/(values['TAVG']+237.3))*values['RELH']/100
                weather[gid][f'{day[:4]}-{day[4:6]}-{day[6:]}'] = values
    # Rebuild every candidate row using the same fiscal-start seasonal calendar.
    totals = defaultdict(float)
    for r in labels: totals[(r['STATE'],r['FYEAR'],r['SEASON'])] += r['CROP_AREA']
    output=[]
    for label in labels:
        year,season = label['FYEAR'],label['SEASON']; days=[]
        for text,values in weather[label['IDREGION']].items():
            d=date.fromisoformat(text)
            wanted_year = year+1 if season == 'Summer' or (season in {'Rabi','Winter'} and d.month <= 4) else year
            if d.year == wanted_year and d.month in MONTHS[season]: days.append(values)
        expected = sum(1 for day in range((date(year+2,1,1)-date(year,1,1)).days)
                       if (d:=date.fromordinal(date(year,1,1).toordinal()+day)).month in MONTHS[season]
                       and d.year == (year+1 if season == 'Summer' or (season in {'Rabi','Winter'} and d.month<=4) else year))
        if len(days) != expected:
            rejected.append({'state':label['STATE'],'district':label['DISTRICT'],'year':year,'season':season,'reason':f'incomplete_weather:{len(days)}/{expected}'})
            continue
        row = {k:v for k,v in label.items() if k!='SOURCE'}
        row['AREA_FRACTION'] = label['CROP_AREA']/totals[(label['STATE'],year,season)]
        row['WEATHER_DAY_COUNT']=len(days)
        means = {k:sum(d[k] for d in days)/len(days) for k in (*PARAMS,'VPRES')}
        for name in ('TMAX','TMIN','TAVG','VPRES','WSPD','RELH','PS'): row[name+'_MEAN']=means[name]
        for name in ('PREC','ET0','RAD'): row[name+'_TOTAL']=sum(d[name] for d in days)
        row['GDD_BASE10']=sum(max(d['TAVG']-10,0) for d in days)
        row['TEMP_RANGE_MEAN']=row['TMAX_MEAN']-row['TMIN_MEAN']
        row['WATER_BALANCE_PROXY']=row['PREC_TOTAL']-row['ET0_TOTAL']
        row['RAIN_PER_GDD']=row['PREC_TOTAL']/row['GDD_BASE10'] if row['GDD_BASE10'] else 0
        row['RADIATION_PER_GDD']=row['RAD_TOTAL']/row['GDD_BASE10'] if row['GDD_BASE10'] else 0
        row['CROP_AREA_LOG1P']=math.log1p(row['CROP_AREA'])
        output.append(row)
    output.sort(key=lambda r:(r['FYEAR'],r['STATE'],r['DISTRICT'],r['SEASON']))
    write(OUT/'rice_master.csv',output)
    if rejected: write(OUT/'excluded_rows.csv',rejected)
    manifest={'rows':len(output),'year_counts':dict(sorted(Counter(r['FYEAR'] for r in output).items())),
              'states':dict(Counter(r['STATE'] for r in output)), 'districts':len({r['IDREGION'] for r in output}),
              'calendar':'agricultural start year; Rabi Nov-Apr across boundary; Winter Dec-Mar across boundary; Summer Mar-Jun in following year',
              'season_windows':'proxies, not measured planting/harvest dates',
              'weather':'NASA POWER RE: EVLAND is land evaporation (not reference evapotranspiration), RAD kWh/m2/day; VPRES derived hPa',
              'label':'production tonnes / area hectares; reported UPAg yield kg/ha not directly used',
              'not_current_forecast_validation':True,'sha256':hashlib.sha256((OUT/'rice_master.csv').read_bytes()).hexdigest()}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest,indent=2),flush=True)


if __name__ == '__main__': main()
