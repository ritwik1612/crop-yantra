"""Offline, typeset PDF exports from immutable successful inference snapshots."""
import base64
import copy
import io
import math
import threading
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image as PILImage, ImageOps
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Image, KeepTogether

VERSION='0.6.1'
BG=colors.HexColor('#080a08'); PANEL=colors.HexColor('#141a14')
INK=colors.HexColor('#eceee4'); MUTED=colors.HexColor('#a8b1a1')
GREEN=colors.HexColor('#bdcda2'); LINE=colors.HexColor('#394333')
LABELS={'bacterial_leaf_blight':'Bacterial leaf blight','bacterial_leaf_streak':'Bacterial leaf streak',
 'bacterial_panicle_blight':'Bacterial panicle blight','blast':'Rice blast','brown_spot':'Brown spot',
 'dead_heart':'Dead heart','downy_mildew':'Downy mildew','hispa':'Hispa damage','normal':'Normal rice','tungro':'Tungro'}

def text(value):
    return str(value).replace('\u2212','-').replace('\u2013','-').replace('\u2014','-').replace('\u00d7',' x ').replace('\u2192',' > ').replace('\u2248','~').replace('\u20b9','INR ').replace('\u00b2','2')

def number(value, digits=3):
    value=float(value)
    if not math.isfinite(value):raise ValueError('Non-finite value in report.')
    return f'{value:,.{digits}f}'

def build_pdf(yield_snapshot=None, health_snapshot=None, scenario=None, logo=None):
    """Return vector/text PDF bytes; never render or capture the app webpage."""
    if not yield_snapshot and not health_snapshot:raise ValueError('Run a prediction or photo screening first.')
    scenario=scenario or {}
    if not isinstance(scenario,dict):raise ValueError('Invalid output scenario.')
    now=datetime.now(timezone(timedelta(hours=5,minutes=30)))
    output=io.BytesIO(); page_width,page_height=A4; width=page_width-88
    styles={
      'body':ParagraphStyle('body',fontName='Helvetica',fontSize=9.3,leading=14,textColor=INK,spaceAfter=8),
      'small':ParagraphStyle('small',fontName='Helvetica',fontSize=8,leading=12,textColor=MUTED,spaceAfter=6),
      'title':ParagraphStyle('title',fontName='Helvetica-Bold',fontSize=28,leading=33,textColor=INK,spaceAfter=12),
      'h':ParagraphStyle('h',fontName='Helvetica-Bold',fontSize=13,leading=18,textColor=GREEN,spaceBefore=14,spaceAfter=9),
      'cell':ParagraphStyle('cell',fontName='Helvetica',fontSize=8.5,leading=12,textColor=INK),
      'head':ParagraphStyle('head',fontName='Helvetica-Bold',fontSize=8,leading=12,textColor=GREEN),
    }
    def p(value,style='body'):return Paragraph(escape(text(value)).replace('\n','<br/>'),styles[style])
    def table(headers,rows,widths=None):
        data=[[p(v,'head') for v in headers]]+[[p(v,'cell') for v in row] for row in rows]
        t=Table(data,colWidths=widths or [width/len(headers)]*len(headers),repeatRows=1,hAlign='LEFT')
        t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PANEL),('VALIGN',(0,0),(-1,-1),'TOP'),
          ('LEFTPADDING',(0,0),(-1,-1),10),('RIGHTPADDING',(0,0),(-1,-1),10),
          ('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),
          ('LINEBELOW',(0,0),(-1,0),.7,LINE),('LINEBELOW',(0,1),(-1,-1),.3,LINE)]))
        t.spaceAfter=6
        return t
    story=[]
    def heading(kicker,title):story.extend([p(kicker.upper(),'small'),p(title,'title')])
    if yield_snapshot:
        req,r=yield_snapshot['request'],yield_snapshot['result']
        area=float(scenario.get('areaHa',req['areaHa']))
        price=scenario.get('priceINRPerKg')
        if not math.isfinite(area) or not .01<=area<=1e6:raise ValueError('Enter a valid positive scenario area before exporting.')
        if price is not None:
            price=float(price)
            if not math.isfinite(price) or not 0<=price<=100000:raise ValueError('Enter a valid price before exporting.')
        y=float(r['yieldTPerHa']);tonnes=y*area;kg=tonnes*1000
        heading('01 / seasonal yield','Yield prediction')
        story.append(p(f"{req.get('district','Selected district')} / {r.get('sourceState',req.get('state',''))} / {r['season']}"))
        story.append(table(['Yield rate','Production','Rice-planted scenario area'],[[number(y)+' t/ha',number(tonnes)+' tonnes',number(area,2)+' ha']]))
        story.append(p('Your field and weather','h'))
        rows=[['Prediction date',r['predictionDate']],['Total land',number(r.get('landAreaHa',req['areaHa']),2)+' ha'],
              ['Rice area at prediction',number(req['areaHa'],2)+' ha'],['Area in this export',number(area,2)+' ha']]
        names={'averageTemperatureC':'Average temperature (C)','seasonalRainfallMm':'Seasonal rainfall (mm)',
          'relativeHumidityPct':'Relative humidity (%)','windSpeedMps':'Wind speed (m/s)',
          'solarRadiationKwhM2Day':'Daily solar radiation (kWh/m2)'}
        rows += [[names.get(k,k),number(v,2)] for k,v in r.get('suppliedWeather',{}).items()]
        story.append(table(['Input','Value'],rows,[width*.63,width*.37]))
        story.append(p('Calculation','h'))
        story.append(p(f"Yield {number(y,6)} t/ha x area {number(area,2)} ha = {number(tonnes,6)} tonnes\n"
          f"Mass = {number(tonnes,6)} tonnes x 1,000 = {number(kg,3)} kg"))
        story.append(p(f"Gross value = {number(kg,3)} kg x INR {number(price,2)}/kg = INR {number(kg*price,2)} (before costs)." if price is not None else 'No selling price supplied. Gross value is not calculated.'))
        if area!=float(req['areaHa']):story.append(p('The export uses the adjusted output-area scenario. The yield rate is unchanged; the model was not re-run.','small'))
        story.append(p('Current-season scenario, not a validated live-weather or farm-level forecast. Unspecified weather uses saved training-season references.','small'))
        story.append(PageBreak());heading('02 / model audit','How the estimate was derived')
        synthetic=r.get('referenceKind')=='synthetic_neighbour_transfer'
        story.append(table(['Model','Reference origin'],[[r['model'],'Neighbour-derived synthetic transfer' if synthetic else 'Local measured training-season references']]))
        story.append(p(f"{r['referenceCount']} reference records. Saved median imputation, numerical standardization and state/season one-hot encoding are reused; all transforms were fitted on training data only."))
        if synthetic:
            story.append(p('This district-season estimate uses a separate neighbour-augmented predictor. Synthetic transfer does not establish measured accuracy for the selected district.','small'))
            donors=r.get('neighbourDonors') or r.get('donors')
            if donors:story.append(p('Donor provenance is retained in the app prediction flow.','small'))
        story.append(p('Largest model-feature contributions','h'))
        contributions=sorted(r.get('contributions',[]),key=lambda v:abs(v['contribution']),reverse=True)
        story.append(table(['Feature','Signed contribution (t/ha)'],[[v['feature'],f"{v['contribution']:+.6f}"] for v in contributions[:10]],[width*.68,width*.32]))
        if r.get('modelKind')!='mlp':
            effect=sum(v['contribution'] for v in contributions)
            story.append(p(f"Baseline {number(r['baseline'],6)} + all signed contributions {effect:+.6f} = {number(y,6)} t/ha. The table shows the largest ten; the reconciliation uses all {len(contributions)} features."))
        story.append(p('Contributions describe the model calculation, not causal agronomic effects or percentages of responsibility. Area scales harvest quantity; selling price scales gross value. Neither changes t/ha.','small'))
        m=r['testMetrics'];story.append(p('Retrospective evaluation','h'))
        story.append(table(['MAE (t/ha)','RMSE (t/ha)','R-squared'],[[number(m['MAE']),number(m['RMSE']),number(m['R2'])]]))
        story.append(p('Held-out district-season evaluation, not a confidence interval for this result. Geographic-transfer results do not demonstrate accuracy in unobserved districts. Rice-photo screening does not adjust the predicted yield.','small'))
    if health_snapshot:
        if story:story.append(PageBreak())
        r=health_snapshot['result']; candidate=LABELS.get(r['candidate'],r['candidate'])
        heading('03 / crop health' if yield_snapshot else '01 / crop health','Rice photo screening')
        story.append(p('Result uncertain' if r['uncertain'] else candidate,'h'))
        story.append(p(('Highest-scoring candidate: '+candidate+'. ') if r['uncertain'] else 'Candidate classification, not a confirmed diagnosis.'))
        with PILImage.open(io.BytesIO(base64.b64decode(health_snapshot['encoded'],validate=True))) as original:
            photo=ImageOps.exif_transpose(original).convert('RGB');photo.thumbnail((1600,1600))
            buffer=io.BytesIO();photo.save(buffer,format='JPEG',quality=92);buffer.seek(0)
            scale=min(width/photo.width,292/photo.height)
            pic=Image(buffer,width=photo.width*scale,height=photo.height*scale);pic.hAlign='LEFT'
            story.extend([pic,Spacer(1,8),p(f"User-supplied photograph / {r['width']} x {r['height']} pixels. Oriented for display; uncropped image embedded, without EXIF metadata.",'small')])
        best=max(s['score'] for s in r['scores'])
        story.append(table(['Candidate','Highest model score','Screening decision'],[[candidate,number(best*100,2)+'%','Uncertain / retake or seek advice' if r['uncertain'] else 'Candidate label returned']]))
        if r.get('warnings'):story.append(p('Photo quality: '+' '.join(r['warnings'])))
        story.append(p('Scores are model outputs, not calibrated diagnostic confidence. Other crops and unsupported conditions are not reliably rejected. Consult an agricultural expert for confirmation.','small'))
        story.append(PageBreak());heading('04 / image audit' if yield_snapshot else '02 / image audit','Screening scores and method')
        story.append(table(['Class','Model score','Output logit'],[[LABELS.get(v['label'],v['label']),number(v['score']*100,3)+'%',number(r['logits'][i],6)] for i,v in enumerate(r['scores'])],[width*.52,width*.23,width*.25]))
        story.append(p('Inference pipeline','h'))
        story.append(p('Model: '+r['model']))
        story.append(p('Orientation correction > RGB > bicubic resize shorter edge to 256 > centre crop 224 x 224 > ImageNet normalization > EfficientNet-B0 > ten logits > softmax.'))
        story.append(p('Softmax: score(i) = exp(logit(i) - max(logits)) / sum(exp(logit(j) - max(logits))).'))
        story.append(p(f"The screening guard marks the result uncertain below a {number(r['threshold']*100,0)}% highest score or when basic image-quality warnings occur. This guard is a heuristic, not a calibrated diagnostic threshold."))
        story.append(p('Image pixels alone determine class scores. District, season and weather are not classifier inputs. No symptom heatmap or disease-related yield-loss estimate is inferred.','small'))
        m=r['testMetrics'];story.append(p(f"Held-out ten-class accuracy {number(m['accuracy']*100,2)}%; macro-F1 {number(m['macro_F1']*100,2)}%. These aggregate test metrics are not confidence for the pictured plant.",'small'))
    def page(canvas,doc):
        canvas.saveState();canvas.setFillColor(BG);canvas.rect(0,0,page_width,page_height,fill=1,stroke=0)
        if logo and Path(logo).is_file():canvas.drawImage(str(logo),44,page_height-54,width=23,height=23,mask='auto')
        canvas.setFillColor(INK);canvas.setFont('Helvetica-Bold',14);canvas.drawString(75,page_height-47,'paddy')
        canvas.setFillColor(MUTED);canvas.setFont('Helvetica',8);canvas.drawRightString(page_width-44,page_height-45,'FIELD RECORD / '+now.strftime('%d %b %Y'))
        canvas.setStrokeColor(LINE);canvas.line(44,page_height-66,page_width-44,page_height-66);canvas.line(44,39,page_width-44,39)
        canvas.setFillColor(MUTED);canvas.setFont('Helvetica',7.5);canvas.drawString(44,25,'Paddy '+VERSION+' | Local model output | '+now.strftime('%d %b %Y, %H:%M IST'))
        canvas.drawRightString(page_width-44,25,'PAGE '+str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=44,leftMargin=44,topMargin=88,bottomMargin=55,
      title='Paddy - '+('Yield and crop health' if yield_snapshot and health_snapshot else 'Yield prediction' if yield_snapshot else 'Crop health screening'),author='Paddy',pageCompression=1)
    doc.build(story,onFirstPage=page,onLaterPages=page)
    return output.getvalue()

class ReportSession:
    """Keep only the last successful snapshots and the matching photo in memory."""
    def __init__(self,engine,logo=None):self.engine=engine;self.logo=logo;self.lock=threading.Lock();self.yield_record=None;self.health_record=None
    def predict_seasonal_yield(self,request):
        result=self.engine.predict_seasonal_yield(request)
        if result.get('ok'):
            result={**result,'exportId':uuid.uuid4().hex}
            with self.lock:self.yield_record=copy.deepcopy({'request':request,'result':result})
        return result
    def classify_image(self,encoded):
        result=self.engine.classify_image(encoded)
        if result.get('ok'):
            result={**result,'exportId':uuid.uuid4().hex}
            with self.lock:self.health_record={'encoded':encoded,'result':copy.deepcopy(result)}
        return result
    def create(self,options):
        if not isinstance(options,dict):raise ValueError('Invalid report request.')
        mode=options.get('mode')
        if mode not in ('yield','health','combined'):raise ValueError('Choose a report type.')
        with self.lock:
            y=copy.deepcopy(self.yield_record) if mode in ('yield','combined') else None
            h=copy.deepcopy(self.health_record) if mode in ('health','combined') else None
        for record,field,needed in ((y,'yieldId',mode in ('yield','combined')),(h,'healthId',mode in ('health','combined'))):
            if needed and (not record or options.get(field)!=record['result']['exportId']):
                raise ValueError('This result is no longer current. Run it again before exporting.')
        return build_pdf(y,h,options.get('scenario'),self.logo)
