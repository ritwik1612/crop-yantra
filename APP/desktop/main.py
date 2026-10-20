"""Native Windows shell. No remote inference, login, or cloud service."""
import ctypes
import json
import os
import sys
import tempfile
from pathlib import Path
from engine import Engine
from reporting import ReportSession

def main():
    bundle = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    assets = bundle/'site' if getattr(sys,'frozen',False) else bundle.parent/'prototype'
    icon = assets/'assets/paddy.ico' if getattr(sys,'frozen',False) else bundle/'branding/paddy.ico'
    if not icon.is_file():
        raise FileNotFoundError('Paddy application icon is missing from the installation.')
    engine = Engine(assets/'runtime')
    reports = ReportSession(engine,assets/'assets/paddy-logo.png' if getattr(sys,'frozen',False) else bundle/'branding/paddy.png')
    if '--self-test' in sys.argv:
        row = next((key for key in engine.history if '|2019|' in key),None)
        district,year,season = row.split('|')
        result = engine.predict_yield({'districtId': district,'year': int(year),'season': season,'areaHa': 12})
        assert result['ok'] and result['yieldTPerHa'] > 0
        neural = engine.predict_yield({'districtId': district,'year': int(year),'season': season,'areaHa': 12,'proposedModel':'mlp'})
        assert neural['ok'] and neural['modelKind'] == 'mlp' and neural['yieldTPerHa'] > 0
        import onnxruntime as ort
        image_session=ort.InferenceSession(str(assets/'runtime/rice.onnx'),providers=['CPUExecutionProvider'])
        import numpy as np
        logits=image_session.run(None,{'image':np.zeros((1,3,224,224),dtype=np.float32)})[0]
        assert logits.shape==(1,len(engine.meta['classes'])) and len(engine.meta['classes'])==10
        import base64
        y=reports.predict_seasonal_yield({'districtId':district,'district':'Self-test','season':season,
                                        'areaHa':12,'landAreaHa':15,'averageTemperatureC':27})
        h=reports.classify_image(base64.b64encode((assets/'assets/blast-real.jpg').read_bytes()).decode('ascii'))
        assert y['ok'] and h['ok']
        pdf=reports.create({'mode':'combined','yieldId':y['exportId'],'healthId':h['exportId']})
        assert pdf.startswith(b'%PDF-') and b'/Subtype /Image' in pdf
        return
    # Establish taskbar identity before the GUI runtime creates any windows.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Paddy.Desktop.1')
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
    class API:
        def status(self): return {**engine.status(),'pdfExportAvailable':True}
        def predict_yield(self, request): return engine.predict_yield(request)
        def predict_seasonal_yield(self, request): return reports.predict_seasonal_yield(request)
        def classify_image(self, encoded): return reports.classify_image(encoded)
        def export_pdf(self, options):
            temporary=None
            try:
                data=reports.create(options)
                selected=window.create_file_dialog(webview.FileDialog.SAVE,
                  save_filename='Paddy-'+options['mode']+'.pdf',file_types=('PDF document (*.pdf)',))
                if not selected:return {'ok':False,'cancelled':True}
                target=Path(selected[0] if isinstance(selected,(tuple,list)) else selected)
                if target.suffix.lower()!='.pdf':raise ValueError('Save the report with a .pdf extension.')
                with tempfile.NamedTemporaryFile(dir=target.parent,prefix='.paddy-',suffix='.tmp',delete=False) as stream:
                    temporary=Path(stream.name);stream.write(data)
                os.replace(temporary,target);temporary=None
                return {'ok':True,'filename':target.name,'path':str(target)}
            except Exception as error:
                return {'ok':False,'error':str(error) if isinstance(error,ValueError) else 'The PDF could not be saved. Choose a writable folder and try again.'}
            finally:
                if temporary is not None:temporary.unlink(missing_ok=True)
    window = webview.create_window('Paddy', str(assets/'index.html'), js_api=API(),
                                  width=1340,height=900,min_size=(880,650),background_color='#030303')
    try:
        # WinForms uses this file for Form.Icon. Do not rely on ExtractIconW's
        # fallback from the frozen executable for title-bar/taskbar branding.
        webview.start(gui='edgechromium',private_mode=False,storage_path=str(profile),debug=False,icon=str(icon))
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
