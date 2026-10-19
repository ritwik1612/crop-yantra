"""Local, uninstalled Paddy preview with the real offline inference engine.

Bind loopback only. Accept JSON POSTs from this exact origin; expose only public
UI assets, never the model directory, project files or arbitrary filesystem paths.
"""
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from engine import Engine

ROOT=Path(__file__).resolve().parents[2]
SITE=ROOT/'APP/prototype'
engine=Engine(SITE/'runtime')
PORT=8765
ORIGIN=f'http://127.0.0.1:{PORT}'
BRIDGE="""<script>window.pywebview={api:Object.fromEntries(['status','predict_seasonal_yield','classify_image'].map(name=>[name,async value=>{const r=await fetch('/api/'+name,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(value??{})});if(!r.ok)throw new Error('Local preview request failed');return r.json()}]))};</script><link rel="stylesheet" href="/desktop.css"><link rel="stylesheet" href="/experience.css"><script defer src="/desktop.js"></script>"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def respond(self,code,content,kind):
        self.send_response(code);self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(content)

    def do_GET(self):
        path=urlsplit(self.path).path
        if path in ('/','/index.html'):
            html=(SITE/'index.html').read_text(encoding='utf-8').replace('</head>',BRIDGE+'</head>')
            return self.respond(200,html.encode(),'text/html; charset=utf-8')
        name=path.lstrip('/')
        if name in ('desktop.js','desktop.css'):target=ROOT/'APP/desktop'/name
        elif '/' not in name and name.endswith(('.js','.css','.svg')):target=SITE/name
        elif name.startswith('assets/'):
            target=(SITE/name).resolve()
            if SITE/'assets' not in target.parents:return self.respond(404,b'Not found','text/plain')
        else:return self.respond(404,b'Not found','text/plain')
        if not target.is_file():return self.respond(404,b'Not found','text/plain')
        return self.respond(200,target.read_bytes(),mimetypes.guess_type(target)[0] or 'application/octet-stream')

    def do_POST(self):
        if self.headers.get('Origin')!=ORIGIN or self.headers.get('Content-Type')!='application/json':
            return self.respond(403,b'Origin or content type rejected','text/plain')
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=14_000_100:raise ValueError('Invalid request size')
            value=json.loads(self.rfile.read(size))
            methods={'/api/status':lambda _:engine.status(), '/api/predict_seasonal_yield':engine.predict_seasonal_yield,
                     '/api/classify_image':engine.classify_image}
            method=methods.get(urlsplit(self.path).path)
            if not method:return self.respond(404,b'Not found','text/plain')
            return self.respond(200,json.dumps(method(value),allow_nan=False).encode(),'application/json')
        except (ValueError,TypeError):return self.respond(400,b'Invalid input','text/plain')


if __name__=='__main__':
    print('Paddy preview: '+ORIGIN,flush=True)
    ThreadingHTTPServer(('127.0.0.1',PORT),Handler).serve_forever()
