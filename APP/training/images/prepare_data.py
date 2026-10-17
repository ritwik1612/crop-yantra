"""Prepare at most 1,600 genuine rice photos from an authorized competition ZIP."""
import argparse
import csv
import hashlib
import io
import json
import random
import tempfile
import zipfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from PIL import Image, ImageOps
import imagehash

ROOT=Path(__file__).resolve().parents[3]
CLASSES=['bacterial_leaf_blight','blast','brown_spot','normal']

def sha(data):return hashlib.sha256(data).hexdigest()

class HashTree:
    """BK tree for bounded Hamming-distance queries on 64-bit perceptual hashes."""
    def __init__(self):self.root=None
    def query(self,value,radius=4):
        found=[];pending=[self.root] if self.root else []
        while pending:
            node=pending.pop();distance=(value^node[0]).bit_count()
            if distance<=radius:found.append(node[1])
            pending.extend(child for edge,child in node[2].items() if distance-radius<=edge<=distance+radius)
        return found
    def add(self,value,index):
        node=self.root
        if node is None:self.root=[value,index,{}];return
        while True:
            distance=(value^node[0]).bit_count()
            if distance not in node[2]:node[2][distance]=[value,index,{}];return
            node=node[2][distance]

def prepare(archive,output,cap=400,seed=42):
    if cap<3 or cap>400:raise ValueError('Choose 3–400 images per class.')
    if output.exists():raise FileExistsError('Output exists; use a new output directory to preserve previous splits.')
    candidates=[];excluded=[];members={}
    with zipfile.ZipFile(archive) as zipped:
        names=zipped.namelist()
        labels=[n for n in names if PurePosixPath(n).name=='train.csv']
        if len(labels)!=1:raise ValueError('Expected exactly one official train.csv in the archive.')
        if zipped.getinfo(labels[0]).file_size>10_000_000:raise ValueError('Unexpected metadata size.')
        metadata=list(csv.DictReader(io.StringIO(zipped.read(labels[0]).decode('utf-8-sig'))))
        if not metadata or not {'image_id','label'}<=metadata[0].keys():raise ValueError('Unsupported train.csv schema.')
        for name in names:
            parts=PurePosixPath(name).parts
            if len(parts)>=3 and parts[-3]=='train_images' and parts[-2] in CLASSES:
                identity=(parts[-2],parts[-1])
                if identity in members:raise ValueError('Duplicate image member path.')
                members[identity]=name
        for meta in metadata:
            label=meta['label'];identity=(label,meta['image_id'])
            if label not in CLASSES:continue
            name=members.get(identity)
            if not name:excluded.append({'image_id':meta['image_id'],'reason':'missing_image'});continue
            try:
                if zipped.getinfo(name).file_size>20*1024*1024:raise ValueError('image exceeds 20 MB')
                data=zipped.read(name)
                with Image.open(io.BytesIO(data)) as original:
                    original.verify()
                with Image.open(io.BytesIO(data)) as original:
                    if original.width*original.height>24_000_000 or min(original.size)<128:raise ValueError('unsupported resolution')
                    rgb=ImageOps.exif_transpose(original).convert('RGB')
                    digest=sha(rgb.width.to_bytes(4,'big')+rgb.height.to_bytes(4,'big')+rgb.tobytes())
                    perceptual=int(str(imagehash.phash(rgb)),16)
                    candidates.append({'image_id':meta['image_id'],'class':label,'member':name,
                        'width':rgb.width,'height':rgb.height,'sha256':sha(data),'pixel_sha256':digest,
                        'phash':format(perceptual,'016x'),'variety':meta.get('variety'),'age_days':meta.get('age')})
            except (OSError,ValueError,Image.DecompressionBombError) as error:
                excluded.append({'image_id':meta['image_id'],'reason':str(error)})
            if len(candidates)%250==0:print(f'Validated {len(candidates)} selected-class images',flush=True)
        if {c['class'] for c in candidates}!=set(CLASSES):raise ValueError('Not all four selected classes are present.')
        parent=list(range(len(candidates)))
        def find(i):
            while parent[i]!=i:parent[i]=parent[parent[i]];i=parent[i]
            return i
        def union(a,b):parent[find(a)]=find(b)
        tree=HashTree();pixels={}
        for i,row in enumerate(candidates):
            value=int(row['phash'],16)
            for other in tree.query(value):union(i,other)
            tree.add(value,i)
            if row['pixel_sha256'] in pixels:union(i,pixels[row['pixel_sha256']])
            else:pixels[row['pixel_sha256']]=i
        groups=defaultdict(list)
        for i,row in enumerate(candidates):groups[find(i)].append(row)
        representatives=[];conflicts=0
        for group in groups.values():
            if len({r['class'] for r in group})!=1:
                conflicts+=1
                excluded.extend({'image_id':r['image_id'],'reason':'perceptual_group_label_conflict'} for r in group)
                continue
            representative=min(group,key=lambda r:sha(f"{seed}|{r['image_id']}".encode()))
            representative['group_id']=min(r['pixel_sha256'] for r in group)
            representative['group_size']=len(group)
            representatives.append(representative)
        selected=[]
        for label in CLASSES:
            available=sorted((r for r in representatives if r['class']==label),key=lambda r:sha(f"{seed}|{r['image_id']}".encode()))[:cap]
            if len(available)<3:raise ValueError(f'Insufficient unique groups for {label}')
            random.Random(seed).shuffle(available)
            validation=max(1,int(len(available)*.15));test=max(1,int(len(available)*.15));train=len(available)-validation-test
            for i,row in enumerate(available):
                row['split']='train' if i<train else 'validation' if i<train+validation else 'test'
                row['class_index']=CLASSES.index(label)
                row['path']=f"images/{label}/{Path(row['image_id']).name}"
                selected.append(row)
        output.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='rice-images-',dir=output.parent) as temporary:
            staging=Path(temporary)/'subset';staging.mkdir()
            for row in selected:
                target=staging/row['path'];target.parent.mkdir(parents=True,exist_ok=True)
                data=zipped.read(row['member'])
                if sha(data)!=row['sha256']:raise ValueError('Archive content changed during preparation.')
                target.write_bytes(data)
            with archive.open('rb') as stream:archive_hash=hashlib.file_digest(stream,'sha256').hexdigest()
            manifest={'schema_version':1,'source':'Paddy Doctor competition train.csv and train_images',
                'crop':'Rice','reported_collection_region':'Near Tirunelveli, Tamil Nadu, India',
                'regional_validation_complete':False,'paired_with_yield_rows':False,
                'source_url':'https://www.kaggle.com/competitions/paddy-disease-classification/data',
                'archive_name':archive.name,'archive_sha256':archive_hash,'seed':seed,'classes':CLASSES,
                'images':selected,'excluded':excluded,'candidate_images':len(candidates),
                'duplicate_groups':len(groups),'conflicting_groups_excluded':conflicts,
                'deduplication':'decoded RGB SHA256 + 64-bit pHash connected groups, Hamming distance <=4; one representative per group',
                'split_counts':{s:dict(Counter(r['class'] for r in selected if r['split']==s)) for s in ['train','validation','test']},
                'bytes':sum((staging/r['path']).stat().st_size for r in selected),
                'limitation':'No plant/capture-session grouping metadata is supplied; perceptual deduplication cannot establish independent field sessions.',
                'augmented_before_split':False,'classifier_trained':False}
            (staging/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
            staging.rename(output)
    print(json.dumps({key:manifest[key] for key in ['classes','split_counts','bytes','candidate_images','conflicting_groups_excluded']},indent=2))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=ROOT/'DATASET/images/prepared/paddy_doctor_4class')
    parser.add_argument('--per-class',type=int,default=400)
    args=parser.parse_args();prepare(args.archive,args.output,args.per_class)

if __name__=='__main__':main()
