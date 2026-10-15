/** Reproducible nearest-district augmentation. Original sources/splits stay untouched. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {createRequire} from 'node:module';
import {fileURLToPath,pathToFileURL} from 'node:url';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const moduleBase=process.env.ARTIFACT_MODULE_BASE||path.join(root,'OTHER/augmentation_runtime');
const require=createRequire(path.join(moduleBase,'package.json'));
const {Workbook}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')).href);
const states={AndhraPradesh:'Andhra Pradesh',Karnataka:'Karnataka',TamilNadu:'Tamil Nadu',Telangana:'Telangana',Kerala:'Kerala',Puducherry:'Puducherry'};
const basePath=path.join(root,'DATASET/merged/rice_master.csv');
const boundariesPath=path.join(root,'DATASET/raw/boundaries/india_districts.csv');
const destination=path.join(root,'DATASET/augmented');
const sha=value=>createHash('sha256').update(value).digest('hex');
const key=value=>String(value).toUpperCase().replace(/[^A-Z0-9]/g,'');
const coordinate=row=>`${Number(row.CENTROID_X).toFixed(6)},${Number(row.CENTROID_Y).toFixed(6)}`;
const numeric=value=>value!==''&&value!==null&&Number.isFinite(Number(value));
const rounded=value=>Math.round(value*1e6)/1e6;
const csvCell=value=>{const text=value===null||value===undefined?'':String(value);return /[",\r\n]/.test(text)?'"'+text.replaceAll('"','""')+'"':text;};
async function readCSV(filename){
 const text=await fs.readFile(filename,'utf8');
 const workbook=await Workbook.fromCSV(text,{sheetName:'Source'});
 const matrix=workbook.worksheets.getItem('Source').getUsedRange().values;
 const headers=matrix[0].map(String);
 return {text,headers,rows:matrix.slice(1).filter(r=>r.some(v=>v!==null&&v!=='')).map(row=>Object.fromEntries(headers.map((name,i)=>[name,row[i]??''])))};
}
function distance(a,b){
 const radians=Math.PI/180,lat1=Number(a.CENTROID_Y)*radians,lat2=Number(b.CENTROID_Y)*radians;
 const dlat=lat2-lat1,dlon=(Number(b.CENTROID_X)-Number(a.CENTROID_X))*radians;
 const h=Math.sin(dlat/2)**2+Math.cos(lat1)*Math.cos(lat2)*Math.sin(dlon/2)**2;
 return 6371.0088*2*Math.asin(Math.sqrt(Math.min(1,h)));
}

const original=await readCSV(basePath),boundaries=await readCSV(boundariesPath);
const geo=boundaries.rows.filter(r=>states[r.NAME_1]);
const byCoordinate=new Map(geo.map(r=>[coordinate(r),r]));
const observedLocations=new Set(original.rows.map(coordinate));
const targets=geo.filter(r=>!observedLocations.has(coordinate(r)));
const rowKey=row=>[row.IDREGION,row.FYEAR,row.SEASON].join('|');
const groups=new Map();
// Only the existing 2001–2015 training years can contribute donor information.
for(const row of original.rows){
 if(Number(row.FYEAR)>2015||!['Kharif','Rabi','Summer'].includes(row.SEASON))continue;
 const gid=byCoordinate.get(coordinate(row))?.GID_2;if(!gid)continue;
 const groupKey=[gid,row.FYEAR,row.SEASON].join('|');
 if(!groups.has(groupKey))groups.set(groupKey,[]);groups.get(groupKey).push(row);
}
const byPeriod=new Map();let ambiguousDonorGroups=0;
for(const grouped of groups.values()){
 // An ambiguous source group must not count twice as two neighbouring districts.
 if(grouped.length!==1){ambiguousDonorGroups++;continue;}
 const row=grouped[0],period=[row.FYEAR,row.SEASON].join('|');
 if(!byPeriod.has(period))byPeriod.set(period,[]);byPeriod.get(period).push(row);
}
const estimatedFields=['YIELD','CROP_AREA','TMAX_MEAN','TMIN_MEAN','TAVG_MEAN','VPRES_MEAN','WSPD_MEAN','PREC_TOTAL','ET0_TOTAL','RAD_TOTAL','RELH_MEAN','PS_MEAN','GDD_BASE10'];
const generated=[],provenance=[];const skipped=[];
for(const target of targets){
 let count=0;
 for(const [period,pool] of [...byPeriod].sort(([a],[b])=>a.localeCompare(b))){
  const donors=pool.map(row=>({row,distance:distance(target,row)}))
   .filter(d=>d.distance<=250&&estimatedFields.every(field=>numeric(d.row[field])))
   .sort((a,b)=>a.distance-b.distance||rowKey(a.row).localeCompare(rowKey(b.row))).slice(0,3);
  if(donors.length!==3){skipped.push({gid:target.GID_2,period,reason:'fewer_than_3_donors_within_250km'});continue;}
  const inverse=donors.map(d=>1/Math.max(d.distance,1)**2),total=inverse.reduce((a,b)=>a+b,0);
  const weights=inverse.map(v=>v/total),[year,season]=period.split('|');
  const row=Object.fromEntries(original.headers.map(name=>[name,'']));
  Object.assign(row,{CROP:'Rice',IDREGION:`IND_${key(states[target.NAME_1])}_${key(target.NAME_2)}`,STATE:states[target.NAME_1],DISTRICT:target.NAME_2,FYEAR:Number(year),SEASON:season,
   CENTROID_X:rounded(Number(target.CENTROID_X)),CENTROID_Y:rounded(Number(target.CENTROID_Y)),MATCH_STATUS:'nearest_district_augmentation'});
  for(const field of estimatedFields)row[field]=rounded(donors.reduce((sum,d,i)=>sum+weights[i]*Number(d.row[field]),0));
  row.PRODUCTION_TONNES=rounded(row.YIELD*row.CROP_AREA);
  row.TEMP_RANGE_MEAN=rounded(row.TMAX_MEAN-row.TMIN_MEAN);
  row.WATER_BALANCE_PROXY=rounded(row.PREC_TOTAL-row.ET0_TOTAL);
  row.RAIN_PER_GDD=row.GDD_BASE10>0?rounded(row.PREC_TOTAL/row.GDD_BASE10):'';
  row.RADIATION_PER_GDD=row.GDD_BASE10>0?rounded(row.RAD_TOTAL/row.GDD_BASE10):'';
  row.CROP_AREA_LOG1P=rounded(Math.log1p(row.CROP_AREA));
  // Neither a real state rice-area denominator nor observed target weather-day
  // count is available. Preserve missingness instead of asserting observations.
  row.AREA_FRACTION='';row.WEATHER_DAY_COUNT='';
  generated.push(row);count++;
  provenance.push({record_key:rowKey(row),target_gid:target.GID_2,role:'experimental_training_candidate',
   donors:donors.map((d,i)=>({record_key:rowKey(d.row),gid:byCoordinate.get(coordinate(d.row)).GID_2,distance_km:rounded(d.distance),weight:weights[i]})),
   unavailable_fields:['AREA_FRACTION','WEATHER_DAY_COUNT'],estimated_fields:[...estimatedFields,'PRODUCTION_TONNES','TEMP_RANGE_MEAN','WATER_BALANCE_PROXY','RAIN_PER_GDD','RADIATION_PER_GDD','CROP_AREA_LOG1P']});
 }
 if(!count)throw Error(`No eligible periods for ${target.GID_2}; not claiming complete map coverage.`);
}
const mixed=[...original.rows,...generated].sort((a,b)=>String(a.STATE).localeCompare(String(b.STATE))||String(a.DISTRICT).localeCompare(String(b.DISTRICT))||Number(a.FYEAR)-Number(b.FYEAR)||String(a.SEASON).localeCompare(String(b.SEASON))||String(a.IDREGION).localeCompare(String(b.IDREGION)));
const keys=mixed.map(rowKey);if(new Set(keys).size!==keys.length)throw Error('Duplicate district/year/season record key');
const newCoordinates=new Set(mixed.map(coordinate));if(geo.some(r=>!newCoordinates.has(coordinate(r))))throw Error('Uncovered map district');
const outputBook=Workbook.create(),sheet=outputBook.worksheets.add('District data');
sheet.getRange('A1').write([original.headers,...mixed.map(row=>original.headers.map(name=>row[name]))]);
sheet.freezePanes.freezeRows(1);sheet.showGridLines=false;
sheet.getRange('A1:AD1').format={font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},fill:'#285B46'};
sheet.getRange('A2:AD8').format.font={name:'Arial',size:10};
sheet.getRange('A1:AD8').format.columnWidth=18;
sheet.getRange('B1:B8').format.columnWidth=46;
sheet.getRange('C1:D8').format.columnWidth=23;
sheet.getRange('H1:H8').format.columnWidth=30;
outputBook.recalculate();
console.log((await outputBook.inspect({kind:'table',range:'A1:J4',include:'values',tableMaxRows:4,tableMaxCols:10,maxChars:1800})).ndjson);
const matrix=sheet.getUsedRange().values;
const outputCSV=matrix.map(row=>row.map(csvCell).join(',')).join('\r\n')+'\r\n';
// Verify the complete round trip before replacing this task's generated output.
const roundTrip=await Workbook.fromCSV(outputCSV,{sheetName:'Verify'});
if(roundTrip.worksheets.getItem('Verify').getUsedRange().values.length!==mixed.length+1)throw Error('CSV row round trip mismatch');
for(const entry of provenance)entry.csv_record_number=keys.indexOf(entry.record_key)+1;
const byState={};for(const state of Object.values(states))byState[state]={map_districts:geo.filter(r=>states[r.NAME_1]===state).length,original_rows:original.rows.filter(r=>r.STATE===state).length,added_rows:generated.filter(r=>r.STATE===state).length};
const manifest={schema_version:1,source_csv:'DATASET/merged/rice_master.csv',source_sha256:sha(original.text),boundary_source:'GADM 4.1',boundary_sha256:sha(boundaries.text),
 output_csv:'rice_master_augmented.csv',output_sha256:sha(outputCSV),columns:original.headers.length,original_rows:original.rows.length,added_rows:generated.length,total_rows:mixed.length,
 original_geographic_districts:observedLocations.size,augmented_geographic_districts:newCoordinates.size,filled_map_districts:targets.length,
 method:'three nearest distinct available district centroids; inverse-distance-squared weighted average; same year and season; max 250 km',
 donor_years:[2001,2015],no_generated_donors:true,no_future_donors:true,no_random_noise:true,ambiguous_donor_groups_excluded:ambiguousDonorGroups,
 scope:'Experimental neighbour-estimated records, not measured target-district observations. Covers this historical map, not current district boundaries.',
 evaluation_policy:'Do not evaluate accuracy against generated labels. Original validation/test files and fitted preprocessing remain unchanged. Rebuild an experimental training representation separately; do not treat all rows as independent evidence.',by_state:byState,generated_records:provenance,skipped_periods:skipped};
await fs.mkdir(destination,{recursive:true});
await fs.writeFile(path.join(destination,'rice_master_augmented.csv'),outputCSV);
await fs.writeFile(path.join(destination,'generation_manifest.json'),JSON.stringify(manifest,null,2)+'\n');
await fs.mkdir(path.join(root,'OTHER/augmentation_runtime'),{recursive:true});
try{const preview=await outputBook.render({sheetName:'District data',range:'A1:H6',scale:1,format:'png'});await fs.writeFile(path.join(root,'OTHER/augmentation_runtime/preview.png'),new Uint8Array(await preview.arrayBuffer()));}catch(error){console.warn('CSV generated; preview unavailable: '+error.message);}
console.log(JSON.stringify({original_rows:manifest.original_rows,added_rows:manifest.added_rows,total_rows:manifest.total_rows,columns:manifest.columns,districts:manifest.augmented_geographic_districts,by_state:byState},null,2));
