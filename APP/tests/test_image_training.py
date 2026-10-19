"""Pipeline tests use generated noise fixtures, never production crop data."""
import csv
import importlib.util
import io
import json
import random
import sys
import tempfile
import zipfile
from pathlib import Path
import pytest
from PIL import Image

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/training/images'))
from prepare_data import CLASSES,ALL_CLASSES,HashTree,prepare
from train import inspect_data,build_model

def test_hash_tree_matches_brute_force():
    rng=random.Random(42);values=[rng.getrandbits(64) for _ in range(100)]
    values += [values[0]^1,values[0]^3,values[0]]
    tree=HashTree()
    for i,value in enumerate(values):
        assert set(tree.query(value))=={j for j,other in enumerate(values[:i]) if (other^value).bit_count()<=4}
        tree.add(value,i)

def test_fixture_preparation_and_split_safety(tmp_path):
    rng=random.Random(19);source=tmp_path/'fixture.zip';metadata=[];photos={}
    for label in CLASSES:
        for i in range(6):
            name=f'{label}_{i}.png';pixels=rng.randbytes(128*128*3)
            image=Image.frombytes('RGB',(128,128),pixels);stream=io.BytesIO();image.save(stream,format='PNG')
            photos[label,name]=stream.getvalue();metadata.append({'image_id':name,'label':label})
    duplicate='duplicate.png';photos['blast',duplicate]=photos['blast','blast_0.png'];metadata.append({'image_id':duplicate,'label':'blast'})
    photos['normal','conflict.png']=photos['blast','blast_1.png'];metadata.append({'image_id':'conflict.png','label':'normal'})
    stream=io.StringIO();writer=csv.DictWriter(stream,fieldnames=['image_id','label']);writer.writeheader();writer.writerows(metadata)
    with zipfile.ZipFile(source,'w') as archive:
        archive.writestr('train.csv',stream.getvalue())
        for (label,name),data in photos.items():archive.writestr(f'train_images/{label}/{name}',data)
    output=tmp_path/'prepared';prepare(source,output,cap=6)
    info,counts=inspect_data(output)
    assert info['conflicting_groups_excluded']==1
    assert info['crop']=='Rice' and not info['paired_with_yield_rows']
    assert len(info['images'])==23
    assert all(set(count)==set(CLASSES) for count in counts.values())
    assert len({row['group_id'] for row in info['images']})==len(info['images'])
    with pytest.raises(FileExistsError):prepare(source,output,cap=6)
    first=info['images'][0];(output/first['path']).write_bytes(b'corrupt fixture')
    with pytest.raises(ValueError,match='hash mismatch'):inspect_data(output)

def test_cached_backbone_forward_without_training():
    import torch
    checkpoint=ROOT/'APP/models/pretrained/checkpoints/efficientnet_b0_rwightman-7f5810bc.pth'
    if not checkpoint.exists():pytest.skip('Download the official backbone before this optional integration test.')
    torch.set_num_threads(2);model,_=build_model();model.eval()
    with torch.inference_mode():result=model(torch.zeros(1,3,224,224))
    assert list(result.shape)==[1,4]
    model,_=build_model(ALL_CLASSES);model.eval()
    with torch.inference_mode():result=model(torch.zeros(1,3,224,224))
    assert list(result.shape)==[1,10]
