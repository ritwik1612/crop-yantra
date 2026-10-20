"""Reproducible local Windows build. Does not upload or publish anything."""
import json
import os
import shutil
import subprocess
import sys
import importlib.metadata
import argparse
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT/'APP/desktop'
WORK = ROOT/'OTHER/paddy_build_0_6_0'
OUTPUT = ROOT/'APP/desktop/releases'

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets-only',action='store_true',help='Repackage JS/CSS/assets only; requires an existing tested frozen Python build')
    args=parser.parse_args()
    WORK.mkdir(parents=True,exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='site-',dir=WORK))
    # Explicit allowlist: no Git, credentials, training data, raw photos, or venv.
    source = ROOT/'APP/prototype'
    for item in source.iterdir():
        if item.is_file() and item.suffix in {'.html','.css','.js','.svg'}:
            shutil.copy2(item,stage/item.name)
    for folder in ['assets','runtime']:
        shutil.copytree(source/folder,stage/folder,ignore=shutil.ignore_patterns('local-references','rice-specimen-*.png','rice-condition-*.png','rice-leaf-healthy.png','rice-leaf-blast.png','rice-leaf-bacterial*.png','rice-leaf-brown_spot.png','rice-leaf-downy_mildew.png','rice-leaf-hispa.png'))
    assert not (stage/'assets/local-references').exists(),'Restricted reference photos entered installer stage'
    subprocess.run(['node',str(ROOT/'APP/tests/test_reference_photos.cjs'),str(stage)],check=True)
    for filename in ['desktop.js','desktop.css']:
        shutil.copy2(DESKTOP/filename,stage/filename)
    # Preserve upstream license notices with the distributed runtime.
    for package in ['pywebview','onnxruntime','numpy','Pillow','pythonnet','clr_loader',
                    'bottle','proxy_tools','typing_extensions','cffi','pycparser','pyinstaller','reportlab','charset-normalizer']:
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or []:
            if ('dist-info' in str(file) and ('license' in str(file).lower() or 'copying' in str(file).lower())):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    target = stage/'licenses'/package/str(file).replace('/','_').replace('\\','_')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(original,target)
    html = (stage/'index.html').read_text(encoding='utf8')
    html = html.replace('</head>','<link rel="stylesheet" href="desktop.css"><link rel="stylesheet" href="experience.css"><script defer src="desktop.js"></script></head>')
    (stage/'index.html').write_text(html,encoding='utf8')
    icon = DESKTOP/'branding/paddy.ico'
    if not icon.exists():
        raise FileNotFoundError('Render the existing rice mark to branding/paddy.ico first.')
    # The native window and shortcuts need an actual ICO file at runtime too.
    shutil.copy2(icon,stage/'assets/paddy.ico')
    shutil.copy2(DESKTOP/'branding/paddy.png',stage/'assets/paddy-logo.png')
    if args.assets_only:
        if not (WORK/'dist/Paddy/Paddy.exe').exists():raise FileNotFoundError('Run a full build first')
        shutil.copytree(stage,WORK/'dist/Paddy/_internal/site',dirs_exist_ok=True)
    else:
      subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
        '--name','Paddy','--icon',str(icon),'--distpath',str(WORK/'dist'),
        '--workpath',str(WORK/'pyinstaller'),'--specpath',str(WORK),
        '--add-data',f'{stage}{os.pathsep}site','--collect-all','onnxruntime','--collect-data','reportlab',
        '--exclude-module','torch','--exclude-module','torchvision',
        '--exclude-module','sklearn','--exclude-module','pandas',
        str(DESKTOP/'main.py')],check=True,cwd=DESKTOP)
    compiler = Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Inno Setup 6/ISCC.exe'
    if not compiler.exists():
        compiler = Path('C:/Program Files (x86)/Inno Setup 6/ISCC.exe')
    if not compiler.exists():
        raise FileNotFoundError('Install Inno Setup 6 from jrsoftware.org to build Setup.exe.')
    subprocess.run([str(compiler),str(DESKTOP/'installer.iss')],check=True,cwd=DESKTOP)
    print('Installer:',OUTPUT/'Paddy-Setup-0.6.0.exe')

if __name__=='__main__': main()
