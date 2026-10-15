"""Read-only sample-size and persistence-baseline audit. No main model training."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATES = {'Andhra Pradesh','Karnataka','Tamil Nadu','Telangana','Kerala','Puducherry'}

def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        yield from csv.DictReader(stream)

def audit():
    master=list(rows(ROOT/'DATASET/merged/rice_master.csv'))
    train=[r for r in master if int(r['FYEAR'])<=2015]
    latest={}
    for row in sorted(train,key=lambda r:int(r['FYEAR'])):
        latest[row['IDREGION'],row['SEASON']]=float(row['YIELD'])
    fallback=sum(float(r['YIELD']) for r in train)/len(train)
    baselines={}
    for name,years in [('validation',{2016,2017}),('test',{2018,2019})]:
        sample=[r for r in master if int(r['FYEAR']) in years]
        actual=[float(r['YIELD']) for r in sample]
        predictions=[latest.get((r['IDREGION'],r['SEASON']),fallback) for r in sample]
        errors=[p-y for p,y in zip(predictions,actual)]
        mean=sum(actual)/len(actual)
        sse=sum(e*e for e in errors);sst=sum((y-mean)**2 for y in actual)
        baselines[name]={'rows':len(sample),'MAE_t_per_ha':sum(abs(e) for e in errors)/len(errors),
            'RMSE_t_per_ha':math.sqrt(sse/len(errors)),'R2':1-sse/sst,
            'fallback_rows':sum((r['IDREGION'],r['SEASON']) not in latest for r in sample)}
    raw_counts=Counter();raw_years=defaultdict(set);raw_keys=defaultdict(set)
    for r in rows(ROOT/'DATASET/raw/government/crop_statistics.csv'):
        state=r['State'].strip()
        if state not in STATES or r['Crop'].strip().lower() not in {'rice','paddy'}:continue
        try:
            area=float(r['Area ']);production=float(r['Production']);year=int(r['Crop_Year'])
        except (ValueError,TypeError):continue
        if not math.isfinite(area) or not math.isfinite(production) or area<=0 or production<0:continue
        raw_counts[state]+=1;raw_years[state].add(year);raw_keys[state].add((r['District '].strip(),year,r['Season'].strip()))
    weather_regions={r['IDREGION'] for r in rows(ROOT/'DATASET/raw/weather/daily_weather.csv')}
    metadata=json.loads((ROOT/'DATASET/augmented/generation_manifest.json').read_text())
    by_district=Counter(r['IDREGION'] for r in master)
    return {'source_rows':len(master),'source_training_rows':len(train),'source_geographic_districts':len({(r['CENTROID_X'],r['CENTROID_Y']) for r in master}),
        'augmented_rows':metadata['total_rows'],'estimated_rows':metadata['added_rows'],
        'estimated_row_fraction':metadata['added_rows']/metadata['total_rows'],
        'standard_predictors':28,'dae_predictors':16,'target':'YIELD','units':'tonnes/hectare',
        'baseline':'Latest original training yield for district/season through 2015; training global mean fallback. No estimated rows used.',
        'baseline_results':baselines,'raw_rice_candidates':{state:{'rows':raw_counts[state],'unique_keys':len(raw_keys[state]),'years':[min(raw_years[state]),max(raw_years[state])]} for state in sorted(STATES)},
        'raw_weather_regions':sorted(weather_regions),
        'assessment':'Row count alone cannot establish accuracy. Estimated rows are dependent on source training rows. More genuine matched labels/weather and geographic evaluation are needed before claiming all-district performance.'}

if __name__=='__main__':
    print(json.dumps(audit(),indent=2))
