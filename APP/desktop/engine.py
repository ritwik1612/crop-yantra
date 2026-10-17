"""Offline inference using exported, already-trained Paddy models."""
import base64
import io
import json
import math
import threading
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
        self.session = None
        self.session_lock = threading.Lock()

    def status(self):
        return {'ok': True, 'version': self.meta['version'], 'offline': True,
                'yieldModel': self.meta['yield_model'], 'imageModel': self.meta['image_model']}

    def predict_yield(self, request):
        try:
            area = float(request['areaHa'])
            year = int(request['year'])
            if isinstance(request['areaHa'], bool) or not math.isfinite(area) or not .01 <= area <= 1_000_000:
                raise ValueError('Enter an area between 0.01 and 1,000,000 hectares.')
            if str(year) != str(request['year']):
                raise ValueError('Crop year must be a whole number.')
            key = f"{request['districtId']}|{year}|{request['season']}"
            row = self.history.get(key)
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
            prediction = self.trees['baseline']
            root_offset = 0.0
            for tree in self.trees['trees']:
                index = 0
                root_offset += tree[0][0]
                while not tree[index][5]:
                    node = tree[index]
                    child = node[3] if x[node[1]] <= node[2] else node[4]
                    contributions[node[1]] += tree[child][0]-node[0]
                    index = child
                prediction += tree[index][0]
            if prediction < 0 or not math.isfinite(prediction):
                raise ValueError('Model returned an invalid yield estimate.')
            baseline = self.trees['baseline'] + root_offset
            assert abs(baseline+sum(contributions)-prediction) < 1e-8
            feature_rows = [{'name': name, 'raw': value, 'imputed': numeric[i], 'scaled': scaled[i]}
                            for i,(name,value) in enumerate(zip(self.prep['numeric'],raw))]
            influence = sorted([{'feature': name.replace('numeric__','').replace('categorical__',''),
                                 'contribution': float(value)} for name,value in zip(self.prep['predictors'],contributions)],
                               key=lambda r: abs(r['contribution']), reverse=True)
            warnings = []
            if request['season'] not in self.prep['categories'][1]:
                warnings.append('Season not seen while fitting preprocessing; its one-hot indicators are all zero.')
            if row['split'] != 'test':
                warnings.append(f"This record belongs to the {row['split']} split, not the independent test split.")
            return {'ok': True, 'model': self.meta['yield_model'], 'version': self.meta['version'],
                    'yieldTPerHa': prediction, 'productionTonnes': prediction*area,
                    'areaHa': area, 'observedYield': row['observed'], 'split': row['split'],
                    'sourceState': row['state'], 'district': row['district'], 'year': year,
                    'season': request['season'], 'features': feature_rows,
                    'encodedCategories': dict(zip(self.prep['predictors'][len(numeric):],x[len(numeric):])),
                    'baseline': baseline, 'contributions': influence, 'warnings': warnings,
                    'testMetrics': self.meta['yield_test'], 'scope': 'historical_district_estimate'}
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            return {'ok': False, 'error': str(error) if isinstance(error, ValueError) else 'Invalid prediction inputs.'}

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
            scores = np.exp(logits-logits.max()); scores /= scores.sum()
            best = int(scores.argmax()); threshold = self.meta['image_abstention_threshold']
            uncertain = float(scores[best]) < threshold or bool(quality_warnings)
            return {'ok': True, 'model': self.meta['image_model'], 'version': self.meta['version'],
                    'label': None if uncertain else self.meta['classes'][best],
                    'candidate': self.meta['classes'][best], 'uncertain': uncertain,
                    'scores': [{'label': c, 'score': float(s)} for c,s in zip(self.meta['classes'],scores)],
                    'logits': [float(v) for v in logits], 'width': photo.width, 'height': photo.height,
                    'threshold': threshold, 'warnings': quality_warnings,
                    'notice': 'Four-class rice screening only. Scores are not calibrated confidence; unsupported plants or diseases may still receive a high score. Confirm symptoms with an agricultural expert.'}
        except (ValueError, UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
            return {'ok': False, 'error': str(error) if isinstance(error,ValueError) else 'Cannot decode this photo safely.'}
