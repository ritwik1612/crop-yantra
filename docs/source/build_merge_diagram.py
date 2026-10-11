"""Render the verified source selection and merge as PNG and editable SVG."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/figures'
OUT.mkdir(parents=True, exist_ok=True)
W, H = 2400, 3760
image = Image.new('RGB', (W, H), '#f5f8f6')
draw = ImageDraw.Draw(image)
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
       '<rect width="100%" height="100%" fill="#f5f8f6"/>']
COLORS = ['#e6f0fa', '#e5f2eb', '#fff1df']

def text(x, y, value, size=28, bold=False, color='#173d32'):
    font = ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf', size)
    draw.text((x, y), value, font=font, fill=color)
    svg.append(f'<text x="{x}" y="{y+size}" font-family="Arial,sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(value)}</text>')

def box(x, y, width, height, title, lines, fill='#ffffff'):
    draw.rounded_rectangle((x,y,x+width,y+height), radius=18, fill=fill, outline='#b9cdc3', width=2)
    svg.append(f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="18" fill="{fill}" stroke="#b9cdc3" stroke-width="2"/>')
    text(x+28,y+24,title,32,True)
    for i, line in enumerate(lines): text(x+28,y+82+i*41,line)
    assert y+82+len(lines)*41 <= y+height+8, title

def arrow(x1,y1,x2,y2):
    segments = [(y1,y2)]
    for label_y in [730,1300,1810,2400,2720,3200]:
        updated = []
        for start,end in segments:
            if start < label_y+45 and end > label_y-8:
                if start < label_y-8: updated.append((start,label_y-8))
                if end > label_y+45: updated.append((label_y+45,end))
            else: updated.append((start,end))
        segments = updated
    for start,end in segments:
        draw.line((x1,start,x2,end),fill='#53776a',width=5)
        svg.append(f'<path d="M{x1},{start} L{x2},{end}" fill="none" stroke="#53776a" stroke-width="5"/>')
    draw.polygon([(x2,y2),(x2-11,y2-18),(x2+11,y2-18)],fill='#53776a')
    svg.append(f'<path d="M{x2-11},{y2-18} L{x2},{y2} L{x2+11},{y2-18}" fill="#53776a"/>')

def heading(y, label): text(60,y,label,34,True)

text(60,35,'HOW THREE RAW SOURCES BECOME ONE RICE DATASET',48,True)
text(60,104,'Feature selection, district matching, seasonal alignment and model input decisions',30)
xs=[60,840,1620]; cw=720
heading(168,'1. RAW SOURCE FIELDS')
box(xs[0],225,cw,470,'GOVERNMENT CROP STATISTICS',[
    'crop_statistics.csv', 'State, District, Crop, Crop_Year,',
    'Season, Area, Production, Yield', '',
    'One crop / district / year / season record.',
    'Area: hectares. Production: tonnes.',
    'Supplies crop context and the yield label.',
    'Header spaces are trimmed during mapping.'],COLORS[0])
box(xs[1],225,cw,470,'GADM DISTRICT BOUNDARIES',[
    'india_districts.csv: 676 districts',
    'GID_0, COUNTRY, GID_1, NAME_1,',
    'NL_NAME_1, GID_2, NAME_2, VARNAME_2,',
    'NL_NAME_2, TYPE_2, ENGTYPE_2, CC_2,',
    'HASC_2 + geometry type and coordinates.',
    'boundary_coordinates.csv: 275,432 vertices',
    'GID_2 links names to polygon/ring/vertex',
    'indexes, LONGITUDE and LATITUDE.'],COLORS[1])
box(xs[2],225,cw,470,'NASA DAILY WEATHER EXTRACT',[
    'daily_weather.csv',
    'IDCOVER, IDREGION, DATE,',
    'TMAX, TMIN, TAVG, VPRES, WSPD,',
    'PREC, ET0, RAD, RELH, PS', '',
    'One district / date record.',
    'Ten numerical weather channels.',
    'Extract includes derived vapour pressure.'],COLORS[2])
for x in xs: arrow(x+cw/2,700,x+cw/2,790)
heading(730,'2. SELECT AND PREPARE RELEVANT INFORMATION')
box(xs[0],800,cw,470,'KEEP RICE AND VALID CROP RECORDS',[
    'Choose AP, Karnataka, Tamil Nadu, Telangana.',
    'Choose Crop = rice or paddy.',
    'Require finite area > 0, production >= 0.',
    'Trim State, District and Season names.',
    'Crop_Year -> FYEAR; Area -> CROP_AREA.',
    'Production -> PRODUCTION_TONNES.',
    'Recompute YIELD = production / area.',
    '3,554 valid rice labels before alignment.',
    'Raw Yield is not copied into the master.'],COLORS[0])
box(xs[1],800,cw,470,'USE NAMES AND LOCATION',[
    'NAME_1 = state; NAME_2 = district.',
    'Normalize case, spaces and punctuation.',
    'Match state + normalized district first.',
    'If absent, use a district unique across',
    'the four states: historical-state crosswalk.',
    'Average boundary vertices -> longitude',
    'CENTROID_X and latitude CENTROID_Y.',
    'Keep MATCH_STATUS for audit.',
    'Other GADM codes/types stay in raw CSV.'],COLORS[1])
box(xs[2],800,cw,470,'USE DATE AND TEN WEATHER CHANNELS',[
    'IDREGION connects weather to district.',
    'DATE selects days for crop year + season.',
    'Use a day only when all 10 values are finite.',
    'IDCOVER is not a final predictor.',
    'ET0 is NASA EVLAND land evaporation.',
    'RAD is solar radiation in kWh/m2/day.',
    'VPRES is derived from temperature/humidity.',
    'Weather values are aggregated,',
    'not joined as individual daily model rows.'],COLORS[2])
for x in xs: arrow(x+cw/2,1275,x+cw/2,1360)
heading(1300,'3. LINK THE SOURCES USING DISTRICT ID AND SEASONAL DATES')
box(60,1370,2280,410,'CROP RECORD + MATCHED DISTRICT + WEATHER FOR THE SAME GROWING WINDOW',[
    'Create IDREGION = IND_<normalized government state>_<normalized government district>.',
    'Crop record + district location: join by IDREGION after the state/district name match.',
    'Crop area + area share + yield: join by (IDREGION, FYEAR, SEASON).',
    'Weather: match IDREGION, then select DATE within the season window for FYEAR.',
    'Kharif Jun-Nov; Rabi previous Nov-Apr; Summer Mar-Jun; Autumn Sep-Dec;',
    'Winter previous Dec-Mar; Whole Year Jan-Dec. These are fixed project calendar assumptions.',
    'Example actual key: IND_ANDHRAPRADESH_ADILABAD / 2001 / Kharif -> Jun-Nov 2001 weather.',
    'Retain matched location + finite yield + at least 60 complete weather days.'], '#edf3ef')
arrow(1200,1785,1200,1870)
heading(1810,'4. CALCULATE SEASONAL SUMMARIES AND ENGINEER FEATURES')
box(60,1880,1110,490,'WEATHER SUMMARIES: 11 NUMERICAL INPUTS',[
    'WEATHER_DAY_COUNT = number of complete days.',
    'Means: TMAX_MEAN, TMIN_MEAN, TAVG_MEAN,',
    'VPRES_MEAN, WSPD_MEAN, RELH_MEAN, PS_MEAN.',
    'Totals: PREC_TOTAL, ET0_TOTAL, RAD_TOTAL.',
    '',
    'Means describe typical seasonal conditions.',
    'Totals describe accumulated rain, evaporation and energy.',
    'Coverage count helps interpret the totals.',
    'Full-season summaries currently support retrospective',
    'estimation; pre-harvest forecasts need date cutoffs.'])
box(1230,1880,1110,490,'CROP, LOCATION AND DERIVED FEATURES: 10 INPUTS',[
    'CROP_AREA + CENTROID_X + CENTROID_Y.',
    'AREA_FRACTION = district area / state-year-season rice area.',
    'CROP_AREA_LOG1P = log(1 + crop area).',
    'GDD_BASE10 = sum(max(daily TAVG - 10, 0)).',
    'TEMP_RANGE_MEAN = TMAX_MEAN - TMIN_MEAN.',
    'WATER_BALANCE_PROXY = PREC_TOTAL - ET0_TOTAL.',
    'RAIN_PER_GDD = PREC_TOTAL / GDD_BASE10.',
    'RADIATION_PER_GDD = RAD_TOTAL / GDD_BASE10.',
    'GDD ratios are assigned 0 when GDD is 0.',
    'Captures area scale, heat, water and energy relationships.'])
arrow(1200,2375,1200,2460)
heading(2400,'5. MERGED MASTER: SAME DISTRICT / YEAR / SEASON OBSERVATIONS')
box(60,2470,2280,220,'rice_master.csv: 2,018 ROWS x 30 COLUMNS; YEARS 2001-2019',[
    '21 numerical inputs + 2 categorical inputs + 1 yield target + 6 provenance/identity fields.',
    'Feature choices follow crop/weather relevance, available data and leakage prevention.',
    'No statistical feature ranking has established that every selected feature improves prediction.'], '#e2efe7')
for x in xs: arrow(x+cw/2,2695,x+cw/2,2780)
heading(2720,'6. SELECT MODEL INPUTS WHILE KEEPING TARGET AND METADATA SEPARATE')
box(60,2790,cw,370,'USE AS PREDICTORS: 23 FIELDS',[
    '21 numerical fields listed above.',
    'STATE and SEASON provide region and',
    'growing-season context.',
    'Seven one-hot indicators are learned',
    'from training categories.',
    'No disease labels or imagery are present.'],COLORS[1])
box(840,2790,cw,370,'PREDICT THIS TARGET: 1 FIELD',[
    'YIELD = production / rice area.',
    'Unit: tonnes per hectare (t/ha).',
    'Preserve the same label for both',
    'standard and DAE experiments.',
    'Never put YIELD into the predictor',
    'inputs or DAE reconstruction target.'],COLORS[0])
box(1620,2790,cw,370,'EXCLUDE FROM INPUTS: 6 FIELDS',[
    'PRODUCTION_TONNES: leaks yield with area.',
    'CROP: always rice, no variation.',
    'IDREGION, DISTRICT: record identity.',
    'FYEAR: controls chronological splitting.',
    'MATCH_STATUS: matching audit.',
    'Keep all six in the master for traceability.'],COLORS[2])
arrow(420,3165,420,3260)
heading(3200,'7. SPLIT FIRST, THEN FIT PREPROCESSING ON TRAINING DATA ONLY')
box(60,3270,2280,160,'TRAIN 2001-2015: 1,485 | VALIDATION 2016-2017: 245 | TEST 2018-2019: 288',[
    'Training medians + scaling for 21 numerical inputs; train-fitted one-hot encoding for STATE and SEASON.'])
arrow(650,3435,650,3510); arrow(1750,3435,1750,3510)
box(60,3520,1110,190,'STANDARD: 28 PREDICTORS',[
    '21 scaled numerical values + 7 category indicators.',
    'Train MLP and boosted trees; evaluate held-out yield.'],COLORS[0])
box(1230,3520,1110,190,'DAE: 16 PREDICTORS',[
    '21 scaled values -> 8 latent + 7 indicators + 1 recon. MSE.',
    'Same rows/labels/models. Test whether DAE helps.'],COLORS[1])
image.save(OUT / 'Raw_Data_Feature_Selection_and_Merge.png')
svg.append('</svg>')
(OUT / 'Raw_Data_Feature_Selection_and_Merge.svg').write_text('\n'.join(svg),encoding='utf-8')
print('Created detailed PNG and editable SVG merge diagram')
