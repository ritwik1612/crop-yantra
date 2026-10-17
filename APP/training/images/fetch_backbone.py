"""Cache official ImageNet EfficientNet-B0 weights. Does not train a model."""
import hashlib
import json
from pathlib import Path
import torch
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

ROOT=Path(__file__).resolve().parents[3]

def main():
    directory=ROOT/'APP/models/pretrained'
    directory.mkdir(parents=True,exist_ok=True)
    torch.hub.set_dir(str(directory))
    weights=EfficientNet_B0_Weights.IMAGENET1K_V1
    state=weights.get_state_dict(progress=True,check_hash=True)
    model=efficientnet_b0(weights=None)
    model.load_state_dict(state,strict=True)
    model.eval()
    torch.set_num_threads(2)
    with torch.inference_mode():
        output=model(torch.zeros(1,3,224,224))
    assert tuple(output.shape)==(1,1000)
    checkpoint=directory/'checkpoints'/weights.url.rsplit('/',1)[1]
    report={'architecture':'EfficientNet-B0','weights':'IMAGENET1K_V1',
            'source':weights.url,'checkpoint':str(checkpoint.relative_to(ROOT)),
            'bytes':checkpoint.stat().st_size,'sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
            'forward_shape':list(output.shape),'rice_classifier_trained':False,
            'torch':torch.__version__}
    (directory/'backbone_manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
