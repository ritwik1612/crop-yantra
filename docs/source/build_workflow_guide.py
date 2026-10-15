"""Build the reviewed project workflow PDF using ReportLab vector diagrams."""
from pathlib import Path
import csv
from collections import Counter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'docs' / 'Crop_Workflow.pdf'
GREEN = HexColor('#174B3A')
TEAL = HexColor('#2D7966')
INK = HexColor('#233B36')
PALE = HexColor('#EFF5F0')
GOLD = HexColor('#B27B2C')
styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyX', fontName='Helvetica', fontSize=10, leading=14, textColor=INK, spaceAfter=9))
styles.add(ParagraphStyle(name='SmallX', parent=styles['BodyX'], fontSize=8.5, leading=11, spaceAfter=5))
styles.add(ParagraphStyle(name='TitleX', fontName='Helvetica-Bold', fontSize=27, leading=32, textColor=GREEN, spaceAfter=18))
styles.add(ParagraphStyle(name='HeadX', fontName='Helvetica-Bold', fontSize=17, leading=21, textColor=GREEN, spaceAfter=14))
styles.add(ParagraphStyle(name='SubX', fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=TEAL, spaceBefore=8, spaceAfter=6))
styles.add(ParagraphStyle(name='BoxX', fontName='Helvetica', fontSize=9, leading=12, textColor=INK, alignment=TA_CENTER))
styles.add(ParagraphStyle(name='KickerX', fontName='Helvetica-Bold', fontSize=9, leading=12, textColor=GOLD, spaceAfter=10))

def p(text, style='BodyX'):
    return Paragraph(text, styles[style])

story = []
def add(text, style='BodyX'):
    story.append(p(text, style))
def page(kicker, title):
    if story:
        story.append(PageBreak())
    add(kicker.upper(), 'KickerX')
    add(title, 'HeadX')
def table(headers, rows, widths):
    data = [[p(h, 'SmallX') for h in headers]] + [[p(str(v), 'SmallX') for v in row] for row in rows]
    t = Table(data, colWidths=widths, hAlign='LEFT')
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), PALE), ('TEXTCOLOR',(0,0),(-1,0),GREEN),
        ('VALIGN',(0,0),(-1,-1),'TOP'), ('BOTTOMPADDING',(0,0),(-1,-1),7),
        ('TOPPADDING',(0,0),(-1,-1),7), ('LEFTPADDING',(0,0),(-1,-1),8),
        ('RIGHTPADDING',(0,0),(-1,-1),8), ('LINEBELOW',(0,0),(-1,0),1,TEAL),
        ('LINEBELOW',(0,1),(-1,-1),0.3,HexColor('#DAE4DD')),
    ]))
    story.append(t)
    story.append(Spacer(1,10))

class Diagram(Flowable):
    def __init__(self, height, boxes, edges):
        super().__init__()
        self.width, self.height = 499, height
        self.boxes, self.edges = boxes, edges
    def draw(self):
        c = self.canv
        for src, dst in self.edges:
            a, b = self.boxes[src], self.boxes[dst]
            x1,y1 = a[0]+a[2]/2, a[1]
            x2,y2 = b[0]+b[2]/2, b[1]+b[3]
            c.setStrokeColor(TEAL); c.setLineWidth(1.3)
            mid = (y1+y2)/2
            c.line(x1,y1,x1,mid); c.line(x1,mid,x2,mid); c.line(x2,mid,x2,y2+5)
            c.setFillColor(TEAL)
            path = c.beginPath(); path.moveTo(x2,y2); path.lineTo(x2-3.5,y2+6); path.lineTo(x2+3.5,y2+6); path.close()
            c.drawPath(path, fill=1, stroke=0)
        for x,y,w,h,text in self.boxes.values():
            c.setFillColor(PALE); c.setStrokeColor(TEAL)
            c.roundRect(x,y,w,h,7,fill=1,stroke=1)
            para=p(text,'BoxX'); _, ph=para.wrap(w-16,h-10)
            if ph > h-8:
                raise ValueError(f'Diagram label exceeds box: {text}')
            para.drawOn(c,x+8,y+(h-ph)/2)

with (ROOT/'DATASET/merged/rice_master.csv').open(newline='',encoding='utf-8') as f:
    records=list(csv.DictReader(f))
states=Counter(r['STATE'] for r in records)
seasons=Counter(r['SEASON'] for r in records)

page('Project guide | 08 October 2026', 'Rice yield prediction for South India')
add('Data, preprocessing and model workflow', 'TitleX')
add('R Ritwik - 23BAI0037<br/>Joshith G - 23BAI0075', 'SubX')
add('This guide explains where our data comes from, how we combine it, what enters the preprocessing model, what training will use, and how the application will turn user inputs into a yield estimate.')
table(['Verified dataset','Current scope'],[
    ('3 source families','Government crop statistics + GADM boundaries + NASA POWER weather'),
    ('2,018 observations / 30 columns','Rice, four states, crop years 2001-2019'),
    ('Prediction target','YIELD, measured in tonnes per hectare (t/ha)'),
    ('Execution status','Master and six training CSVs generated and verified. DAE fitted for 180 epochs. Supervised yield models have definitions but are not trained. Beta UI uses illustrative outputs.'),
], [155,344])
add('Models we will use', 'SubX')
table(['Model / method','Role and learning objective'],[
    ('SimpleImputer (median), StandardScaler, OneHotEncoder','Conventional preprocessing; training-set medians, means/scales and category mappings.'),
    ('Denoising Autoencoder (DAE)','Implemented DL preprocessing stage. Reconstruct 21 clean predictors from lightly corrupted inputs; learn 8 latent features.'),
    ('Gradient-boosted decision trees (GBDT)','Planned tabular baseline using HistGradientBoostingRegressor; learn nonlinear predictor-to-yield relationships.'),
    ('Multilayer Perceptron (MLP) regressor','Initial tabular DL predictor: latent/context inputs -> dense layers 64 and 32 -> one yield output. Defined, not trained.'),
    ('Long Short-Term Memory (LSTM); One-dimensional CNN (1D CNN)','Paper-based sequence experiments after time-series tensor preparation. Learn weather patterns over the crop season. Defined, not trained.'),
], [155,344])
add('The current data supports yield estimation. Direct disease classification, nutrient diagnosis, and image segmentation require additional labelled data.', 'SmallX')

page('01 | Original sources', 'Three raw sources, five construction tables')
table(['Source / preserved file','Contents and contribution'],[
    ('Government crop statistics<br/>government/crop_statistics.csv<br/>(originally APY.csv)','State, district, crop, crop year, season, reported area and production. We derive rice yield = production / area.'),
    ('GADM 4.1 administrative level 2<br/>boundaries/india_districts.csv','District names, identifiers and representative coordinates. Full geometry is preserved in boundary_coordinates.csv, linked by GID_2.'),
    ('NASA POWER Daily API extract<br/>weather/daily_weather.csv','Daily temperature, relative humidity, wind, precipitation, radiation, surface pressure and evapotranspiration proxy, queried at matched district locations. Vapour pressure is calculated from temperature and humidity.'),
], [210,289])
add('These preserved files live under <b>DATASET/raw/</b>. Their contents match the original project copies. The weather CSV is an assembled API extract. It is not a second government label dataset. Preserve raw files without editing.')
add('Temporary join tables - no extra user-facing datasets', 'SubX')
table(['File','Contents'],[
    ('YIELD_NUTS2_SOUTH_INDIA_RICE.csv','3,554 rice labels; yield, production, year, season and district ID.'),
    ('CROP_AREA_NUTS2_SOUTH_INDIA_RICE.csv','Rice cultivated area for each district-year-season.'),
    ('AREA_FRACTIONS_NUTS2_SOUTH_INDIA_RICE.csv','District rice area / recorded state rice area, for the same year and season.'),
    ('CENTROIDS_NUTS2_SOUTH_INDIA.csv','District crosswalk, coordinates and match status.'),
    ('METEO_DAILY_NUTS2_SOUTH_INDIA.csv','Daily weather used for season-specific aggregation.'),
], [280,219])
add('The raw crop selection yields 66,172 valid four-state records across crops; our final experiment selects rice. The builder creates the five join products temporarily, then removes temporary files automatically. The only retained merged CSV is <b>DATASET/merged/rice_master.csv</b>. Netherlands data contributes no rows. FAPAR, soil, elevation and WOFOST variables are not currently included.')
add('Source links', 'SubX')
add('<link href="https://data.gov.in/resource/district-wise-season-wise-crop-production-statistics-1997" color="#2D7966">Government crop-statistics resource</link> | <link href="https://gadm.org/data.html" color="#2D7966">GADM data</link> | <link href="https://power.larc.nasa.gov/docs/services/api/temporal/daily/" color="#2D7966">NASA POWER Daily API</link>', 'SmallX')

page('02 | Data lineage diagram', 'From downloads to preprocessed training files')
story.append(Diagram(550,{
    'a':(0,485,155,60,'<b>Download APY.csv</b><br/>Crop area + production<br/>Government statistics'),
    'b':(172,485,155,60,'<b>Download GADM 4.1</b><br/>District geometries<br/>Match names + locations'),
    'c':(344,485,155,60,'<b>Query NASA POWER</b><br/>Matched coordinates<br/>Save daily weather CSV'),
    'd':(45,398,410,60,'<b>Construct five input tables</b><br/>Rice labels + area + area fraction + coordinates + daily weather<br/>Normalize names; reject invalid area/production records'),
    'e':(45,301,410,70,'<b>Merge and aggregate</b><br/>Join district ID + crop year + season; map weather dates<br/>Seasonal means/totals + GDD + five derived predictors<br/>Require matched district and at least 60 valid weather days'),
    'f':(45,220,410,55,'<b>Consolidated master CSV</b><br/>2,018 district-year-season rice observations | 30 columns'),
    'g':(45,131,410,60,'<b>Split before fitting transforms</b><br/>Train 2001-2015 | Validation 2016-2017 | Test 2018-2019<br/>Median imputation + standardization; state/season encoding'),
    'h':(45,38,410,65,'<b>DAE feature learning: 21 -> 64 -> 32 -> 8</b><br/>Fit weights on training predictors; transform all three splits<br/>Export 8 latent features + encoded context + label/metadata'),
}, [('a','d'),('b','d'),('c','d'),('d','e'),('e','f'),('f','g'),('g','h')]))
add('Verified outputs: DATASET/training/standard/{train,validation,test}.csv and DATASET/training/autoencoder/{train,validation,test}.csv. Models live in pre-processing/artifacts/; plots/reports live in docs/. Raw sources are preserved separately.', 'SmallX')

page('03 | Merge rules and feature dictionary', 'What the 30 master columns represent')
add('The builder joins yield, area and area fraction using <b>IDREGION + FYEAR + SEASON</b>. It joins district coordinates by IDREGION and selects weather by district and date. Each output row describes one rice observation, not one day or one farm.')
table(['Group','Exact column names and meaning'],[
    ('Identity / context','CROP; IDREGION; STATE; DISTRICT; FYEAR; SEASON. Observation identity, location and crop-calendar context.'),
    ('Label / reported production','YIELD (t/ha); PRODUCTION_TONNES (tonnes). Yield is the prediction label; production is provenance only.'),
    ('Crop area','CROP_AREA (ha); AREA_FRACTION (district share of state-season rice area); CROP_AREA_LOG1P (log(1 + area)).'),
    ('Location / matching','CENTROID_X (longitude); CENTROID_Y (latitude); MATCH_STATUS (district-name crosswalk status).'),
    ('Weather coverage','WEATHER_DAY_COUNT: number of valid daily records used.'),
    ('Temperature','TMAX_MEAN, TMIN_MEAN, TAVG_MEAN (degrees C); TEMP_RANGE_MEAN = max mean - min mean; GDD_BASE10 = sum(max(TAVG - 10, 0)).'),
    ('Atmospheric conditions','VPRES_MEAN (hPa), WSPD_MEAN (m/s), RELH_MEAN (%), PS_MEAN (kPa).'),
    ('Season totals','PREC_TOTAL (mm), ET0_TOTAL (mm land-evaporation proxy), RAD_TOTAL (sum of daily radiation, kWh/m2 for the original RE-community API query).'),
    ('Derived interactions','WATER_BALANCE_PROXY = PREC_TOTAL - ET0_TOTAL; RAIN_PER_GDD = rainfall / GDD; RADIATION_PER_GDD = radiation / GDD. Zero GDD uses zero for ratios in the current builder.'),
], [125,374])
add('Weather season assumptions', 'SubX')
add('Kharif: June-November. Rabi: preceding November-April. Summer: March-June. Autumn: September-December. Winter: preceding December-March. These are approximate month windows, not district-specific recorded sowing dates.')
add('The builder calculates source-derived features and retains actual label observations. Calling this dataset synthetic would misdescribe how it was made. ET0 uses NASA EVLAND land evaporation as a proxy; it is not a calibrated FAO-56 reference ET estimate. API unit metadata was checked: the RE-community radiation values are kWh/m2/day, so their seasonal sum is kWh/m2.', 'SmallX')

page('04 | Preprocessing and column selection', 'What changes, what is excluded, what is learned')
table(['Stage','Input -> processing -> output'],[
    ('Split','2,018 rows -> chronological partition -> 1,485 train / 245 validation / 288 test.'),
    ('Median imputation','21 numeric columns -> fit medians using training rows -> fill missing values consistently in every split.'),
    ('StandardScaler','Imputed numeric values -> fit training mean and standard deviation -> comparable z-score inputs.'),
    ('OneHotEncoder','STATE and SEASON -> fit training categories -> categorical indicator columns. Unseen categories are ignored by the current encoder.'),
    ('DAE training','21 standardized predictors + small Gaussian corruption -> reconstruction objective -> 8 learned latent features. Clean inputs are the reconstruction targets; yield is not used.'),
    ('DAE export','Apply fitted encoder without training noise -> AE_LATENT_01 to AE_LATENT_08; reconstruction MSE; encoded categories; retained label and identifiers.'),
], [125,374])
add('The 21 numeric inputs', 'SubX')
add('CROP_AREA, AREA_FRACTION, CENTROID_X, CENTROID_Y, WEATHER_DAY_COUNT, TMAX_MEAN, TMIN_MEAN, TAVG_MEAN, VPRES_MEAN, WSPD_MEAN, PREC_TOTAL, ET0_TOTAL, RAD_TOTAL, RELH_MEAN, PS_MEAN, GDD_BASE10, TEMP_RANGE_MEAN, WATER_BALANCE_PROXY, RAIN_PER_GDD, RADIATION_PER_GDD, CROP_AREA_LOG1P.', 'SmallX')
add('Columns excluded from model inputs', 'SubX')
table(['Column(s)','Reason / treatment'],[
    ('PRODUCTION_TONNES','Excluded to prevent leakage: production/area defines the yield target.'),
    ('YIELD','Kept as the supervised label, excluded from preprocessing-model inputs.'),
    ('CROP','Constant rice crop in this cohort; retained only in the master.'),
    ('IDREGION, DISTRICT','Identifiers; retain for tracing predictions, exclude from encoder inputs.'),
    ('FYEAR','Defines chronological splits; not an encoder input in this implementation.'),
    ('MATCH_STATUS','Provenance only; not a predictor.'),
], [165,334])
add('No master columns are physically deleted. The deep CSV replaces the 21 explicit numeric predictors with 8 latent columns and retains selected metadata. Both current representations use the same 21 original numeric predictors and the same observation splits. Conventional exports have 28 predictor columns; DAE exports have 16 including reconstruction error.', 'SmallX')

page('05 | Findings and evidence', 'What preprocessing has taught us so far')
table(['Measured from the current master','Finding'],[
    ('Cohort filtering','3,554 rice labels -> 2,018 usable master rows. 1,536 label rows do not enter the final matched/covered cohort; the current builder does not export a per-reason rejection audit.'),
    ('State coverage','Andhra Pradesh: 572; Karnataka: 722; Tamil Nadu: 612; Telangana: 112. Coverage is unequal.'),
    ('Season coverage','Kharif: 1,037; Rabi: 492; Summer: 345; Winter: 75; Autumn: 69.'),
    ('Time coverage','2001-2019. Training: 2001-2015; validation: 2016-2017; test: 2018-2019.'),
], [160,339])
add('What the generated preprocessing plots show', 'SubX')
add('Coverage charts show imbalance. Yield distributions and annual curves reveal unusual values and temporal patterns. Correlation charts show associations and redundant features. Raw-versus-standardized histograms demonstrate the effect of scaling, not improved accuracy.')
add('What the DAE learns and how we assess it', 'SubX')
add('The encoder learns numerical dependencies among weather, location and crop predictors. Training/validation reconstruction losses assess how well it reproduces the clean standardized inputs. Reconstructed-versus-original plots show where it loses information. High reconstruction error means the representation fits that row poorly; it does not prove a source error or diagnose disease.')
add('The eight latent dimensions have learned numerical meaning. We cannot claim that one is drought, another is nutrient deficiency, or that lower reconstruction loss guarantees better yield estimates.')
add('Measured DAE run and remaining evaluation', 'SubX')
add('The DAE completed 180 epochs. Validation chose epoch 178 with reconstruction MSE <b>0.07724</b> in standardized feature units. All exported predictors are finite, labels and chronological splits are preserved, and the master has no missing cells or duplicate district-year-season keys. Supervised yield accuracy and superiority over the reference paper have not been established.')
add('Autumn and Winter are absent from training years. Their season categories map to zero under the current encoder rule. Evaluate those seasons separately; a pooled score alone can hide this generalization limit.', 'SmallX')
add('Compare identical test rows using MAE (t/ha), RMSE (t/ha), R2, and state/season errors. Use validation for selecting model settings. Our Indian rice results cannot directly be ranked against European crops tested on different datasets.')
add('Important data assumptions', 'SubX')
add('District weather is reanalysis, not farm sensor data. Coordinates currently average boundary vertices. Partial-season coverage can bias totals despite the 60-day rule. Full-season weather and reported area support retrospective estimation; early forecasts need predictors restricted to the forecast date.', 'SmallX')

page('05A | Generated evidence', 'Raw values and standardized model inputs')
story.append(Image(str(ROOT/'docs/figures/05_raw_vs_standardized_features.png'),width=470,height=509))
add('These are actual training observations before and after StandardScaler. Differences in shape or scale illustrate transformations; they are not proof of higher prediction accuracy. Imputation/scaling parameters come only from training years.', 'SmallX')

page('05B | Generated evidence', 'DAE learning and reconstruction')
story.append(Image(str(ROOT/'docs/figures/07_autoencoder_training_loss.png'),width=475,height=267))
story.append(Spacer(1,12))
story.append(Image(str(ROOT/'docs/figures/06_autoencoder_reconstruction.png'),width=475,height=198))
add('Actual 180-epoch run; best validation checkpoint: epoch 178. The dashed diagonal indicates perfect reconstruction for the selected raw-unit features. These plots evaluate feature reconstruction. Yield accuracy still requires supervised-model training and held-out tests.', 'SmallX')

page('06 | Training architecture diagram', 'How preprocessed data becomes a yield model')
story.append(Diagram(450,{
    'a':(45,387,410,58,'<b>Chronological training split + YIELD labels</b><br/>All fitted preprocessing parameters come from training data'),
    'b':(0,282,238,75,'<b>Conventional arm</b><br/>21 standardized predictors + encoded state/season<br/>Same master rows and predictor availability'),
    'c':(261,282,238,75,'<b>DAE arm</b><br/>8 latent features + encoded state/season<br/>Optional reconstruction error'),
    'd':(0,176,238,77,'<b>GBDT baseline / comparison</b><br/>Learn nonlinear splits and feature interactions<br/>Fit both representations for a controlled comparison'),
    'e':(261,176,238,77,'<b>MLP tabular DL regressor</b><br/>Input -> Dense 64 -> Dense 32 -> Yield<br/>Learn latent/context relationships with yield'),
    'f':(45,82,410,64,'<b>Validation, then held-out test</b><br/>Tune on 2016-2017; evaluate once on 2018-2019<br/>MAE / RMSE / R2 + state and season errors'),
    'g':(45,0,410,52,'<b>Selected model + saved preprocessing</b><br/>Deploy only after evaluating its performance'),
}, [('a','b'),('a','c'),('b','d'),('c','d'),('c','e'),('d','f'),('e','f'),('f','g')]))
add('Paper-based sequence experiment', 'SubX')
add('Prepare district-season sequences from daily/dekad weather using the same observation split. <b>LSTM</b> learns patterns across successive weather steps; <b>1D CNN</b> learns local time-window patterns with temporal filters. Combine their sequence representation with static/context inputs and a regression head. These sequence tensors and forecasting trainers are planned work; the master CSV alone is not a weather sequence.')
add('The DAE is an adapted implementation of the established Vincent et al. preprocessing method. The LSTM/1D CNN experiments follow the model families in Paudel et al. (2023); this is an Indian-data adaptation, not an exact replication of its European multimodal experiment.', 'SmallX')

page('07 | Application flow diagram', 'What the user enters and what they receive')
story.append(Diagram(490,{
    'a':(45,420,410,65,'<b>User inputs</b><br/>State + district, rice season + crop year, crop area (ha)<br/>Weather upload or supported historical-data selection'),
    'b':(45,334,410,58,'<b>Resolve context and validate request</b><br/>Check location, dates, units, required fields and weather coverage<br/>If required data is absent, request it before prediction'),
    'c':(45,244,410,62,'<b>Create predictors with the training definitions</b><br/>Fetch/parse weather; aggregate by season; derive GDD and ratios<br/>Obtain coordinates and state-season area total if fraction is used'),
    'd':(45,154,410,62,'<b>Apply saved preprocessing</b><br/>Training-fitted imputer/scaler + category encoder<br/>Saved DAE encoder -> latent representation'),
    'e':(45,72,410,54,'<b>Run selected trained yield regressor</b><br/>GBDT or MLP; sequence models require prepared weather tensors'),
    'f':(45,0,410,46,'<b>User output</b><br/>Estimated rice yield (t/ha) + coverage/context information'),
}, [('a','b'),('b','c'),('c','d'),('d','e'),('e','f')]))
add('The user does not enter a known yield or observed production. The service calculates derived inputs; district names identify the request but are not numerical encoder features. AREA_FRACTION requires a corresponding state-season rice-area denominator: obtain that context or redesign/retrain the feature set.', 'SmallX')
add('Optional output: estimated production = predicted yield x user crop area. This is derived from the prediction, not an input. Confidence/risk bands need a separately validated uncertainty method. Current data cannot produce a crop disease label.', 'SmallX')

page('08 | Files, reproducibility and references', 'Where everything lives and what remains to build')
add('Project navigation', 'SubX')
table(['Folder','Purpose'],[
    ('APP/','Implementation and existing application scaffold.'),
    ('DATASET/raw/','Three preserved source files; clear government/boundaries/weather names.'),
    ('DATASET/merged/','Only rice_master.csv and its README; 2,018 rows x 30 columns.'),
    ('DATASET/training/','standard/ and autoencoder/ split CSVs plus predictor manifest.'),
    ('pre-processing/','Dataset builders and preprocessing scripts.'),
    ('docs/','Current guide, reports and reference papers; source/ contains this PDF generator.'),
    ('github/','GitHub working copy and repository-related files.'),
    ('OTHER/archive/','Superseded material, recoverable and excluded from training/GitHub.'),
], [205,294])
add('Files consumed by supervised training', 'SubX')
add('Conventional: DATASET/training/standard/train.csv, validation.csv, test.csv. Deep: DATASET/training/autoencoder/train.csv, validation.csv, test.csv. Select predictor columns explicitly using DATASET/training/manifest.json and separate YIELD. Only train.csv fits supervised weights; validation selects settings; test measures final performance.', 'SmallX')
add('Next implementation steps', 'SubX')
add('Preprocessing is executed and verified. APP/models/ contains GBDT, MLP, LSTM and 1D CNN definitions. Next: implement supervised trainers and sequence preparation; evaluate held-out years; save the selected predictor; connect it to the beta UI. The prototype is available at APP/prototype/index.html and uses fixed, explicitly illustrative yield outputs.', 'SmallX')
add('Hyperlinked references', 'SubX')
add('1. <link href="https://doi.org/10.1016/j.compag.2023.107663" color="#2D7966">Paudel et al. (2023), Interpretability of deep learning models for crop yield forecasting.</link><br/>2. <link href="https://www.cs.toronto.edu/~larocheh/publications/icml-2008-denoising-autoencoders.pdf" color="#2D7966">Vincent et al. (2008), Extracting and Composing Robust Features with Denoising Autoencoders.</link><br/>3. <link href="https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.HistGradientBoostingRegressor.html" color="#2D7966">scikit-learn HistGradientBoostingRegressor documentation.</link><br/>4. <link href="https://github.com/ritwik1612/crop-yantra" color="#2D7966">Project dataset repository.</link><br/>5. <link href="https://doi.org/10.5281/zenodo.5561113" color="#2D7966">European reference dataset record - background only.</link>', 'SmallX')

page('09 | Reproduce and show the beta', 'A simple entry point for the team')
add('Read docs/README.md, then use these commands from the project or GitHub clone root:', 'SubX')
add('python -m pip install -r pre-processing/requirements.txt<br/>python pre-processing/run_pipeline.py --epochs 180<br/>python pre-processing/verify_outputs.py<br/>python -m http.server 8765 --directory APP/prototype', 'SmallX')
add('Open http://localhost:8765 for Verdant, the green/off-white beta. Overview shows source and dataset counts; Yield preview demonstrates user input and result cards; Data pipeline explains files; Models &amp; learning names every method and its role.')
add('The beta is a frontend demonstration. Its displayed 4.20 t/ha is fixed and explicitly labelled illustrative; multiplying it by entered area produces illustrative tonnes. No trained yield model runs in the prototype.')
add('Checklist', 'SubX')
table(['Requested item','Delivered / status'],[
    ('Sources, counts, contents, merge and column exclusions','Documented here, in source code and dataset READMEs.'),
    ('Full preprocessing model and trainable outputs','DAE fitted; standard and DAE CSVs verified; checkpoint and transforms saved.'),
    ('Three end-to-end diagrams','Data construction; training architecture; user computation flow.'),
    ('Exact computation model names','HistGradientBoostingRegressor (GBDT), MLP, LSTM and 1D CNN; supervised weights are not yet trained.'),
    ('Clean local and GitHub structure','Active data has raw, merged and training stages. Historical local material is archived outside the workflow.'),
    ('Prototype without yield training','Verdant beta: navigation, dependent district selectors, form validation and illustrative result cards.'),
], [210,289])
add('The DAE is preprocessing; it does not itself predict crop yield. The selected supervised yield predictor will provide the application estimate after training and evaluation. LSTM/1D CNN require time-series inputs; MLP/GBDT use the prepared tabular representations.')

if (ROOT/'docs/figures/Beta_Preview.png').exists():
    page('10 | Verdant beta', 'The proposed application experience')
    story.append(Image(str(ROOT/'docs/figures/Beta_Preview.png'),width=499,height=334))
    story.append(Spacer(1,15))
    add('The verified demonstration selected Karnataka / Mandya, Kharif 2019, and 20 hectares. The result card shows fixed illustrative yield 4.20 t/ha and illustrative production 84 tonnes. This checks interface calculations only.')
    add('The sidebar includes Overview, Yield preview, Data pipeline and Models &amp; learning. The model screen explicitly names the DAE preprocessing network, conventional transforms, GBDT baseline, MLP regressor and future LSTM/1D CNN sequence models.')
    add('Open APP/prototype/index.html directly or serve it with the command on the previous page. No supervised yield weights or live weather service are connected to the beta.')

def footer(c, doc):
    c.setFillColor(GREEN); c.rect(0,A4[1]-15,A4[0],15,fill=1,stroke=0)
    c.setStrokeColor(HexColor('#DAE4DD')); c.line(48,43,A4[0]-48,43)
    c.setFont('Helvetica',8); c.setFillColor(TEAL)
    c.drawString(48,30,'SOUTH INDIA RICE | DATA & MODEL GUIDE')
    c.drawRightString(A4[0]-48,30,str(doc.page))

doc=SimpleDocTemplate(str(DEST),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=42,bottomMargin=55,
                      title='South India Rice: Data, Preprocessing and Model Workflow',author='R Ritwik; Joshith G')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
print(DEST)
