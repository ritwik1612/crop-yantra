"""Expose actual stage tensors in the existing ONNX graph without changing weights."""
import hashlib
import json
from pathlib import Path
import numpy as np
import onnx
import onnxruntime as ort
from PIL import Image
from engine import Engine

ROOT=Path(__file__).resolve().parents[2]


def main():
    runtime=ROOT/'APP/prototype/runtime';path=runtime/'rice.onnx'
    original=ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
    model=onnx.load(path)
    while len(model.graph.output)>1:model.graph.output.pop()
    checksums=[hashlib.sha256(p.SerializeToString()).hexdigest() for p in model.graph.initializer]
    inferred=onnx.shape_inference.infer_shapes(model)
    info={v.name:v for v in inferred.graph.value_info}
    stages=[]
    for i in range(9):
        nodes=[n for n in model.graph.node if n.name.startswith(f'/features/features.{i}/')]
        name=nodes[-1].output[0]
        model.graph.output.append(info[name]);stages.append({'name':'Stem' if i==0 else ('Feature head' if i==8 else f'MBConv group {i}'),'output':name})
    pooled='/Flatten_output_0';model.graph.output.append(info[pooled])
    candidate=runtime/'rice-stages-candidate.onnx';onnx.checker.check_model(model);onnx.save(model,candidate)
    session=ort.InferenceSession(str(candidate),providers=['CPUExecutionProvider'])
    maximum=0.
    for photo in sorted((ROOT/'APP/prototype/assets').glob('*-real.jpg')):
        with Image.open(photo) as image:tensor=Engine.image_tensor(image.convert('RGB'))
        before=original.run(['logits'],{'image':tensor})[0]
        after=session.run(['logits'],{'image':tensor})[0]
        np.testing.assert_allclose(before,after,atol=1e-4,rtol=1e-4)
        np.testing.assert_array_equal(before.argmax(1),after.argmax(1))
        maximum=max(maximum,float(np.max(np.abs(before-after))))
    assert checksums==[hashlib.sha256(p.SerializeToString()).hexdigest() for p in model.graph.initializer]
    candidate.replace(path)
    (runtime/'image-stages.json').write_text(json.dumps({'stages':stages,'pooled_output':pooled,
        'weights_unchanged':True,'reference_logit_max_error':maximum},indent=2),encoding='utf-8')
    print(json.dumps({'stage_outputs':len(stages),'weights_unchanged':True,'max_logit_error':maximum}))


if __name__=='__main__':main()
