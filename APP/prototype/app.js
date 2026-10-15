/* Browser-local beta. No model training, weather fetch or yield inference. */
'use strict';
const $ = id => document.getElementById(id);
const data = window.RYP_DATA;
if (!data) throw new Error('Map data missing. Run APP/tools/build_ui_data.py.');
const districts = data.districts, states = [...new Set(districts.map(d=>d.state))];
const svg = $('district-map'), ns = 'http://www.w3.org/2000/svg';
const groups = new Map(), paths = new Map(), initialView = [-30,-20,1000,1100];
let selected = null, activeState = null, view = [...initialView], animation = 0, drag = null, suppressClick = false, resultSnapshot = null;
const escapeHTML = value => String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const format = (value,digits=2) => Number(value).toLocaleString('en-IN',{maximumFractionDigits:digits});
const option = (value,label) => { const el=document.createElement('option');el.value=value;el.textContent=label;return el; };
function camera(next, animated=false){
 cancelAnimationFrame(animation);
 if(!animated || matchMedia('(prefers-reduced-motion: reduce)').matches){ view=next;svg.setAttribute('viewBox',view.join(' '));return; }
 const start=[...view], time=performance.now();
 const tick=now=>{const t=Math.min(1,(now-time)/380), eased=1-(1-t)**3;view=start.map((v,i)=>v+(next[i]-v)*eased);svg.setAttribute('viewBox',view.join(' '));if(t<1)animation=requestAnimationFrame(tick);};
 animation=requestAnimationFrame(tick);
}
function fitState(state){
 const box=groups.get(state).getBBox(), padding=45;
 camera([box.x-padding,box.y-padding,box.width+padding*2,box.height+padding*2],true);
}
function tooltip(event,title,detail){
 const tip=$('map-tooltip'), box=$('map-stage').getBoundingClientRect();
 tip.textContent=`${title} · ${detail}`;tip.hidden=false;
 tip.style.left=Math.max(8,Math.min(event.clientX-box.left+14,box.width-230))+'px';
 tip.style.top=Math.max(8,Math.min(event.clientY-box.top+14,box.height-48))+'px';
}
function clearResult(){ $('result').hidden=true;$('empty-result').hidden=false;resultSnapshot=null; }
function updateDistrictOptions(state){
 $('district').replaceChildren(option('','Choose a district'));
 districts.filter(d=>d.state===state).forEach(d=>$('district').append(option(d.id,d.name)));
 $('district').disabled=!state;
}
function updateCoverage(){
 window.CropHealth?.setContext({crop:'Rice',districtId:selected?.id??null,district:selected?.name??null,state:selected?.state??$('state').value,season:$('season').value,year:Number($('year').value),areaHa:$('area').value&&$('area').validity.valid?Number($('area').value):null});
 const el=$('coverage');el.classList.toggle('unsupported',Boolean(selected&&!selected.records));
 if(!selected){el.innerHTML='<b>Start with a location</b>Click a state, then select a district on the map or from the dropdown.';return;}
 let text=selected.records?`${selected.records} historical observations · ${selected.years[0]}–${selected.years.at(-1)}. Coverage does not establish predictive accuracy.`:'No observations for this district in the current cohort. You can preview the interface, but model generalization here has not been established.';
 const historical=selected.historicalStates.filter(s=>s!==selected.state);
 if(historical.length)text+=` Some source records use historical state labels (${historical.join(', ')}).`;
 if(['Autumn','Winter'].includes($('season').value))text+=' This season was unseen during preprocessing fitting.';
 if(Number($('year').value)>2019)text+=' No historical weather/labels are loaded beyond 2019.';
 el.innerHTML=`<b>${selected.records?'Historical cohort available':'Outside the training cohort'}</b>${escapeHTML(text)}`;
}
function paint(){
 groups.forEach((group,state)=>{
   group.querySelector('.state-surface').style.display=activeState?'none':'';
   group.querySelector('.district-layer').style.display=activeState===state?'':'none';
   group.querySelector('.district-layer').setAttribute('aria-hidden',String(activeState!==state));
   group.setAttribute('aria-hidden',String(Boolean(activeState&&activeState!==state)));
   group.style.display=!activeState||activeState===state?'':'none';
   group.classList.toggle('state-overview',!activeState);
   group.querySelector('.state-surface').setAttribute('tabindex',activeState?'-1':'0');
   group.querySelector('.state-surface').setAttribute('aria-hidden',String(Boolean(activeState)));
 });
 paths.forEach((path,id)=>{const chosen=selected?.id===id;path.classList.toggle('selected',chosen);path.setAttribute('aria-pressed',String(chosen));path.setAttribute('tabindex',activeState===districts.find(d=>d.id===id).state&&(chosen||!selected)?'0':'-1');});
 $('state-labels').style.display=activeState?'none':'';
 $('back-map').hidden=!activeState;
 $('map-step').textContent=activeState?`${activeState} / click a district`:'Click a state to explore its districts';
 $('map-selected').textContent=selected?`${selected.name} · ${selected.state}`:'Select a district to begin';
}
function openState(state){
 if(!states.includes(state))return;
 activeState=state;selected=null;$('state').value=state;updateDistrictOptions(state);clearResult();updateCoverage();paint();fitState(state);
 $('map-tooltip').hidden=true;
}
function selectDistrict(id, focus=false){
 const district=districts.find(d=>d.id===id);if(!district)return;
 const changedState=activeState!==district.state;
 activeState=district.state;selected=district;$('state').value=district.state;
 updateDistrictOptions(district.state);$('district').value=id;clearResult();updateCoverage();paint();
 if(changedState)fitState(district.state);
 if(focus)paths.get(id).focus({preventScroll:true});
 $('form-error').textContent='';$('map-tooltip').hidden=true;
}
states.forEach(state=>{
 const group=document.createElementNS(ns,'g');group.setAttribute('class','state-region');groups.set(state,group);
 const members=districts.filter(d=>d.state===state);
 const surface=document.createElementNS(ns,'path');surface.setAttribute('d',members.map(d=>d.path).join(''));
 surface.setAttribute('d',data.stateShapes[state]);surface.setAttribute('fill-rule','evenodd');surface.setAttribute('class','state-surface');surface.setAttribute('role','button');surface.setAttribute('aria-label',`${state}, ${members.length} districts. Select to zoom.`);
 surface.setAttribute('tabindex','0');
 surface.addEventListener('click',()=>{if(!suppressClick)openState(state);});
 surface.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();openState(state);paths.get(members[0].id).focus({preventScroll:true});}});
 surface.addEventListener('pointermove',event=>{if(!drag)tooltip(event,state,`${members.length} districts · click to zoom`);});
 surface.addEventListener('pointerleave',()=>$('map-tooltip').hidden=true);
 const layer=document.createElementNS(ns,'g');layer.setAttribute('class','district-layer');
 members.forEach(d=>{
  const path=document.createElementNS(ns,'path');path.setAttribute('d',d.path);path.setAttribute('fill-rule','evenodd');path.setAttribute('class','district-path'+(d.records?'':' outside'));path.setAttribute('role','button');path.setAttribute('aria-label',`${d.name}, ${d.state}. ${d.records} historical records.`);paths.set(d.id,path);
  path.addEventListener('click',()=>{if(!suppressClick)selectDistrict(d.id);});
  path.addEventListener('keydown',event=>{
   if(['Enter',' '].includes(event.key)){event.preventDefault();selectDistrict(d.id,true);}
   if(['ArrowRight','ArrowDown','ArrowLeft','ArrowUp'].includes(event.key)){event.preventDefault();const delta=['ArrowRight','ArrowDown'].includes(event.key)?1:-1;const next=members[(members.indexOf(d)+delta+members.length)%members.length];selectDistrict(next.id,true);}
  });
  path.addEventListener('pointermove',event=>{if(!drag)tooltip(event,d.name,d.records?`${d.records} historical records`:'outside cohort');});
  path.addEventListener('pointerleave',()=>$('map-tooltip').hidden=true);
  layer.append(path);
 });
 group.append(surface,layer);$('district-paths').append(group);
 const label=document.createElementNS(ns,'text');label.textContent=state.toUpperCase();label.setAttribute('class','state-label');label.setAttribute('x',members.reduce((v,d)=>v+d.x,0)/members.length);label.setAttribute('y',members.reduce((v,d)=>v+d.y,0)/members.length);$('state-labels').append(label);
});
$('district-count').textContent=`${districts.length} DISTRICTS`;
$('state').append(option('','Choose a state'));states.forEach(state=>$('state').append(option(state,state)));
updateDistrictOptions('');updateCoverage();paint();
$('state').addEventListener('change',()=>{if($('state').value)openState($('state').value);else reset();});
$('district').addEventListener('change',()=>{if($('district').value)selectDistrict($('district').value);else{selected=null;clearResult();updateCoverage();paint();}});
function reset(){activeState=null;selected=null;$('state').value='';updateDistrictOptions('');updateCoverage();clearResult();paint();camera([...initialView],true);}
$('clear-selection').addEventListener('click',reset);
$('back-map').addEventListener('click',()=>{activeState=null;paint();camera([...initialView],true);});
function zoom(factor){const width=Math.max(90,Math.min(2000,view[2]*factor)), ratio=width/view[2];camera([view[0]+(view[2]-width)/2,view[1]+(view[3]-view[3]*ratio)/2,width,view[3]*ratio]);}
$('zoom-in').addEventListener('click',()=>zoom(.75));$('zoom-out').addEventListener('click',()=>zoom(1.33));$('zoom-reset').addEventListener('click',()=>activeState?fitState(activeState):camera([...initialView],true));
svg.addEventListener('wheel',event=>{if(event.ctrlKey){event.preventDefault();zoom(event.deltaY>0?1.1:.9);}},{passive:false});
svg.addEventListener('pointerdown',event=>{if(event.button!==0)return;cancelAnimationFrame(animation);drag={x:event.clientX,y:event.clientY,view:[...view],moved:false};suppressClick=false;});
svg.addEventListener('pointermove',event=>{
 if(!drag)return;const dx=event.clientX-drag.x,dy=event.clientY-drag.y;
 if(Math.hypot(dx,dy)>6){drag.moved=true;suppressClick=true;svg.classList.add('dragging');svg.setPointerCapture(event.pointerId);$('map-tooltip').hidden=true;}
 if(drag.moved){const scale=Math.max(view[2]/svg.clientWidth,view[3]/svg.clientHeight);camera([drag.view[0]-dx*scale,drag.view[1]-dy*scale,drag.view[2],drag.view[3]]);}
});
function endDrag(){drag=null;svg.classList.remove('dragging');setTimeout(()=>suppressClick=false,0);}
svg.addEventListener('pointerup',endDrag);svg.addEventListener('pointercancel',endDrag);svg.addEventListener('lostpointercapture',()=>{drag=null;});
['area','year','season','representation','model'].forEach(id=>$(id).addEventListener('input',()=>{clearResult();updateCoverage();}));
function snapshot(){return {mode:'interface_demo',districtId:selected.id,district:selected.name,state:selected.state,season:$('season').value,year:Number($('year').value),areaHa:Number($('area').value),representation:$('representation').value,proposedModel:$('model').value,illustrativeYieldTPerHa:4.2,modelTrained:false};}
function baseOutputDashboard(request){
 const summary=RYPOutputs.summarize(request,data.history[request.districtId]);
 const p=summary.productionTonnes, ref=summary.reference, trend=summary.trend;
 const maxYield=Math.max(summary.yieldTPerHa,ref?Number(ref.YIELD):0,1)*1.2;
 const comparison=`<svg class="result-chart" viewBox="0 0 560 205" role="img" aria-label="Illustrative yield ${format(summary.yieldTPerHa)} tonnes per hectare${ref?', observed yield '+format(ref.YIELD,3):', observed comparison unavailable'}"><title>Demo versus observed yield; not a model evaluation</title><line x1="50" y1="162" x2="520" y2="162" class="chart-axis"/>${[0,.5,1].map(f=>`<line x1="50" y1="${162-f*125}" x2="520" y2="${162-f*125}" class="chart-grid"/><text x="42" y="${167-f*125}" text-anchor="end">${format(maxYield*f,1)}</text>`).join('')}<rect x="130" y="${162-summary.yieldTPerHa/maxYield*125}" width="95" height="${summary.yieldTPerHa/maxYield*125}" rx="5" class="demo-bar"/><text x="177" y="${151-summary.yieldTPerHa/maxYield*125}" text-anchor="middle">${format(summary.yieldTPerHa,2)}</text><text x="177" y="188" text-anchor="middle">Demo · t/ha</text>${ref?`<rect x="335" y="${162-Number(ref.YIELD)/maxYield*125}" width="95" height="${Number(ref.YIELD)/maxYield*125}" rx="5" class="observed-bar"/><text x="382" y="${151-Number(ref.YIELD)/maxYield*125}" text-anchor="middle">${format(ref.YIELD,3)}</text>`:`<rect x="335" y="132" width="95" height="30" rx="5" class="missing-bar"/><text x="382" y="120" text-anchor="middle">No match</text>`}<text x="382" y="188" text-anchor="middle">Observed · t/ha</text></svg>`;
 const scenario=`<svg class="result-chart" viewBox="0 0 560 210" role="img" aria-label="Illustrative production at half, entered and one-and-a-half times area"><title>Area scenarios at the fixed demo yield; not uncertainty bounds</title>${[.5,1,1.5].map((factor,i)=>{const x=110+i*155,height=factor/1.5*120;return `<rect x="${x}" y="${160-height}" width="85" height="${height}" rx="5" class="${factor===1?'demo-bar':'observed-bar'}"/><text x="${x+42}" y="${149-height}" text-anchor="middle">${format(p*factor)} t</text><text x="${x+42}" y="183" text-anchor="middle">${format(request.areaHa*factor)} ha</text>`;}).join('')}<line x1="50" y1="160" x2="520" y2="160" class="chart-axis"/></svg>`;
 let historyChart='<div class="chart-unavailable"><b>No unambiguous same-season history.</b><p>Try a covered district or another season. No trend is generated from missing records.</p></div>';
 if(trend.length){
  const ymax=Math.max(...trend.map(d=>d.yield),1)*1.2,minYear=trend[0].year,maxYear=trend.at(-1).year;
  const x=year=>60+(year-minYear)/Math.max(maxYear-minYear,1)*450,y=value=>170-value/ymax*125;
  historyChart=`<svg class="result-chart history-chart" viewBox="0 0 560 220" role="img" aria-label="Observed ${escapeHTML(request.season)} yield history for ${escapeHTML(request.district)}, ${trend.length} available years"><title>Observed source labels, not model forecasts</title>${[0,.5,1].map(f=>`<line x1="55" y1="${170-f*125}" x2="520" y2="${170-f*125}" class="chart-grid"/><text x="44" y="${175-f*125}" text-anchor="end">${format(ymax*f,1)}</text>`).join('')}<polyline points="${trend.map(d=>`${x(d.year)},${y(d.yield)}`).join(' ')}" class="history-line"/>${trend.map(d=>`<circle cx="${x(d.year)}" cy="${y(d.yield)}" r="4" class="history-point"><title>${d.year}: ${format(d.yield,3)} t/ha</title></circle>`).join('')}<text x="60" y="201">${minYear}</text>${maxYear!==minYear?`<text x="510" y="201" text-anchor="end">${maxYear}</text>`:''}<text x="287" y="216" text-anchor="middle">Crop year · observed yield (t/ha)</text></svg><div class="history-summary"><span><b>${format(summary.observedMeanYield,3)}</b>Mean t/ha</span><span><b>${format(summary.observedMinYield,3)}–${format(summary.observedMaxYield,3)}</b>Observed range t/ha</span><span><b>${trend.length}</b>Available years</span></div><details class="history-table"><summary>View the observations behind the chart</summary><table><thead><tr><th>Crop year</th><th>Observed yield (t/ha)</th></tr></thead><tbody>${trend.map(d=>`<tr><td>${d.year}</td><td>${format(d.yield,3)}</td></tr>`).join('')}</tbody></table></details>`;
 }
 return `<section class="visual-output" aria-label="Visual harvest outputs"><div class="section-title"><div><p class="eyebrow">YOUR HARVEST / AT A GLANCE</p><h2>Harvest summary</h2></div><span class="small-badge">DEMO & OBSERVED DATA</span></div><div class="output-kpis"><article><span>Illustrative production</span><strong>${format(p)} <small>t</small></strong><p>Yield × entered hectares</p></article><article><span>Harvest mass equivalent</span><strong>${format(summary.productionKg,0)} <small>kg</small></strong><p>Tonnes × 1,000 · no milling conversion</p></article><article><span>Entered cultivation area</span><strong>${format(request.areaHa)} <small>ha</small></strong><p>User input · not a model output</p></article><article><span>Historical reference</span><strong>${ref?format(ref.YIELD,3):'—'} <small>${ref?'t/ha':'no match'}</small></strong><p>Observed district yield, not predicted</p></article></div><div class="charts-grid"><article class="chart-card"><p class="eyebrow">LIKE-FOR-LIKE UNITS</p><h3>Demo and observed yield</h3>${comparison}<p>${ref?`Demo minus observed = ${format(summary.demoGapTPerHa,3)} t/ha. This gap is illustrative, not prediction error or an improvement claim.`:'No matching district, year and season observation.'}</p></article><article class="chart-card"><p class="eyebrow">AREA SCENARIOS / FIXED DEMO YIELD</p><h3>If the cultivated area changes…</h3>${scenario}<label class="scenario-control">Explore area: <output id="scenario-area">${format(request.areaHa)} ha</output><input id="scenario-factor" type="range" min="50" max="150" value="100" step="5" aria-label="Scenario area as percentage of entered area"></label><div class="scenario-answer"><span id="scenario-tonnes">${format(p)} tonnes</span><small id="scenario-formula">${format(summary.yieldTPerHa,2)} × ${format(request.areaHa)} ha</small></div><p>Fixed yield × scenario area. Not an uncertainty interval.</p></article><article class="chart-card"><p class="eyebrow">RECORDED HISTORY / ${escapeHTML(request.season.toUpperCase())}</p><h3>How this district's yield varied</h3>${historyChart}<p>Same-season records through ${request.year} only. Lines connect available observations, not estimated missing years. ${summary.ambiguousYears.length?`${summary.ambiguousYears.length} ambiguous years excluded.`:''}</p></article><article class="chart-card"><p class="eyebrow">OPTIONAL / USER-DEFINED PRICE</p><h3>Explore gross harvest value</h3><p>Enter a sale-price assumption. No live market prices.</p><label>Assumed sale price (₹ per kg)<input id="sale-price" type="number" min="0" max="100000" step="0.01" placeholder="Enter a price; no default"></label><div id="gross-value" class="gross-value" aria-live="polite">Price not entered</div><p id="gross-formula">Enter a valid price.</p><p>Gross value only. Costs, taxes, losses, milling recovery and profit are not estimated.</p></article></div><div class="coverage-output"><div><b>What is computed now?</b><p>Demo production, mass conversion and area/price scenarios are exact arithmetic. Historical yield and weather come from existing observations.</p></div><div><b>What comes after training?</b><p>Model-derived yield and its derived production can replace the demo values. Validated uncertainty or feature attribution would require additional implementation.</p></div></div></section>`;
}
function outputDashboard(request){
 const container=document.createElement('div');container.innerHTML=baseOutputDashboard(request);
 const summary=RYPOutputs.summarize(request,data.history[request.districtId]);
 const cards=container.querySelectorAll('.chart-card');
 cards[0].querySelector('svg').outerHTML=CropCharts.comparison(summary);
 cards[1].querySelector('svg').outerHTML=CropCharts.scenario(summary);
 const history=CropCharts.history(summary);
 if(history)cards[2].querySelector('svg').outerHTML=history;
 cards[0].querySelector('h3').textContent='Yield comparison';
 cards[1].querySelector('h3').textContent='Production by cultivation area';
 cards[2].querySelector('h3').textContent='Historical district yield';
 cards[3].querySelector('h3').textContent='Gross harvest value';
 container.querySelector('.coverage-output').remove();
 return container.innerHTML;
}
function renderResult(request){
 const model=request.proposedModel==='mlp'?'MLP regressor':'HistGradientBoostingRegressor', dae=request.representation==='autoencoder', count=dae?16:28;
 const history=data.history[request.districtId].filter(r=>r.FYEAR===request.year&&r.SEASON===request.season);
 const h=history.length===1?history[0]:null;
 const historical=h?`<div class="history-card"><b>Observed historical reference · NOT a prediction</b><p>${escapeHTML(h.DISTRICT)} / ${escapeHTML(h.STATE)} / ${request.year} ${escapeHTML(request.season)}. Historical district area ${format(h.CROP_AREA)} ha, not your entered area.</p><div class="history-metrics"><span><b>${format(h.YIELD,3)} t/ha</b>Observed yield</span><span><b>${format(h.TAVG_MEAN,1)} °C</b>Season mean temperature</span><span><b>${format(h.PREC_TOTAL,1)} mm</b>Season precipitation</span><span><b>${format(h.GDD_BASE10,0)}</b>Growing degree days</span></div></div>`:`<div class="history-card"><b>No unique historical reference for this selection</b><p>No single matching district/year/season observation is available. No weather or observed yield is invented.</p></div>`;
 $('result').innerHTML=`<div class="output-grid"><article class="yield-card"><p class="eyebrow">ILLUSTRATIVE RESULT / NO MODEL INFERENCE</p><div class="big-number">${format(request.illustrativeYieldTPerHa,2)} <span>t/ha</span></div><p>${escapeHTML(request.district)} · ${escapeHTML(request.season)} ${request.year}<br>${format(request.areaHa)} hectares</p><div class="output-production"><span>Illustrative production</span><b>${format(request.illustrativeYieldTPerHa*request.areaHa)} t</b></div><p>Demo calculation · not a forecast.</p></article><article class="explanation-card"><p class="eyebrow">HOW THIS PREVIEW WAS DERIVED</p><h3>Calculation</h3><p><b>Demo yield: 4.20 t/ha.</b> Adjust the assumptions below. No trained model is running.</p><div class="formula">${format(request.illustrativeYieldTPerHa,2)} t/ha × ${format(request.areaHa)} ha = ${format(request.illustrativeYieldTPerHa*request.areaHa)} tonnes</div><p>Planned route: <b>${dae?'DAE':'Standard'} (${count} predictors) → ${model}</b>. Training pending.</p><button id="download-preview" type="button">Download input & calculation JSON ↓</button> <a class="inline-link" href="#info">Read the full method →</a></article></div><div class="trace"><div><b>01 · Inputs validated</b><span>Location, season, year and positive hectares.</span></div><div><b>02 · Feature construction</b><span>Future weather + area-context service; 21 numerical features.</span></div><div><b>03 · Preprocessing</b><span>Saved imputer/scaler/encoder${dae?' + DAE':''}. Not run in demo.</span></div><div><b>04 · Yield model</b><span>${model}. Awaiting training, evaluation and integration.</span></div></div>${historical}`;
 $('empty-result').hidden=true;$('result').hidden=false;
 const dashboard=document.createElement('div');dashboard.innerHTML=outputDashboard(request);$('result').append(dashboard);
 $('result').insertAdjacentHTML('beforeend',CropHelp.calculation(request));
 let scenarioFactor=1, salePrice=null;
 function derived(){return RYPOutputs.summarize(request,data.history[request.districtId],salePrice,scenarioFactor);}
 const startingArea=request.areaHa;
 const controls=document.createElement('section');controls.className='metric-controls';controls.setAttribute('aria-label','Live what-if metrics');
 controls.innerHTML=`<div class="metric-heading"><div><p class="eyebrow">LIVE WHAT-IF CONTROLS</p><h3>Adjust yield and area</h3><p>Charts update immediately. Historical data stays fixed.</p></div><button id="reset-metrics" type="button">Reset assumptions</button></div><div class="metric-fields"><label>Demo yield assumption <output id="yield-assumption-label">${format(request.illustrativeYieldTPerHa,2)} t/ha</output><input id="demo-yield" type="range" min="0" max="12" step="0.05" value="${request.illustrativeYieldTPerHa}" aria-label="Demo yield assumption in tonnes per hectare"></label><label>What-if cultivation area (ha)<input id="result-area" type="number" min="0.01" max="1000000" step="0.01" value="${request.areaHa}"></label></div><p id="metric-error" role="alert" class="error"></p>`;
 $('result').prepend(controls);
 function refreshDerived(){
  const summary=derived();$('scenario-area').textContent=format(summary.scenario.areaHa)+' ha';$('scenario-tonnes').textContent=format(summary.scenario.productionTonnes)+' tonnes';$('scenario-formula').textContent=`${format(summary.yieldTPerHa,2)} × ${format(summary.scenario.areaHa)} ha`;
  if(salePrice===null){$('gross-value').textContent='Price not entered';$('gross-formula').textContent='Enter a valid price.';}
  else{$('gross-value').textContent='₹ '+format(summary.grossValueINR);$('gross-formula').textContent=`${format(summary.productionKg)} kg × ₹ ${format(salePrice)}/kg. Uses the base what-if area, not the scenario slider.`;}
  dashboard.querySelectorAll('.chart-card')[1].querySelector('svg').outerHTML=CropCharts.scenario(summary,scenarioFactor);
  if(!$('price-chart')){const priceChart=document.createElement('div');priceChart.id='price-chart';$('gross-formula').after(priceChart);}
  $('price-chart').innerHTML=salePrice===null?'':`<svg class="result-chart" viewBox="0 0 560 180" role="img" aria-label="Gross value at 75, 100 and 125 percent of your assumed sale price"><title>Illustrative price scenarios; not market predictions</title>${[.75,1,1.25].map((factor,i)=>{const x=90+i*165,height=salePrice===0?0:factor/1.25*85;return `<rect x="${x}" y="${120-height}" width="95" height="${height}" rx="5" class="${factor===1?'demo-bar':'observed-bar'}"/><text x="${x+47}" y="${109-height}" text-anchor="middle">₹ ${format(summary.grossValueINR*factor,0)}</text><text x="${x+47}" y="143" text-anchor="middle">₹ ${format(salePrice*factor)}/kg</text>`;}).join('')}<text x="280" y="170" text-anchor="middle">User-price scenarios: −25% / entered / +25%</text></svg>`;
 }
 function refreshVisuals(){
  const fresh=document.createElement('div');fresh.innerHTML=outputDashboard(request);
  dashboard.querySelector('.output-kpis').replaceWith(fresh.querySelector('.output-kpis'));
  const currentCards=dashboard.querySelectorAll('.chart-card'),nextCards=fresh.querySelectorAll('.chart-card');
  [0,1].forEach(index=>currentCards[index].querySelector('svg').replaceWith(nextCards[index].querySelector('svg')));
  currentCards[0].querySelector('p:last-child').textContent=nextCards[0].querySelector('p:last-child').textContent;
  const card=$('result').querySelector('.yield-card');card.querySelector('.big-number').innerHTML=`${format(request.illustrativeYieldTPerHa,2)} <span>t/ha</span>`;
  card.querySelector('p:not(.eyebrow)').innerHTML=`${escapeHTML(request.district)} · ${escapeHTML(request.season)} ${request.year}<br>${format(request.areaHa)} hectares`;
  card.querySelector('.output-production b').textContent=format(request.illustrativeYieldTPerHa*request.areaHa)+' t';
  $('result').querySelector('.formula').textContent=`${format(request.illustrativeYieldTPerHa,2)} t/ha × ${format(request.areaHa)} ha = ${format(request.illustrativeYieldTPerHa*request.areaHa)} tonnes`;
  $('yield-assumption-label').textContent=format(request.illustrativeYieldTPerHa,2)+' t/ha';
  const example=$('result').querySelector('.calculation-example');
  example.querySelector('.calc-area').textContent=format(request.areaHa);
  example.querySelector('.calc-example-tonnes').textContent=format(4.2*request.areaHa);
  example.querySelector('.calc-example-kg').textContent=format(4200*request.areaHa,0);
  example.querySelector('.calc-current').textContent=`Current dashboard assumption: ${format(request.illustrativeYieldTPerHa)} t/ha × ${format(request.areaHa)} ha = ${format(request.illustrativeYieldTPerHa*request.areaHa)} tonnes.`;
  refreshDerived();
 }
 $('demo-yield').addEventListener('input',()=>{request.illustrativeYieldTPerHa=Number($('demo-yield').value);refreshVisuals();});
 $('result-area').addEventListener('input',()=>{const field=$('result-area');if(!field.value||!field.validity.valid){$('metric-error').textContent='Enter a valid positive area. Charts retain the last valid area until corrected.';return;}request.areaHa=Number(field.value);$('area').value=field.value;updateCoverage();$('metric-error').textContent='';refreshVisuals();});
 $('reset-metrics').addEventListener('click',()=>{request.areaHa=startingArea;request.illustrativeYieldTPerHa=4.2;scenarioFactor=1;salePrice=null;$('result-area').value=startingArea;$('area').value=startingArea;$('demo-yield').value='4.2';$('scenario-factor').value='100';$('sale-price').value='';updateCoverage();$('metric-error').textContent='';refreshVisuals();});
 $('scenario-factor').addEventListener('input',()=>{scenarioFactor=Number($('scenario-factor').value)/100;refreshDerived();});
 $('sale-price').addEventListener('input',()=>{const input=$('sale-price'),value=Number(input.value);salePrice=input.value!==''&&input.validity.valid&&Number.isFinite(value)?value:null;refreshDerived();});
 $('download-preview').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({...request,outputs:derived(),explanation:'User-selected demo yield assumption multiplied by user area. Gross value uses user-supplied price only. Trend/reference are observed source labels, not forecasts. No trained model inference.'},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='crop-yantra-preview.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
}
$('yield-form').addEventListener('submit',event=>{event.preventDefault();if(!$('yield-form').reportValidity())return;if(!selected){$('form-error').textContent='Choose a district first.';return;}resultSnapshot=snapshot();renderResult(resultSnapshot);$('result').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});});
data.manifest.standard.predictor_columns.filter(name=>name.startsWith('numeric__')).forEach(name=>{const tag=document.createElement('span');tag.textContent=name.replace('numeric__','');$('feature-list').append(tag);});
function route(){const hash=location.hash.slice(1),info=hash==='info'||['sources-section','preprocessing-section','models-section','output-section'].includes(hash),health=hash==='health';$('studio').hidden=info;$('info').hidden=!info;$('health').hidden=info;document.querySelectorAll('.nav-link').forEach(a=>a.classList.toggle('active',a.hash===(info?'#info':health?'#health':'#studio')));if(health||hash.endsWith('-section'))requestAnimationFrame(()=>$(hash)?.scrollIntoView({block:'start'}));else window.scrollTo({top:0,behavior:'auto'});}
window.addEventListener('hashchange',route);route();
const themeButton=$('theme-toggle');
function setTheme(theme){document.documentElement.dataset.theme=theme;themeButton.setAttribute('aria-pressed',String(theme==='dark'));themeButton.textContent=theme==='dark'?'☀ Switch to light mode':'◐ Switch to dark mode';try{localStorage.setItem('ryp-theme',theme);}catch{/* Storage may be unavailable in private/file contexts. */}}
try{setTheme(localStorage.getItem('ryp-theme')||'light');}catch{setTheme('light');}
themeButton.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
