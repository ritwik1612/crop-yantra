"""Train a separate coverage model using train-only geographic pseudo-labels.

Does not overwrite measured data, its model, or measured evaluation splits.
Synthetic records are deterministic weighted combinations, never observations.
"""
import copy
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from APP.training.train import metrics


def distance(a,b):
    lat1,lat2=map(math.radians,(a['CENTROID_Y'],b['CENTROID_Y']))
    dlat=lat2-lat1;dlon=math.radians(b['CENTROID_X']-a['CENTROID_X'])
    return 6371*2*math.asin(min(1,math.sqrt(math.sin(dlat/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2)))


def portable(tree):
    trees=[]
    for iteration in tree._predictors:
        for t in iteration:
            if t.nodes['is_categorical'].any():raise ValueError('Categorical tree unsupported')
            nodes=[[float(n['value']),int(n['feature_idx']),float(n['num_threshold']),int(n['left']),int(n['right']),bool(n['is_leaf']),bool(n['missing_go_to_left'])] for n in t.nodes]
            for i in reversed(range(len(nodes))):
                if not nodes[i][5]:
                    a,b=nodes[i][3:5];ca,cb=int(t.nodes[a]['count']),int(t.nodes[b]['count'])
                    nodes[i][0]=(nodes[a][0]*ca+nodes[b][0]*cb)/(ca+cb)
            trees.append(nodes)
    return {'baseline':float(tree._baseline_prediction[0,0]),'trees':trees}


def main():
    runtime=ROOT/'APP/prototype/runtime';out=ROOT/'DATASET/candidates/spatial_coverage'
    run=ROOT/'APP/training/runs/spatial_coverage_20261019'
    if (run/'bundle.json').exists():raise ValueError('Completed run exists; preserve it')
    source=ROOT/'DATASET/merged/rice_master.csv'
    prep=json.loads((runtime/'preprocessor.json').read_text())
    data_script=(ROOT/'APP/prototype/data.js').read_text(encoding='utf-8')
    catalog=json.loads(data_script.split('=',1)[1].strip().rstrip(';'))['districts']
    with (ROOT/'DATASET/raw/boundaries/india_districts.csv').open(newline='',encoding='utf-8') as f:
        boundaries={r['GID_2']:r for r in csv.DictReader(f)}
    with source.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f);columns=reader.fieldnames;rows=list(reader)
    numbers=set(prep['numeric'])|{'FYEAR','YIELD','PRODUCTION_TONNES'}
    for row in rows:
        for name in numbers:row[name]=float(row[name])
    train=[r for r in rows if r['FYEAR']<=2020]
    validation=[r for r in rows if 2021<=r['FYEAR']<=2022]
    test=[r for r in rows if 2023<=r['FYEAR']<=2024]
    known={(r['IDREGION'],r['SEASON']) for r in train}
    synthetic=[];references={}
    provenance_columns=['DATA_ORIGIN','DONOR_RECORD_KEYS','DONOR_DISTANCES_KM','DONOR_WEIGHTS','CROSS_STATE_TRANSFER']
    for district in catalog:
        boundary=boundaries[district['id']]
        target={'CENTROID_X':float(boundary['CENTROID_X']),'CENTROID_Y':float(boundary['CENTROID_Y'])}
        for season in prep['categories'][1]:
            if (district['id'],season) in known:continue
            candidates=[r for r in train if r['SEASON']==season]
            years=sorted({int(r['FYEAR']) for r in candidates})
            for year in years:
                available=[r for r in candidates if int(r['FYEAR'])==year]
                # Geographic proximity, not claimed administrative adjacency.
                donors=sorted(available,key=lambda r:(distance(target,r),r['IDREGION']))[:3]
                if len(donors)<3:continue
                distances=np.asarray([distance(target,r) for r in donors])
                weights=1/np.maximum(distances,10)**2;weights/=weights.sum()
                row=copy.deepcopy(donors[0])
                for name in numbers:row[name]=float(np.dot(weights,[r[name] for r in donors]))
                row.update(IDREGION=district['id'],STATE=district['state'],DISTRICT=district['name'],FYEAR=year,
                           MATCH_STATUS='synthetic_geographic_transfer',**target)
                row['CROP_AREA_LOG1P']=math.log1p(row['CROP_AREA'])
                row['TEMP_RANGE_MEAN']=row['TMAX_MEAN']-row['TMIN_MEAN']
                row['WATER_BALANCE_PROXY']=row['PREC_TOTAL']-row['ET0_TOTAL']
                row['RAIN_PER_GDD']=row['PREC_TOTAL']/row['GDD_BASE10'] if row['GDD_BASE10'] else 0
                row['RADIATION_PER_GDD']=row['RAD_TOTAL']/row['GDD_BASE10'] if row['GDD_BASE10'] else 0
                row['PRODUCTION_TONNES']=row['YIELD']*row['CROP_AREA']
                donors_meta=[{'district':r['DISTRICT'],'state':r['STATE'],'districtId':r['IDREGION'],'year':year,
                             'distanceKm':float(d),'weight':float(w)} for r,d,w in zip(donors,distances,weights)]
                row.update(DATA_ORIGIN='synthetic_neighbour_transfer',
                           DONOR_RECORD_KEYS=json.dumps([f"{r['IDREGION']}|{year}|{season}" for r in donors]),
                           DONOR_DISTANCES_KM=json.dumps(distances.tolist()),DONOR_WEIGHTS=json.dumps(weights.tolist()),
                           CROSS_STATE_TRANSFER=any(r['STATE']!=district['state'] for r in donors))
                synthetic.append(row)
                references.setdefault(district['id']+'|'+season,[]).append({'year':year,'numeric':[row[n] for n in prep['numeric']],
                    'state':district['state'],'district':district['name'],'observed':None,'split':'synthetic_reference','donors':donors_meta})
    def transform(records):
        result=[]
        for row in records:
            numeric=[(row[n]-prep['mean'][i])/prep['scale'][i] for i,n in enumerate(prep['numeric'])]
            categories=[float(row[name]==choice) for name,choices in zip(('STATE','SEASON'),prep['categories']) for choice in choices]
            result.append(numeric+categories)
        return np.asarray(result,dtype=np.float64)
    all_train=train+synthetic;x=transform(all_train);val_x=transform(validation)
    y=np.asarray([r['YIELD'] for r in all_train]);val_y=np.asarray([r['YIELD'] for r in validation])
    candidates=[]
    for weight in (.1,.25):
        for leaves in (7,15):
            model=HistGradientBoostingRegressor(max_leaf_nodes=leaves,max_iter=250,learning_rate=.04,
                l2_regularization=1,random_state=42,early_stopping=False)
            model.fit(x,y,sample_weight=np.r_[np.ones(len(train)),np.full(len(synthetic),weight)])
            score=metrics(val_y,model.predict(val_x))
            candidates.append((score['RMSE'],model,{'synthetic_weight':weight,'leaves':leaves,'validation':score}))
            print(json.dumps(candidates[-1][2]),flush=True)
    _,model,selected=min(candidates,key=lambda r:r[0])
    tree=portable(model)
    def predict(row):
        result=tree['baseline']
        for t in tree['trees']:
            i=0
            while not t[i][5]:i=t[i][3] if row[t[i][1]]<=t[i][2] else t[i][4]
            result+=t[i][0]
        return result
    np.testing.assert_allclose([predict(r) for r in x],model.predict(x),atol=1e-8)
    test_metrics=metrics(np.asarray([r['YIELD'] for r in test]),model.predict(transform(test)))
    # Keep measured splits and their trained default model untouched.
    out.mkdir(parents=True,exist_ok=True);run.mkdir(parents=True,exist_ok=True)
    with (out/'synthetic_train.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns+provenance_columns);writer.writeheader();writer.writerows(synthetic)
    with (out/'combined_train.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns+provenance_columns);writer.writeheader()
        for row in train:writer.writerow({**row,'DATA_ORIGIN':'measured_source'})
        writer.writerows(synthetic)
    bundle={'model_name':'Neighbour-augmented HistGradientBoostingRegressor','method':'Three nearest same-season, same-year training districts; inverse-square geographic distance with a 10 km floor',
        'source_master_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'donor_years_max':2020,
        'measured_train_rows':len(train),'synthetic_train_rows':len(synthetic),'coverage_pairs':len(references),
        'map_districts':len(catalog),'selection':selected,'search':[c[2] for c in candidates],
        'test':test_metrics,'test_scope':'Measured 2023–2024 rows only; NOT missing-district validation',
        'scope':'Synthetic geographic transfer. No measured local accuracy is established. Cross-state transfers may be required.',
        'preprocessor_sha256':hashlib.sha256((runtime/'preprocessor.json').read_bytes()).hexdigest()}
    (run/'bundle.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
    payload={'metadata':bundle,'model':tree,'references':references}
    (run/'spatial-coverage.json').write_text(json.dumps(payload,allow_nan=False,separators=(',',':')),encoding='utf-8')
    (runtime/'spatial-coverage.json').write_text(json.dumps(payload,allow_nan=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({k:v for k,v in bundle.items() if k!='search'},indent=2),flush=True)


if __name__=='__main__':main()
