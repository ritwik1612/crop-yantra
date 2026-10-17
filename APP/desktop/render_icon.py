"""Convert an already-rendered logo PNG to a multi-resolution Windows icon."""
from pathlib import Path
from PIL import Image

directory=Path(__file__).resolve().parent/'branding'
with Image.open(directory/'paddy.png') as image:
    image.save(directory/'paddy.ico',format='ICO',sizes=[(16,16),(24,24),(32,32),(48,48),(64,64),(128,128),(256,256)])
