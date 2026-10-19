"""Reproducible local Windows build. Does not upload or publish anything."""
import json
import os
import shutil
import subprocess
import sys
import importlib.metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT/'APP/desktop'
WORK = ROOT/'OTHER/paddy_build_0_3_0'
OUTPUT = ROOT/'APP/desktop/releases'

def main():
    WORK.mkdir(parents=True,exist_ok=True)
    OUTPUT.mkdir(exist_ok=True)
    stage = WORK/'site'
    stage.mkdir(exist_ok=True)
    # Explicit allowlist: no Git, credentials, training data, raw photos, or venv.
    source = ROOT/'APP/prototype'
    for item in source.iterdir():
        if item.is_file() and item.suffix in {'.html','.css','.js','.svg'}:
            shutil.copy2(item,stage/item.name)
    for folder in ['assets','runtime']:
        shutil.copytree(source/folder,stage/folder,dirs_exist_ok=True)
    for filename in ['desktop.js','desktop.css']:
        shutil.copy2(DESKTOP/filename,stage/filename)
    # Preserve upstream license notices with the distributed runtime.
    for package in ['pywebview','onnxruntime','numpy','Pillow','pythonnet','clr_loader',
                    'bottle','proxy_tools','typing_extensions','cffi','pycparser','pyinstaller']:
        distribution = importlib.metadata.distribution(package)
        for file in distribution.files or []:
            if ('dist-info' in str(file) and ('license' in str(file).lower() or 'copying' in str(file).lower())):
                original = Path(distribution.locate_file(file))
                if original.is_file():
                    target = stage/'licenses'/package/str(file).replace('/','_').replace('\\','_')
                    target.parent.mkdir(parents=True,exist_ok=True)
                    shutil.copy2(original,target)
    html = (stage/'index.html').read_text(encoding='utf8')
    html = html.replace('</head>','<link rel="stylesheet" href="desktop.css"><script defer src="desktop.js"></script></head>')
    (stage/'index.html').write_text(html,encoding='utf8')
    icon = DESKTOP/'branding/paddy.ico'
    if not icon.exists():
        raise FileNotFoundError('Render the existing rice mark to branding/paddy.ico first.')
    subprocess.run([sys.executable,'-m','PyInstaller','--noconfirm','--clean','--windowed',
        '--name','Paddy','--icon',str(icon),'--distpath',str(WORK/'dist'),
        '--workpath',str(WORK/'pyinstaller'),'--specpath',str(WORK),
        '--add-data',f'{stage}{os.pathsep}site','--collect-all','onnxruntime',
        '--exclude-module','torch','--exclude-module','torchvision',
        '--exclude-module','sklearn','--exclude-module','pandas',
        str(DESKTOP/'main.py')],check=True,cwd=DESKTOP)
    compiler = Path(os.environ.get('LOCALAPPDATA',''))/'Programs/Inno Setup 6/ISCC.exe'
    if not compiler.exists():
        compiler = Path('C:/Program Files (x86)/Inno Setup 6/ISCC.exe')
    if not compiler.exists():
        raise FileNotFoundError('Install Inno Setup 6 from jrsoftware.org to build Setup.exe.')
    subprocess.run([str(compiler),str(DESKTOP/'installer.iss')],check=True,cwd=DESKTOP)
    print('Installer:',OUTPUT/'Paddy-Setup-0.3.0.exe')

if __name__=='__main__': main()
