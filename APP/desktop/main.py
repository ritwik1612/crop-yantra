"""Native Windows shell. No remote inference, login, or cloud service."""
import ctypes
import json
import os
import sys
from pathlib import Path
from engine import Engine

def main():
    bundle = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    assets = bundle/'site' if getattr(sys,'frozen',False) else bundle.parent/'prototype'
    engine = Engine(assets/'runtime')
    if '--self-test' in sys.argv:
        row = next((key for key in engine.history if '|2019|' in key),None)
        district,year,season = row.split('|')
        result = engine.predict_yield({'districtId': district,'year': int(year),'season': season,'areaHa': 12})
        assert result['ok'] and result['yieldTPerHa'] > 0
        import onnxruntime as ort
        assert ort.InferenceSession(str(assets/'runtime/rice.onnx'),providers=['CPUExecutionProvider'])
        return
    import webview
    ctypes.windll.kernel32.CreateMutexW.restype = ctypes.c_void_p
    qa = '--qa' in sys.argv
    mutex = ctypes.windll.kernel32.CreateMutexW(None,False,'PaddyDesktopQA' if qa else 'PaddyDesktop')
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(None,'Paddy is already running. Switch to its open window.','Paddy',0x40)
        return
    # Store browser settings in the user's profile, never in Program Files.
    profile = Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'Paddy' / ('QAWebView' if qa else 'WebView')
    profile.mkdir(parents=True,exist_ok=True)
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Paddy.Desktop.1')
    class API:
        def status(self): return engine.status()
        def predict_yield(self, request): return engine.predict_yield(request)
        def classify_image(self, encoded): return engine.classify_image(encoded)
    window = webview.create_window('Paddy QA' if qa else 'Paddy', str(assets/'index.html'), js_api=API(),
                                  width=1340,height=900,min_size=(880,650),background_color='#f6f8f0')
    try:
        webview.start(gui='edgechromium',private_mode=False,storage_path=str(profile),debug=False)
    finally:
        ctypes.windll.kernel32.CloseHandle(ctypes.c_void_p(mutex))

if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        if '--self-test' not in sys.argv:
            ctypes.windll.user32.MessageBoxW(None,
                'Paddy could not start. Ensure Microsoft Edge WebView2 Runtime is installed.\n\n'+str(error),
                'Paddy',0x10)
        sys.exit(1)
