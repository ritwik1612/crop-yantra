"""Verify and activate the validation-selected ten-class EfficientNet-B0.

Checks the entire locked test partition against the original PyTorch checkpoint
before replacing the app's ONNX model. Does not train or select using test scores.
"""
import hashlib
import json
import os
import sys
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch
from PIL import Image, ImageOps
from sklearn.metrics import accuracy_score, f1_score, classification_report
from torch import nn
from torchvision.models import efficientnet_b0, EfficientNet_B0_Weights

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    torch.set_num_threads(2)
    run=ROOT/'APP/training/runs/images_10class_20261019'
    data=ROOT/'DATASET/images/prepared/paddy_doctor_10class'
    runtime=ROOT/'APP/prototype/runtime'
    manifest=json.loads((data/'manifest.json').read_text())
    metrics=json.loads((run/'metrics.json').read_text())
    checkpoint=torch.load(run/'model.pt',map_location='cpu',weights_only=True)
    if checkpoint['manifest_sha256']!=digest(data/'manifest.json'):
        raise ValueError('Training manifest changed since the checkpoint was trained.')
    classes=checkpoint['classes']
    if classes!=manifest['classes'] or len(classes)!=10 or checkpoint['architecture']!='efficientnet_b0':
        raise ValueError('Unexpected model or class order.')
    selected=next(row['validation'] for row in metrics['history'] if row['epoch']==metrics['best_epoch'])
    alternative=json.loads((ROOT/'APP/training/runs/images_mobile_10class_20261019/metrics.json').read_text())
    mobile_validation=next(row['validation'] for row in alternative['history'] if row['epoch']==alternative['best_epoch'])
    if selected['macro_F1']<=mobile_validation['macro_F1']:
        raise ValueError('EfficientNet did not win the validation architecture comparison.')
    model=efficientnet_b0(weights=None)
    model.classifier[-1]=nn.Linear(model.classifier[-1].in_features,len(classes))
    model.load_state_dict(checkpoint['state_dict'],strict=True);model.eval()
    temporary=runtime/'rice-verified-candidate.onnx'
    torch.onnx.export(model,torch.zeros(1,3,224,224),str(temporary),
        input_names=['image'],output_names=['logits'],opset_version=17,dynamo=False,
        dynamic_axes={'image':{0:'batch'},'logits':{0:'batch'}})
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(temporary),options,providers=['CPUExecutionProvider'])
    transform=EfficientNet_B0_Weights.IMAGENET1K_V1.transforms()
    rows=[row for row in manifest['images'] if row['split']=='test']
    expected_labels=[];predictions=[];maximum=0.
    for offset in range(0,len(rows),32):
        tensors=[]
        for row in rows[offset:offset+32]:
            path=data/row['path']
            if digest(path)!=row['sha256']:raise ValueError('Test image changed: '+row['image_id'])
            with Image.open(path) as photo:photo=ImageOps.exif_transpose(photo).convert('RGB')
            tensor=transform(photo).numpy()
            # Desktop resampling and normalization must match training too.
            np.testing.assert_allclose(Engine.image_tensor(photo)[0],tensor,atol=1e-6)
            tensors.append(tensor);expected_labels.append(row['class_index'])
        values=np.stack(tensors)
        with torch.inference_mode():original=model(torch.from_numpy(values)).numpy()
        exported=session.run(None,{'image':values})[0]
        maximum=max(maximum,float(np.max(np.abs(original-exported))))
        np.testing.assert_allclose(original,exported,atol=1e-4,rtol=1e-4)
        np.testing.assert_array_equal(original.argmax(1),exported.argmax(1))
        predictions.extend(exported.argmax(1).tolist())
        print(f'Verified {len(predictions)}/{len(rows)} locked test photos',flush=True)
    accuracy=accuracy_score(expected_labels,predictions)
    macro=f1_score(expected_labels,predictions,average='macro')
    np.testing.assert_allclose([accuracy,macro],[metrics['test']['accuracy'],metrics['test']['macro_F1']],atol=1e-12)
    report=classification_report(expected_labels,predictions,target_names=classes,output_dict=True,zero_division=0)
    metadata=json.loads((runtime/'metadata.json').read_text())
    metadata.update({'version':'2026-10-19-ten-class','classes':classes,'image_model':'EfficientNet-B0',
        'image_test_accuracy':accuracy,'image_test_macro_f1':macro,'image_export_max_error':maximum,
        'source_checkpoint_sha256':digest(run/'model.pt'),
        'image_training':{'train':5905,'validation':1257,'test':1257,'total':8419,'best_epoch':metrics['best_epoch'],
            'validation':selected,'alternative':'MobileNetV3-Small','alternative_validation':mobile_validation,
            'selection':'EfficientNet-B0 selected using validation macro-F1; each checkpoint selected using validation loss.',
            'manifest_sha256':digest(data/'manifest.json')},
        'image_per_class_recall':{label:report[label]['recall'] for label in classes},
        'image_transform':{'resize_short_edge':256,'crop':224,'interpolation':'bicubic',
            'mean':[.485,.456,.406],'std':[.229,.224,.225]},
        'image_export_verified_test_rows':len(rows),
        'image_scope':'Ten-class rice disease, pest-symptom and normal screening; not confirmed diagnosis or regional field validation.'})
    os.replace(temporary,runtime/'rice.onnx')
    (runtime/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'activated':True,'test_accuracy':accuracy,'test_macro_F1':macro,'max_logit_error':maximum,'test_photos_checked':len(rows)}),flush=True)


if __name__=='__main__':main()
