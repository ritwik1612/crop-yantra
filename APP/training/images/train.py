"""Four- or ten-class rice classifier. Default checks readiness; --train is required."""
import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
import torch
from torch import nn
from torch.utils.data import Dataset, DataLoader
from torchvision import transforms
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0, MobileNet_V3_Small_Weights, mobilenet_v3_small
from torchvision.transforms import InterpolationMode
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).parent))
from prepare_data import CLASSES, ALL_CLASSES, HashTree

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def inspect_data(directory):
    filename=directory/'manifest.json'
    if not filename.exists():raise FileNotFoundError('Image dataset not prepared. Download the official ZIP, then run prepare_data.py.')
    info=json.loads(filename.read_text(encoding='utf8'))
    if info.get('crop')!='Rice' or info['classes'] not in (CLASSES,ALL_CLASSES):raise ValueError('Unsupported crop or class mapping')
    classes=info['classes']
    images=info['images'];groups=set();pixels=set();files=set();tree=HashTree()
    counts={split:Counter() for split in ['train','validation','test']}
    for i,row in enumerate(images):
        path=(directory/row['path']).resolve()
        if not path.is_relative_to(directory.resolve()):raise ValueError('Image path leaves dataset directory')
        if row['split'] not in counts or row['class_index']!=classes.index(row['class']):raise ValueError('Invalid split/class mapping')
        if row['group_id'] in groups or row['pixel_sha256'] in pixels or path in files:raise ValueError('Duplicate image/group in prepared set')
        groups.add(row['group_id']);pixels.add(row['pixel_sha256']);files.add(path)
        if digest(path)!=row['sha256']:raise ValueError(f'Image hash mismatch: {path.name}')
        with Image.open(path) as image:image.verify()
        value=int(row['phash'],16)
        if tree.query(value):raise ValueError('Near-duplicate representatives remain in prepared set')
        tree.add(value,i);counts[row['split']][row['class']]+=1
    if any(set(count)!=set(classes) for count in counts.values()):raise ValueError('Every class must appear in every split')
    return info,counts

class RiceImages(Dataset):
    def __init__(self,directory,records,transform):self.directory,self.records,self.transform=directory,records,transform
    def __len__(self):return len(self.records)
    def __getitem__(self,index):
        row=self.records[index]
        with Image.open(self.directory/row['path']) as image:
            rgb=ImageOps.exif_transpose(image).convert('RGB')
            tensor=self.transform(rgb)
        return tensor,row['class_index']

def build_model(classes=CLASSES,architecture='efficientnet_b0'):
    weights=(MobileNet_V3_Small_Weights.IMAGENET1K_V1 if architecture=='mobilenet_v3_small' else EfficientNet_B0_Weights.IMAGENET1K_V1)
    checkpoint=ROOT/'APP/models/pretrained/checkpoints'/weights.url.rsplit('/',1)[1]
    if not checkpoint.exists():raise FileNotFoundError('Backbone missing. Run fetch_backbone.py first.')
    expected=weights.url.rsplit('-',1)[-1].split('.')[0]
    if not digest(checkpoint).startswith(expected):raise ValueError('Backbone hash mismatch')
    model= mobilenet_v3_small(weights=None) if architecture=='mobilenet_v3_small' else efficientnet_b0(weights=None)
    model.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True),strict=True)
    model.classifier[-1]=nn.Linear(model.classifier[-1].in_features,len(classes))
    return model,weights

def evaluate(model,loader,criterion,device):
    model.eval();total=0;loss_sum=0;actual=[];predictions=[]
    with torch.inference_mode():
        for x,y in loader:
            x,y=x.to(device),y.to(device);logits=model(x);loss=criterion(logits,y)
            total+=len(y);loss_sum+=loss.item()*len(y)
            actual.extend(y.cpu().tolist());predictions.extend(logits.argmax(1).cpu().tolist())
    return {'loss':loss_sum/total,'accuracy':accuracy_score(actual,predictions),
            'macro_F1':f1_score(actual,predictions,labels=list(range(model.classifier[-1].out_features)),average='macro',zero_division=0)},actual,predictions

def main():
    global CLASSES
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data',type=Path,default=ROOT/'DATASET/images/prepared/paddy_doctor_4class')
    parser.add_argument('--train',action='store_true')
    parser.add_argument('--epochs',type=int,default=15)
    parser.add_argument('--head-epochs',type=int,default=5)
    parser.add_argument('--batch-size',type=int,default=32)
    parser.add_argument('--workers',type=int,default=0)
    parser.add_argument('--threads',type=int,default=2)
    parser.add_argument('--architecture',choices=['efficientnet_b0','mobilenet_v3_small'],default='efficientnet_b0')
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    if args.epochs<1 or not 1<=args.head_epochs<=args.epochs or args.batch_size<1 or args.threads<1 or args.workers<0:parser.error('Invalid epoch/batch/thread settings')
    random.seed(args.seed);np.random.seed(args.seed);torch.manual_seed(args.seed);torch.set_num_threads(args.threads)
    info,counts=inspect_data(args.data)
    CLASSES=info['classes']
    model,weights=build_model(CLASSES,args.architecture);model.eval()
    sample=RiceImages(args.data,info['images'][:1],weights.transforms())[0][0]
    if list(sample.shape)!=[3,224,224] or not torch.isfinite(sample).all():
        raise ValueError('Invalid transformed image tensor')
    with torch.inference_mode():
        logits=model(sample.unsqueeze(0))
        shape=list(logits.shape)
    if not torch.isfinite(logits).all():raise ValueError('Non-finite classifier output')
    if shape!=[1,len(CLASSES)]:raise ValueError('Invalid classifier output shape')
    device=torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    readiness={'status':'image_data_ready','trained':False,'crop':'Rice','classes':CLASSES,
        'split_counts':{s:dict(count) for s,count in counts.items()},'forward_shape':shape,
        'sample_tensor_shape':list(sample.shape),'real_image_forward_checked':True,
        'architecture':args.architecture,'pretrained_weights':'ImageNet IMAGENET1K_V1',
        'device':str(device),'manifest_sha256':digest(args.data/'manifest.json'),
        'regional_validation_complete':False,'paired_with_yield_rows':False}
    if not args.train:print(json.dumps(readiness,indent=2));return
    training_transform=transforms.Compose([
        transforms.RandomResizedCrop(224,scale=(.85,1),interpolation=InterpolationMode.BICUBIC),
        transforms.RandomHorizontalFlip(),transforms.RandomRotation(10,interpolation=InterpolationMode.BILINEAR),
        transforms.ColorJitter(brightness=.1,contrast=.1,saturation=.05),transforms.ToTensor(),
        transforms.Normalize([.485,.456,.406],[.229,.224,.225])])
    loaders={}
    for split in counts:
        records=[r for r in info['images'] if r['split']==split]
        dataset=RiceImages(args.data,records,training_transform if split=='train' else weights.transforms())
        loaders[split]=DataLoader(dataset,batch_size=args.batch_size,shuffle=split=='train',num_workers=args.workers,
            generator=torch.Generator().manual_seed(args.seed),pin_memory=device.type=='cuda')
    output=args.output or ROOT/'APP/training/runs'/datetime.now(timezone.utc).strftime('images_%Y%m%dT%H%M%S_%fZ')
    output.mkdir(parents=True,exist_ok=False)
    model.to(device)
    for parameter in model.features.parameters():parameter.requires_grad=False
    optimizer=torch.optim.AdamW(model.classifier.parameters(),lr=1e-3,weight_decay=1e-4)
    frequencies=torch.tensor([counts['train'][c] for c in CLASSES],dtype=torch.float32,device=device)
    class_weights=frequencies.sum()/(len(CLASSES)*frequencies)
    criterion=nn.CrossEntropyLoss(weight=class_weights);best_loss=float('inf');best_state=None;best_epoch=0;stale=0;history=[]
    for epoch in range(args.epochs):
        if epoch==args.head_epochs:
            for block in model.features[-2:]:
                for parameter in block.parameters():parameter.requires_grad=True
            optimizer=torch.optim.AdamW((p for p in model.parameters() if p.requires_grad),lr=1e-4,weight_decay=1e-4)
            stale=0
        model.train();model.features.eval()
        if epoch>=args.head_epochs:
            for block in model.features[-2:]:block.train()
        loss_sum=0;seen=0
        for x,y in loaders['train']:
            x,y=x.to(device),y.to(device);optimizer.zero_grad(set_to_none=True)
            loss=criterion(model(x),y);loss.backward();optimizer.step()
            loss_sum+=loss.item()*len(y);seen+=len(y)
        measured,_,_=evaluate(model,loaders['validation'],criterion,device)
        entry={'epoch':epoch+1,'phase':'head' if epoch<args.head_epochs else 'fine_tune','train_loss':loss_sum/seen,'validation':measured}
        history.append(entry);print(json.dumps(entry),flush=True)
        torch.save({'state_dict':model.state_dict(),'epoch':epoch+1,'classes':CLASSES,'architecture':args.architecture},output/'latest.pt')
        (output/'progress.json').write_text(json.dumps({'status':'training','history':history,'classes':CLASSES},indent=2),encoding='utf8')
        if measured['loss']<best_loss:
            best_loss=measured['loss'];best_epoch=epoch+1;stale=0
            best_state={k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            torch.save({'state_dict':best_state,'classes':CLASSES,'architecture':args.architecture,'epoch':best_epoch},output/'best.pt')
        else:stale+=1
        if epoch>=args.head_epochs and stale>=4:break
    model.load_state_dict(best_state)
    test,y,pred=evaluate(model,loaders['test'],criterion,device)
    bundle={**readiness,'status':'trained_not_activated','trained':True,'best_epoch':best_epoch,
        'selection':'lowest validation cross-entropy; test evaluated once after selection','test':test,
        'classification_report':classification_report(y,pred,labels=list(range(len(CLASSES))),target_names=CLASSES,output_dict=True,zero_division=0),
        'confusion_matrix':confusion_matrix(y,pred,labels=list(range(len(CLASSES)))).tolist(),'history':history,
        'open_set_rejection_validated':False,'confidence_calibrated':False}
    torch.save({'state_dict':best_state,'classes':CLASSES,'architecture':args.architecture,'manifest_sha256':readiness['manifest_sha256']},output/'model.pt')
    (output/'metrics.json').write_text(json.dumps(bundle,indent=2)+'\n',encoding='utf8')
    (output/'progress.json').write_text(json.dumps({'status':'complete','history':history,'classes':CLASSES,
        'best_epoch':best_epoch,'test':test,'activated':False},indent=2),encoding='utf8')
    print(f'Training complete: {output}. No app model activation or deployment performed.')

if __name__=='__main__':main()
