"""Record installed public package versions, never credentials or environment values."""
import importlib.metadata
import json
import platform
import zipfile
from pathlib import Path
import torch

ROOT=Path(__file__).resolve().parents[2]
packages=sorted((distribution.metadata['Name'],distribution.version) for distribution in importlib.metadata.distributions())
output=ROOT/'APP/training/images'
(output/'requirements-local-cpu.lock.txt').write_text('\n'.join(f'{name}=={version}' for name,version in packages)+'\n',encoding='utf8')
report={'python':platform.python_version(),'platform':platform.platform(),'torch':torch.__version__,
        'cuda_available':torch.cuda.is_available(),'environment':'OTHER/training_env','packages':len(packages),
        'image_archive_present':any(zipfile.is_zipfile(path) for path in (ROOT/'DATASET/images/source').glob('*.zip')),
        'image_manifest_present':(ROOT/'DATASET/images/prepared/paddy_doctor_4class/manifest.json').is_file(),
        'training_started':False}
(output/'environment_status.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
print(json.dumps(report,indent=2))
