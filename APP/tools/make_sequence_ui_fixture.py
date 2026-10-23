"""Private browser fixtures from the real neural runtime. No training or report."""
import base64
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine
from reporting import ReportSession

engine=Engine(ROOT/'APP/prototype/runtime');reports=ReportSession(engine)
request={'districtId':'IND.2.7_1','season':'Kharif','areaHa':12,
         'landAreaHa':15,'averageTemperatureC':27}
fixture={'status':{**engine.status(),'pdfExportAvailable':True},
         'yield':reports.predict_seasonal_yield(request),
         'health':reports.classify_image(base64.b64encode((ROOT/'APP/prototype/assets/brown-spot-real.jpg').read_bytes()).decode())}
(ROOT/'OTHER').mkdir(exist_ok=True)
(ROOT/'OTHER/ui-audit-fixture.json').write_text(json.dumps(fixture),encoding='utf-8')
print('Actual runtime browser fixtures ready in private OTHER folder.')
