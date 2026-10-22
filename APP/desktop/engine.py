"""Offline inference using exported, already-trained Paddy models."""
import base64
import io
import json
import math
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

Image.MAX_IMAGE_PIXELS = 24_000_000

class Engine:
    def __init__(self, directory):
        self.directory = Path(directory)
        def read(name):
            return json.loads((self.directory/name).read_text(encoding='utf8'))
        self.prep = read('preprocessor.json')
        self.history = read('historical.json')
        self.trees = read('yield.json')
        self.meta = read('metadata.json')
        coverage_path=self.directory/'spatial-coverage.json'
        self.coverage=read('spatial-coverage.json') if coverage_path.exists() else None
        self.session = None
        self.yield_session = None
        self.session_lock = threading.Lock()

    def status(self):
        return {'ok': True, 'version': self.meta['version'], 'offline': True,
                'yieldModel': self.meta['yield_model'], 'imageModel': self.meta['image_model'],
                'yieldConfiguration': self.meta.get('yield_mlp'),
                'yieldDefaultModel':self.meta.get('yield_default_model','mlp'),
                'yieldDataset':self.meta.get('yield_dataset'), 'yieldTest':self.meta.get('yield_test'),
                'yieldCoverage':self.coverage['metadata'] if self.coverage else None,
                'imageClasses': self.meta['classes'],
                'imageTest': {'accuracy':self.meta['image_test_accuracy'],'macro_F1':self.meta['image_test_macro_f1']}}

    def predict_yield(self, request, *, _row=None, _tree_model=None):
        try:
            area = float(request['areaHa'])
            year = int(request['year'])
            if isinstance(request['areaHa'], bool) or not math.isfinite(area) or not .01 <= area <= 1_000_000:
                raise ValueError('Enter an area between 0.01 and 1,000,000 hectares.')
            if str(year) != str(request['year']):
                raise ValueError('Crop year must be a whole number.')
            key = f"{request['districtId']}|{year}|{request['season']}"
            row = _row if _row is not None else self.history.get(key)
            if row is None:
                raise ValueError('No complete historical inputs for this district, season and year. Choose an available 2001–2019 record. No weather is invented.')
            raw = row['numeric']
            numeric = [(self.prep['median'][i] if v is None else v) for i,v in enumerate(raw)]
            scaled = [(v-self.prep['mean'][i])/self.prep['scale'][i] for i,v in enumerate(numeric)]
            categories = [row['state'], request['season']]
            x = scaled + [float(value == category) for value, choices in zip(categories, self.prep['categories']) for category in choices]
            if not all(math.isfinite(v) for v in x):
                raise ValueError('Historical inputs contain invalid values.')
            contributions = np.zeros(len(x))
            tree_model=self.trees if _tree_model is None else _tree_model
            prediction = tree_model['baseline']
            root_offset = 0.0
            path_counts = np.zeros(len(x),dtype=int)
            path_example = None
            for tree_number,tree in enumerate(tree_model['trees'],start=1):
                index = 0
                steps = []
                root_offset += tree[0][0]
                while not tree[index][5]:
                    node = tree[index]
                    child = node[3] if x[node[1]] <= node[2] else node[4]
                    change = tree[child][0]-node[0]
                    contributions[node[1]] += change
                    path_counts[node[1]] += 1
                    steps.append({'feature':self.prep['predictors'][node[1]].replace('numeric__','').replace('categorical__',''),
                                  'input':float(x[node[1]]),'threshold':float(node[2]),
                                  'branch':'left (≤)' if child==node[3] else 'right (>)',
                                  'before':float(node[0]),'after':float(tree[child][0]),'change':float(change)})
                    index = child
                prediction += tree[index][0]
                if path_example is None or (not any(v['feature'].startswith('STATE_') for v in path_example['steps']) and any(v['feature'].startswith('STATE_') for v in steps)):
                    path_example={'tree':tree_number,'rootValue':float(tree[0][0]),'leafValue':float(tree[index][0]),'steps':steps}
            if prediction < 0 or not math.isfinite(prediction):
                raise ValueError('Model returned an invalid yield estimate.')
            baseline = tree_model['baseline'] + root_offset
            assert abs(baseline+sum(contributions)-prediction) < 1e-8
            kind = request.get('proposedModel', 'gbdt')
            if kind not in ('mlp', 'gbdt'):
                raise ValueError('Choose MLP or HistGradientBoostingRegressor.')
            explanation = 'tree_path_contributions'
            model_name = self.meta['yield_model']
            test_metrics = self.meta['yield_test']
            network_output = None
            if kind == 'mlp':
                with self.session_lock:
                    if self.yield_session is None:
                        import onnxruntime as ort
                        options = ort.SessionOptions()
                        options.intra_op_num_threads = 1
                        self.yield_session = ort.InferenceSession(str(self.directory/'yield-mlp.onnx'), options,
                                                                 providers=['CPUExecutionProvider'])
                # Occlude one numerical feature or an entire categorical group
                # to its training reference. Effects are NOT additive attribution.
                inputs = np.asarray(x, dtype=np.float32)
                config = self.meta['yield_mlp']
                context = config.get('model_kind') == 'contextual_mlp'
                district_index = 0
                if context:
                    context_key = row['state']+'|'+row['district']
                    if config.get('season_context'):context_key += '|'+request['season']
                    district_index = config['district_vocabulary'].get(context_key,0)
                    scaled_year=(year-config['year_mean'])/config['year_scale'] if config.get('use_year_trend',True) else 0
                    inputs = np.append(inputs,[scaled_year,district_index]).astype(np.float32)
                batches = [inputs.copy()]
                groups = [(name.replace('numeric__',''), [i]) for i,name in enumerate(self.prep['predictors'][:len(numeric)])]
                offset = len(numeric)
                for name, choices in zip(('STATE','SEASON'), self.prep['categories']):
                    # Use the observed training-mode category, avoiding invalid
                    # fractional one-hot vectors in the occlusion reference.
                    indexes = list(range(offset, offset+len(choices)))
                    groups.append((name, indexes))
                    offset += len(choices)
                if context:
                    groups += [('CROP_YEAR',[len(x)]),('DISTRICT_CONTEXT',[len(x)+1])]
                for name,indexes in groups:
                    variant = inputs.copy()
                    variant[indexes] = 0
                    if name in ('STATE','SEASON'):
                        category_index = 0 if name == 'STATE' else 1
                        reference = self.meta['yield_mlp']['category_reference'][name]
                        variant[indexes[self.prep['categories'][category_index].index(reference)]] = 1
                        if context and name == 'SEASON' and config.get('season_context'):
                            variant[len(x)+1] = config['district_vocabulary'].get(row['state']+'|'+row['district']+'|'+reference,0)
                    batches.append(variant)
                outputs = self.yield_session.run(None, {'features': np.stack(batches)})[0]
                prediction = float(outputs[0])
                contributions = [float(prediction-value) for value in outputs[1:]]
                influence = sorted([{'feature': name, 'contribution': value} for (name,_),value in zip(groups,contributions)],
                                   key=lambda r: abs(r['contribution']), reverse=True)
                explanation = 'reference_occlusion_sensitivity'
                model_name = config['model']
                test_metrics = self.meta['yield_mlp']['test']
                network_output = (prediction-self.meta['yield_mlp']['target_mean'])/self.meta['yield_mlp']['target_scale']
                baseline = None
                if prediction < 0 or not math.isfinite(prediction):
                    raise ValueError('Neural network returned an invalid yield estimate.')
            feature_rows = [{'name': name, 'raw': value, 'imputed': numeric[i], 'scaled': scaled[i]}
                            for i,(name,value) in enumerate(zip(self.prep['numeric'],raw))]
            if kind == 'gbdt':
                influence = sorted([{'feature': name.replace('numeric__','').replace('categorical__',''),
                                 'contribution': float(value)} for name,value in zip(self.prep['predictors'],contributions)],
                               key=lambda r: abs(r['contribution']), reverse=True)
            state_audit = []
            if kind == 'gbdt':
                for i,name in enumerate(self.prep['predictors']):
                    if not name.startswith('categorical__STATE_'):continue
                    state_audit.append({'state':name.removeprefix('categorical__STATE_'),'input':float(x[i]),
                                        'contribution':float(contributions[i]),'pathSplits':int(path_counts[i]),
                                        'modelSplits':sum(1 for tree in tree_model['trees'] for node in tree if not node[5] and node[1]==i)})
            warnings = []
            if request['season'] not in self.prep['categories'][1]:
                warnings.append('Season not seen while fitting preprocessing; its one-hot indicators are all zero.')
            if row['split'] != 'test':
                warnings.append(f"This record belongs to the {row['split']} split, not the independent test split.")
            if kind == 'mlp' and context and district_index == 0:
                warnings.append('District context was unseen during training; the reference embedding is used. Spatial transfer is not validated.')
            return {'ok': True, 'model': model_name, 'modelKind': kind, 'version': self.meta['version'],
                    'yieldTPerHa': prediction, 'productionTonnes': prediction*area,
                    'areaHa': area, 'observedYield': row['observed'], 'split': row['split'],
                    'sourceState': row['state'], 'district': row['district'], 'year': year,
                    'season': request['season'], 'features': feature_rows,
                    'encodedCategories': dict(zip(self.prep['predictors'][len(numeric):],x[len(numeric):])),
                    'baseline': baseline, 'contributions': influence, 'warnings': warnings,
                    'stateEncodingAudit':state_audit,'treePathExample':path_example if kind=='gbdt' else None,
                    'explanationMethod': explanation, 'normalizedNetworkOutput': network_output,
                    'networkConfiguration': self.meta.get('yield_mlp') if kind == 'mlp' else None,
                    'contextInputs': {'year': year, 'district_index': district_index,
                        'scaled_year': float(inputs[len(x)])} if kind == 'mlp' and context else None,
                    'testMetrics': test_metrics, 'scope': 'historical_district_estimate'}
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            return {'ok': False, 'error': str(error) if isinstance(error, ValueError) else 'Invalid prediction inputs.'}

    def predict_seasonal_yield(self, request):
        """Current-season what-if inference; never relabel a historic record.

        Only training-split covariates form the default seasonal reference.
        User temperature is a scenario assumption, not a measured weather feed.
        The result is explicitly outside retrospective test validation.
        """
        try:
            if 'year' in request or 'month' in request:
                raise ValueError('Select a season; separate year/month inputs are not supported.')
            rice_area=float(request['areaHa'])
            land_area=float(request.get('landAreaHa',rice_area))
            if isinstance(request.get('landAreaHa'),bool) or not math.isfinite(land_area) or not .01<=land_area<=1_000_000:
                raise ValueError('Total land size must be between 0.01 and 1,000,000 hectares.')
            if rice_area>land_area:
                raise ValueError('Rice-planted area cannot exceed total land size.')
            temperature = float(request['averageTemperatureC'])
            if isinstance(request['averageTemperatureC'],bool) or not math.isfinite(temperature) or not 10 <= temperature <= 40:
                raise ValueError('Average seasonal temperature must be between 10 and 40 °C.')
            season = request['season']
            if season not in self.prep['categories'][1]:
                raise ValueError('This season is not supported by the trained yield model.')
            prefix = str(request['districtId'])+'|'
            references = [(k,r) for k,r in self.history.items()
                          if k.startswith(prefix) and k.endswith('|'+season) and r['split']=='train']
            spatial=False
            if not references:
                stored=self.coverage['references'].get(str(request['districtId'])+'|'+season,[]) if self.coverage else []
                references=[(prefix+str(r['year'])+'|'+season,r) for r in stored]
                spatial=bool(references)
            if not references:
                raise ValueError('This location is not in the supported map coverage.')
            values = np.asarray([r['numeric'] for _,r in references],dtype=np.float64)
            raw = np.nanmedian(values,axis=0).tolist()
            fields = dict(zip(self.prep['numeric'],raw))
            shift = temperature-fields['TAVG_MEAN']
            fields['TAVG_MEAN'] = temperature
            fields['TMAX_MEAN'] += shift
            fields['TMIN_MEAN'] += shift
            supplied={'averageTemperatureC':temperature}
            optional_specs=[('seasonalRainfallMm','PREC_TOTAL',0,10000),('relativeHumidityPct','RELH_MEAN',0,100),
                            ('windSpeedMps','WSPD_MEAN',0,30),('solarRadiationKwhM2Day','RAD_TOTAL',0,12)]
            for name,feature,lower,upper in optional_specs:
                value=request.get(name)
                if value is None or value=='':continue
                number=float(value)
                if isinstance(value,bool) or not math.isfinite(number) or not lower<=number<=upper:
                    raise ValueError(f'{name} must be between {lower} and {upper}.')
                fields[feature]=number*fields['WEATHER_DAY_COUNT'] if name=='solarRadiationKwhM2Day' else number
                supplied[name]=number
            fields['VPRES_MEAN'] = 6.108*math.exp(17.27*temperature/(temperature+237.3))*fields['RELH_MEAN']/100
            fields['GDD_BASE10'] = max(temperature-10,0)*fields['WEATHER_DAY_COUNT']
            fields['TEMP_RANGE_MEAN'] = fields['TMAX_MEAN']-fields['TMIN_MEAN']
            fields['WATER_BALANCE_PROXY'] = fields['PREC_TOTAL']-fields['ET0_TOTAL']
            fields['RAIN_PER_GDD'] = fields['PREC_TOTAL']/fields['GDD_BASE10'] if fields['GDD_BASE10'] else 0
            fields['RADIATION_PER_GDD'] = fields['RAD_TOTAL']/fields['GDD_BASE10'] if fields['GDD_BASE10'] else 0
            fields['CROP_AREA_LOG1P'] = math.log1p(fields['CROP_AREA'])
            now = datetime.now(timezone(timedelta(hours=5,minutes=30)))
            year = now.year if now.month >= 6 else now.year-1
            row = {**references[0][1], 'numeric':[fields[n] for n in self.prep['numeric']],
                   'observed':None,'split':'scenario'}
            result = self.predict_yield({**request,'year':year,'proposedModel':'gbdt' if spatial else self.meta.get('yield_default_model','gbdt')},
                                        _row=row,_tree_model=self.coverage['model'] if spatial else None)
            if not result['ok']:return result
            result.update({'scope':'current_season_scenario','predictionDate':now.date().isoformat(),
                           'referenceYears':sorted(int(k.split('|')[1]) for k,_ in references),
                           'referenceCount':len(references), 'averageTemperatureC':temperature,
                           'landAreaHa':land_area,'suppliedWeather':supplied,
                           'inputProvenance':{n:('user input / derived from user input' if n in {'TAVG_MEAN','TMIN_MEAN','TMAX_MEAN','VPRES_MEAN','GDD_BASE10','TEMP_RANGE_MEAN','RAIN_PER_GDD','RADIATION_PER_GDD'} or
                              any(k in supplied and feature==n for k,feature,_,_ in optional_specs) or (n=='WATER_BALANCE_PROXY' and 'seasonalRainfallMm' in supplied)
                              else 'training-season reference / derived reference') for n in self.prep['numeric']},
                           'observedYield':None,'testMetricsApplyToThisForecast':False,
                           'warnings':['Current-season scenario, not a validated live forecast. Other weather and district-area inputs use training-season medians.' + (' Neural year trend is extrapolated beyond training.' if result['modelKind']=='mlp' and self.meta['yield_mlp'].get('use_year_trend',True) else '')],
                           'temperatureMethod':'Shift reference Tmin/Tmax by the user-average change; vapour pressure from assumed relative humidity; GDD approximately max(Tavg−10,0) × reference season days. Not daily measured GDD.'})
            result['referenceKind']='synthetic_neighbour_transfer' if spatial else 'measured_training_reference'
            if spatial:
                result['model']=self.coverage['metadata']['model_name']
                result['testMetrics']=self.coverage['metadata']['test']
                result['neighbourMethod']=self.coverage['metadata']['method']
                result['neighbourReferences']=[{'year':r['year'],'donors':r['donors']} for _,r in references]
                result['warnings'].append('Neighbour-derived synthetic reference. Local accuracy is not measured; donors may cross state boundaries.')
                result['inputProvenance']={n:v.replace('training-season reference','neighbour-derived synthetic reference') for n,v in result['inputProvenance'].items()}
            return result
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            return {'ok':False,'error':str(error) if isinstance(error,ValueError) else 'Invalid seasonal inputs.'}

    @staticmethod
    def image_tensor(photo):
        # Match EfficientNet-B0's ImageNet evaluation: shorter edge 256, bicubic,
        # centre crop 224, tensor /255, ImageNet channel normalization.
        width,height = photo.size
        if width <= height:
            size = (256, int(256*height/width))
        else:
            size = (int(256*width/height), 256)
        photo = photo.resize(size, Image.Resampling.BICUBIC)
        left,top = int(round((size[0]-224)/2)),int(round((size[1]-224)/2))
        pixels = np.asarray(photo.crop((left,top,left+224,top+224)),dtype=np.float32)/255
        x = (pixels-np.array([.485,.456,.406],np.float32))/np.array([.229,.224,.225],np.float32)
        return np.ascontiguousarray(x.transpose(2,0,1)[None])

    def classify_image(self, encoded):
        try:
            if not isinstance(encoded,str) or len(encoded) > 14_000_000:
                raise ValueError('Choose a photo no larger than 10 MB.')
            data = base64.b64decode(encoded,validate=True)
            if not 0 < len(data) <= 10*1024*1024:
                raise ValueError('Choose a photo no larger than 10 MB.')
            with Image.open(io.BytesIO(data)) as original:
                if original.format not in ('JPEG','PNG','WEBP'):
                    raise ValueError('Only JPEG, PNG and WebP photos are supported.')
                if min(original.size) < 128 or original.width*original.height > 24_000_000:
                    raise ValueError('Use a photo at least 128 × 128 pixels and no more than 24 megapixels.')
                photo = ImageOps.exif_transpose(original).convert('RGB')
            grey = np.asarray(photo.resize((224,224)).convert('L'),dtype=np.float32)
            contrast = float(np.percentile(grey,95)-np.percentile(grey,5))
            if float(grey.std()) < 4 or contrast < 10:
                raise ValueError('The photo has too little detail. Use a clear, well-lit rice-leaf photograph.')
            laplacian = -4*grey[1:-1,1:-1]+grey[:-2,1:-1]+grey[2:,1:-1]+grey[1:-1,:-2]+grey[1:-1,2:]
            quality_warnings = []
            if float(laplacian.var()) < 15:
                quality_warnings.append('The photo may be blurred; retake it in focus.')
            if grey.mean() < 35 or grey.mean() > 220:
                quality_warnings.append('Lighting is extreme; retake the photo in even daylight.')
            with self.session_lock:
                if self.session is None:
                    import onnxruntime as ort
                    options = ort.SessionOptions()
                    options.intra_op_num_threads = 2; options.inter_op_num_threads = 1
                    self.session = ort.InferenceSession(str(self.directory/'rice.onnx'),options,
                                                        providers=['CPUExecutionProvider'])
            logits = self.session.run(None, {'image': self.image_tensor(photo)})[0][0]
            if len(logits)!=len(self.meta['classes']) or not np.isfinite(logits).all():
                raise ValueError('Image model and class metadata are inconsistent. Reinstall Paddy.')
            scores = np.exp(logits-logits.max()); scores /= scores.sum()
            best = int(scores.argmax()); threshold = self.meta['image_abstention_threshold']
            uncertain = float(scores[best]) < threshold or bool(quality_warnings)
            return {'ok': True, 'model': self.meta['image_model'], 'version': self.meta['version'],
                    'label': None if uncertain else self.meta['classes'][best],
                    'candidate': self.meta['classes'][best], 'uncertain': uncertain,
                    'scores': [{'label': c, 'score': float(s)} for c,s in zip(self.meta['classes'],scores)],
                    'logits': [float(v) for v in logits], 'width': photo.width, 'height': photo.height,
                    'threshold': threshold, 'warnings': quality_warnings,
                    'testMetrics': {'accuracy':self.meta['image_test_accuracy'],'macro_F1':self.meta['image_test_macro_f1']},
                    'notice': f"{len(self.meta['classes'])}-class rice condition screening only. Scores are not calibrated confidence; unsupported plants or diseases may still receive a high score. Confirm symptoms with an agricultural expert."}
        except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            return {'ok': False, 'error': str(error) if isinstance(error,ValueError) else 'Cannot decode this photo safely.'}
