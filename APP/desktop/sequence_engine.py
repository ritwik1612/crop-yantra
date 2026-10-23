"""CNN-LSTM seasonal scenarios; no tree or synthetic label training fallback."""
import json
import math
from datetime import datetime, timedelta, timezone
import numpy as np


class SequenceYield:
    def __init__(self,directory):
        self.directory=directory
        self.config=json.loads((directory/'sequence-config.json').read_text(encoding='utf-8'))
        self.references=json.loads((directory/'sequence-references.json').read_text(encoding='utf-8'))
        import onnxruntime as ort
        options=ort.SessionOptions();options.intra_op_num_threads=2
        self.session=ort.InferenceSession(str(directory/'yield-sequence.onnx'),options,providers=['CPUExecutionProvider'])

    def predict(self,request):
        try:
            cfg=self.config
            if 'year' in request or 'month' in request:raise ValueError('Select a season, not a separate year or month.')
            def number(name,lo,hi,default=None):
                value=request.get(name,default)
                if isinstance(value,bool):raise ValueError(f'Invalid {name}.')
                value=float(value)
                if not math.isfinite(value) or not lo<=value<=hi:raise ValueError(f'{name} must be between {lo} and {hi}.')
                return value
            area=number('areaHa',.01,1e6);land=number('landAreaHa',.01,1e6,area)
            if area>land:raise ValueError('Rice-planted area cannot exceed total land size.')
            temp=number('averageTemperatureC',10,40)
            ref=self.references.get(str(request['districtId'])+'|'+str(request['season']))
            if ref is None:raise ValueError('This location/season has no supported sequence reference.')
            channels=cfg['weather_channels'];w=np.array(ref['weather'],dtype=np.float64)
            idx={name:i for i,name in enumerate(channels)};days=w[:,idx['BIN_DAY_COUNT']]
            window_days=float(days.sum())
            weights=days/window_days
            shift=temp-float(weights@w[:,idx['TAVG']])
            for c in ['TMAX','TMIN','TAVG']:w[:,idx[c]]+=shift
            supplied={'averageTemperatureC':temp}
            specs=[('seasonalRainfallMm',0,10000),('relativeHumidityPct',0,100),
                   ('windSpeedMps',0,30),('solarRadiationKwhM2Day',0,12)]
            for name,lo,hi in specs:
                if request.get(name) in ('',None):continue
                value=number(name,lo,hi);supplied[name]=value
                if name=='seasonalRainfallMm':
                    total=value*window_days/ref['season_days']
                    previous=w[:,idx['PREC']].sum()
                    w[:,idx['PREC']]=w[:,idx['PREC']]*total/previous if previous>0 else total*weights
                elif name=='relativeHumidityPct':w[:,idx['RELH']]=np.clip(w[:,idx['RELH']]+value-weights@w[:,idx['RELH']],0,100)
                elif name=='windSpeedMps':w[:,idx['WSPD']]=value
                else:w[:,idx['RAD']]=value*days
            w[:,idx['VPRES']]=6.108*np.exp(17.27*w[:,idx['TAVG']]/(w[:,idx['TAVG']]+237.3))*w[:,idx['RELH']]/100
            static_names=cfg['static_features']
            static=np.array(ref['coordinates']+[float(name=='STATE_'+ref['state']) for name in static_names[2:6]]+
                            [float(name=='SEASON_'+request['season']) for name in static_names[6:]],dtype=np.float32)
            static[:2]=(static[:2]-cfg['coordinate_mean'])/cfg['coordinate_scale']
            scaled=(w-cfg['weather_mean'])/cfg['weather_scale']
            padded=np.zeros((cfg['max_steps'],len(channels)),dtype=np.float32)
            padded[:len(w)]=scaled
            groups=[(c,'weather',[i]) for i,c in enumerate(channels) if c!='BIN_DAY_COUNT']
            groups += [('LOCATION','static',[0,1]),('STATE','static',list(range(2,6))),
                       ('SEASON','static',list(range(6,11)))]
            weather_batch=[padded.copy()];static_batch=[static.copy()]
            for name,branch,indexes in groups:
                v=padded.copy();s=static.copy()
                if branch=='weather':v[:len(w),indexes]=0
                else:
                    s[indexes]=0
                    if name in ['STATE','SEASON']:
                        s[static_names.index(name+'_'+cfg['category_reference'][name])]=1
                weather_batch.append(v);static_batch.append(s)
            outputs=self.session.run(None,{'weather':np.stack(weather_batch),
                'lengths':np.full(len(weather_batch),len(w),dtype=np.int64),
                'static':np.stack(static_batch)})
            output=outputs[0]
            prediction=float(output[0])
            if not math.isfinite(prediction) or prediction<0:raise ValueError('The neural model returned an invalid estimate for these inputs.')
            effects=sorted([{'feature':g[0],'contribution':float(prediction-value)}
                            for g,value in zip(groups,output[1:])],key=lambda x:abs(x['contribution']),reverse=True)
            now=datetime.now(timezone(timedelta(hours=5,minutes=30)))
            warnings=['Current-season scenario uses assumed weather and training-only sequence references, not current observed daily weather. Test scores do not validate this scenario.']
            if ref['kind']=='synthetic_neighbour_transfer':warnings.append('Weather reference transferred from nearby training districts; accuracy in this district is unmeasured. No synthetic yield labels were used to train CNN–LSTM.')
            sequence_rows=[]
            for i,row in enumerate(w):
                sequence_rows.append({'step':i+1,'startDay':int(days[:i].sum())+1,'endDay':int(days[:i+1].sum()),
                                      'raw':row.tolist(),'scaled':scaled[i].tolist()})
            return {'ok':True,'version':'0.7.0','model':cfg['model'],'modelKind':'cnn_lstm',
                    'scope':'current_season_scenario','yieldTPerHa':prediction,'productionTonnes':prediction*area,
                    'areaHa':area,'landAreaHa':land,'sourceState':ref['state'],'district':ref['district'],
                    'season':request['season'],'predictionDate':now.date().isoformat(),
                    'averageTemperatureC':temp,'observedYield':None,'split':'scenario',
                    'referenceYears':ref['years'],'referenceCount':len(ref['years']),
                    'referenceKind':ref['kind'],'neighbourDonors':ref['donors'],'suppliedWeather':supplied,
                    'warnings':warnings,'testMetrics':cfg['test'],'testMetricsApplyToThisForecast':False,
                    'baseline':None,'explanationMethod':'sequence_reference_occlusion_sensitivity',
                    'contributions':effects,'normalizedNetworkOutput':(prediction-cfg['target_mean'])/cfg['target_scale'],
                    'networkConfiguration':{'target_mean':cfg['target_mean'],'target_scale':cfg['target_scale'],
                                            'architecture':cfg['architecture'],'best_epoch':cfg['best_epoch']},
                    'networkTrace':{'normalizedOutput':float(outputs[1][0]),
                        'firstConvolutionFeatures':outputs[6][0,:len(w)].tolist(),
                        'convolutionFeatures':outputs[2][0,:len(w)].tolist(),
                        'lstmStates':outputs[3][0,:len(w)].tolist(),
                        'joined':outputs[4][0].tolist(),'dense':outputs[5][0].tolist()},
                    'sequence':{'channels':channels,'steps':len(w),'maxSteps':cfg['max_steps'],
                        'windowDays':window_days,'seasonDays':ref['season_days'],'leadDays':cfg['lead_days'],
                        'rows':sequence_rows,'staticFeatures':[{'name':name,'value':float(v)} for name,v in zip(static_names,static)]},
                    'features':[],'encodedCategories':{},
                    'temperatureMethod':'Shift all reference-window temperature bins together. Rainfall is allocated by observed-window/season-day fraction; no future weather is supplied.'}
        except (KeyError,TypeError,ValueError,OverflowError) as error:
            return {'ok':False,'error':str(error) if isinstance(error,ValueError) else 'Invalid prediction inputs.'}
