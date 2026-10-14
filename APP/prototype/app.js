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
function reset(){activeState=null;selected=null;$('state').value='';updateDistrictOptions('');$('district-search').value='';$('search-results').replaceChildren();updateCoverage();clearResult();paint();camera([...initialView],true);}
$('clear-selection').addEventListener('click',reset);
$('back-map').addEventListener('click',()=>{activeState=null;paint();camera([...initialView],true);});
$('district-search').addEventListener('input',()=>{
 const query=$('district-search').value.trim().toLowerCase(), list=$('search-results');list.replaceChildren();if(!query)return;
 const matches=districts.filter(d=>`${d.name} ${d.state}`.toLowerCase().includes(query));
 matches.slice(0,8).forEach(d=>{const button=document.createElement('button');button.type='button';button.innerHTML=`${escapeHTML(d.name)}<span>${escapeHTML(d.state)}</span>`;button.addEventListener('click',()=>{selectDistrict(d.id);list.replaceChildren();$('district-search').value=d.name;});list.append(button);});
 if(!matches.length)list.textContent='No matching district. Try its source-vintage spelling.';
});
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
function renderResult(request){
 const model=request.proposedModel==='mlp'?'MLP regressor':'HistGradientBoostingRegressor', dae=request.representation==='autoencoder', count=dae?16:28;
 const history=data.history[request.districtId].filter(r=>r.FYEAR===request.year&&r.SEASON===request.season);
 const h=history.length===1?history[0]:null;
 const historical=h?`<div class="history-card"><b>Observed historical reference · NOT a prediction</b><p>${escapeHTML(h.DISTRICT)} / ${escapeHTML(h.STATE)} / ${request.year} ${escapeHTML(request.season)}. Historical district area ${format(h.CROP_AREA)} ha, not your entered area.</p><div class="history-metrics"><span><b>${format(h.YIELD,3)} t/ha</b>Observed yield</span><span><b>${format(h.TAVG_MEAN,1)} °C</b>Season mean temperature</span><span><b>${format(h.PREC_TOTAL,1)} mm</b>Season precipitation</span><span><b>${format(h.GDD_BASE10,0)}</b>Growing degree days</span></div></div>`:`<div class="history-card"><b>No unique historical reference for this selection</b><p>No single matching district/year/season observation is available. No weather or observed yield is invented.</p></div>`;
 $('result').innerHTML=`<div class="output-grid"><article class="yield-card"><p class="eyebrow">ILLUSTRATIVE RESULT / NO MODEL INFERENCE</p><div class="big-number">4.20 <span>t/ha</span></div><p>${escapeHTML(request.district)} · ${escapeHTML(request.season)} ${request.year}<br>${format(request.areaHa)} hectares</p><div class="output-production"><span>Illustrative production</span><b>${format(4.2*request.areaHa)} t</b></div><p>Not a forecast, confidence estimate or disease diagnosis.</p></article><article class="explanation-card"><p class="eyebrow">HOW THIS PREVIEW WAS DERIVED</p><h3>Follow the numbers.</h3><p><b>4.20 t/ha is a fixed interface placeholder.</b> District, weather, representation and predictor do not alter it. Only the entered area changes the production calculation.</p><div class="formula">4.20 t/ha × ${format(request.areaHa)} ha = ${format(4.2*request.areaHa)} tonnes</div><p>Planned route: <b>${dae?'DAE':'Standard'} (${count} predictors) → ${model}</b>. Both yield predictors are untrained. No preprocessing is executed in this browser preview.</p><button id="download-preview" type="button">Download input & calculation JSON ↓</button> <a class="inline-link" href="#info">Read the full method →</a></article></div><div class="trace"><div><b>01 · Inputs validated</b><span>Location, season, year and positive hectares.</span></div><div><b>02 · Feature construction</b><span>Future weather + area-context service; 21 numerical features.</span></div><div><b>03 · Preprocessing</b><span>Saved imputer/scaler/encoder${dae?' + DAE':''}. Not run in demo.</span></div><div><b>04 · Yield model</b><span>${model}. Awaiting training, evaluation and integration.</span></div></div>${historical}`;
 $('empty-result').hidden=true;$('result').hidden=false;
 $('download-preview').addEventListener('click',()=>{const blob=new Blob([JSON.stringify({...request,illustrativeProductionTonnes:4.2*request.areaHa,explanation:'Fixed demo yield multiplied by user area. No trained model inference.'},null,2)],{type:'application/json'});const url=URL.createObjectURL(blob),link=document.createElement('a');link.href=url;link.download='ryp-preview.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
}
$('yield-form').addEventListener('submit',event=>{event.preventDefault();if(!$('yield-form').reportValidity())return;if(!selected){$('form-error').textContent='Choose a district first.';return;}resultSnapshot=snapshot();renderResult(resultSnapshot);$('result').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth',block:'start'});});
data.manifest.standard.predictor_columns.filter(name=>name.startsWith('numeric__')).forEach(name=>{const tag=document.createElement('span');tag.textContent=name.replace('numeric__','');$('feature-list').append(tag);});
function route(){const hash=location.hash.slice(1), info=hash==='info'||['sources-section','preprocessing-section','models-section','output-section'].includes(hash);$('studio').hidden=info;$('info').hidden=!info;document.querySelectorAll('.nav-link').forEach(a=>a.classList.toggle('active',a.hash===(info?'#info':'#studio')));if(hash.endsWith('-section'))requestAnimationFrame(()=>$(hash)?.scrollIntoView());else window.scrollTo({top:0,behavior:'auto'});}
window.addEventListener('hashchange',route);route();
const themeButton=$('theme-toggle');
function setTheme(theme){document.documentElement.dataset.theme=theme;themeButton.setAttribute('aria-pressed',String(theme==='dark'));themeButton.textContent=theme==='dark'?'☀ Switch to light mode':'◐ Switch to dark mode';try{localStorage.setItem('ryp-theme',theme);}catch{/* Storage may be unavailable in private/file contexts. */}}
try{setTheme(localStorage.getItem('ryp-theme')||'light');}catch{setTheme('light');}
themeButton.addEventListener('click',()=>setTheme(document.documentElement.dataset.theme==='dark'?'light':'dark'));
