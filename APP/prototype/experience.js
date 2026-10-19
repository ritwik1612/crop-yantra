/* Paddy botanical stage: true WebGL geometry and separate real symptom photos. */
(function(){
 'use strict';
 const $=id=>document.getElementById(id),reduced=matchMedia('(prefers-reduced-motion: reduce)');
 document.body.classList.add('paddy-experience');
 const icons={plant:'<path d="M12 22V6m0 9C5 15 3 9 3 9c7-1 9 6 9 6Zm0-4c7 0 9-7 9-7-7-1-9 7-9 7Z"/>',leaf:'<path d="M6 20C-2 7 12 1 21 3c1 12-4 20-15 17Zm0 0L17 7"/>',wind:'<path d="M3 8h12c5 0 5-6 1-6M3 12h16c5 0 5 7 0 7M3 16h7"/>',photo:'<path d="M3 6h5l2-3h5l2 3h4v15H3V6Z"/><circle cx="12" cy="13" r="4"/>'};
 const icon=name=>'<svg viewBox="0 0 24 26" aria-hidden="true">'+icons[name]+'</svg>';
 let mode='plant';
 const hero=document.createElement('section');hero.className='botanical-stage';hero.setAttribute('aria-label','Interactive rice reference and photo screening');
 hero.innerHTML='<div class="botanical-copy"><span class="stage-overline">ORYZA SATIVA / RICE</span><h2 id="botanical-title">Inspect<br>your crop.</h2><p id="botanical-description">Explore leaf symptoms or screen a rice photo with the trained image model.</p><div class="botanical-modes" aria-label="Rice visualisation"><button type="button" aria-pressed="true" data-botanical="plant">'+icon('plant')+'<span>Plant</span></button><button type="button" aria-pressed="false" data-botanical="leaf">'+icon('leaf')+'<span>Symptoms</span></button><button type="button" aria-pressed="false" data-botanical="wind">'+icon('wind')+'<span>Wind</span></button></div><div class="botanical-condition" hidden><label for="botanical-disease">Reference condition</label><select id="botanical-disease"><option value="blast">Rice blast</option><option value="bacterial_blight">Bacterial leaf blight</option><option value="brown_spot">Brown spot</option></select></div><div class="wind-explorer" hidden><label for="botanical-wind">Illustrative wind <output id="botanical-wind-value">2 m/s</output></label><input id="botanical-wind" type="range" min="0" max="10" step=".1" value="2"></div></div><div class="botanical-canvas-wrap"><canvas id="rice-canvas" aria-hidden="true"></canvas><div class="specimen-caption"><span>PROCEDURAL RICE STUDY</span><button type="button" id="motion-toggle" aria-pressed="false" aria-label="Pause botanical animation">Ⅱ</button></div><span class="specimen-coordinate" aria-hidden="true">01 — RICE</span><div class="reference-preview" hidden><img id="botanical-reference" alt=""><span>Real symptom reference</span></div></div><div class="botanical-upload"></div>';
 const atlas=window.PaddyConditions;
 const photoSection=document.querySelector('#health .photo-section');photoSection.before(hero);hero.querySelector('.botanical-upload').append(photoSection);
 const conditionSelect=$('botanical-disease');conditionSelect.replaceChildren(...atlas.map(condition=>{const option=document.createElement('option');option.value=condition.id;option.textContent=condition.label;return option;}));
 const compareControls=document.createElement('div');compareControls.className='symptom-comparison';compareControls.innerHTML='<label><input id="compare-leaf-symptoms" type="checkbox" checked> Different symptoms across leaves</label><button type="button" id="view-all-leaves">View all leaves ↗</button><small>Educational comparison, not one diagnosed plant. Click a leaf to inspect its example.</small>';hero.querySelector('.botanical-condition').append(compareControls);
 $('compare-leaf-symptoms').addEventListener('change',()=>{draw(performance.now()*.001);start();});
 $('view-all-leaves').addEventListener('click',()=>cameraAction('overview'));
 const symptomSigns=document.createElement('p');symptomSigns.className='symptom-signs';symptomSigns.id='symptom-signs';hero.querySelector('.botanical-condition').append(symptomSigns);
 const organLabel=document.createElement('span');organLabel.className='organ-label';organLabel.id='organ-label';hero.querySelector('.stage-overline').after(organLabel);
 const locationRail=document.createElement('div');locationRail.className='symptom-location-rail';locationRail.setAttribute('aria-label','Plant inspection points');
 atlas.forEach((condition,index)=>{const button=document.createElement('button');button.type='button';button.setAttribute('aria-label','Inspect '+condition.label+' — '+condition.position);button.title=condition.label+' / '+condition.position;button.setAttribute('aria-pressed','false');button.addEventListener('click',()=>inspectCondition(index));locationRail.append(button);});hero.querySelector('.botanical-canvas-wrap').append(locationRail);
 const scrollHint=document.createElement('span');scrollHint.className='plant-scroll-hint';scrollHint.textContent='Scroll to inspect ↓';hero.querySelector('.botanical-canvas-wrap').append(scrollHint);
 const notice=document.createElement('p');notice.className='botanical-notice';notice.textContent='3D educational model. Symptom progression is illustrative, not measured. Photo screening uses your uploaded image.';hero.after(notice);
 hero.querySelector('.specimen-caption>span').textContent='RICE / 3D SPECIMEN';
 const detailControls=document.createElement('div');detailControls.className='symptom-zoom';detailControls.innerHTML='<label for="symptom-zoom">Photo detail <output id="symptom-zoom-value">1.0×</output></label><input id="symptom-zoom" type="range" min="1" max="3" value="1" step=".05" aria-label="Magnify reference photograph">';hero.querySelector('.botanical-condition').append(detailControls);
 $('symptom-zoom').addEventListener('input',()=>{$('symptom-zoom-value').textContent=Number($('symptom-zoom').value).toFixed(1)+'×';referenceFrame.style.setProperty('--reference-zoom',$('symptom-zoom').value);});
 const sourceLink=document.createElement('a');sourceLink.className='botanical-source';sourceLink.target='_blank';sourceLink.rel='noopener';hero.querySelector('.reference-preview').append(sourceLink);
 const photoViewport=document.createElement('div');photoViewport.className='symptom-image-viewport';$('botanical-reference').before(photoViewport);photoViewport.append($('botanical-reference'));
 const referenceFrame=document.createElement('div');referenceFrame.className='reference-photo-frame';photoViewport.prepend(referenceFrame);referenceFrame.append($('botanical-reference'));
 const unavailablePhoto=document.createElement('p');unavailablePhoto.className='reference-unavailable';unavailablePhoto.hidden=true;unavailablePhoto.textContent='The reference image could not be loaded. Please reopen this panel.';photoViewport.append(unavailablePhoto);
 $('botanical-reference').addEventListener('load',()=>{$('botanical-reference').hidden=false;unavailablePhoto.hidden=true;detailControls.hidden=false;});
 $('botanical-reference').addEventListener('error',()=>{$('botanical-reference').hidden=true;unavailablePhoto.hidden=false;detailControls.hidden=true;});
 photoViewport.addEventListener('pointermove',event=>{const rect=referenceFrame.getBoundingClientRect();referenceFrame.style.transformOrigin=((event.clientX-rect.left)/rect.width*100)+'% '+((event.clientY-rect.top)/rect.height*100)+'%';});
 photoViewport.addEventListener('pointerleave',()=>{referenceFrame.style.transformOrigin='50% 50%';});
 const referenceModal=document.createElement('dialog');referenceModal.id='real-reference-modal';referenceModal.className='real-reference-modal';referenceModal.setAttribute('aria-label','Real rice symptom photograph');
 const closeReference=document.createElement('button');closeReference.type='button';closeReference.className='reference-modal-close';closeReference.textContent='×';closeReference.setAttribute('aria-label','Close real reference photo');referenceModal.append(closeReference);
 const realPanel=hero.querySelector('.reference-preview');realPanel.hidden=false;referenceModal.append(realPanel,detailControls);document.body.append(referenceModal);
 const realButton=document.createElement('button');realButton.id='open-real-reference';realButton.className='open-real-reference';realButton.type='button';realButton.hidden=true;realButton.innerHTML=icon('photo')+'<span>Real photo</span>';realButton.setAttribute('aria-haspopup','dialog');realButton.setAttribute('aria-controls','real-reference-modal');hero.querySelector('.botanical-canvas-wrap').append(realButton);
 realButton.addEventListener('click',()=>{updateReference();referenceModal.showModal();});closeReference.addEventListener('click',()=>referenceModal.close());
 window.addEventListener('hashchange',()=>{if(referenceModal.open)referenceModal.close();});
 referenceModal.addEventListener('click',event=>{if(event.target===referenceModal){const r=referenceModal.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)referenceModal.close();}});
 referenceModal.addEventListener('close',()=>{if(!realButton.hidden)realButton.focus({preventScroll:true});});
 const symptomControls=document.createElement('div');symptomControls.className='symptom-progression';symptomControls.innerHTML='<label for="symptom-progress">Illustrative progression <output id="symptom-progress-label">0%</output></label><input id="symptom-progress" type="range" min="0" max="100" step="1" value="0"><button type="button" id="symptom-play" aria-pressed="true">Pause progression</button>';
 hero.querySelector('.botanical-condition').append(symptomControls);
 let symptomProgress=0,symptomPlaying=!reduced.matches,symptomLast=0;
 $('symptom-play').textContent=symptomPlaying?'Pause progression':'Play progression';$('symptom-play').setAttribute('aria-pressed',String(symptomPlaying));
 $('symptom-play').disabled=reduced.matches;
 $('symptom-progress').addEventListener('input',()=>{symptomProgress=Number($('symptom-progress').value)/100;symptomPlaying=false;$('symptom-progress-label').textContent=Math.round(symptomProgress*100)+'%';$('symptom-play').textContent='Play progression';$('symptom-play').setAttribute('aria-pressed','false');draw(performance.now()*.001);});
 $('symptom-play').addEventListener('click',()=>{symptomPlaying=!symptomPlaying;if(symptomProgress>=1)symptomProgress=0;symptomLast=0;if(symptomPlaying&&!reduced.matches){paused=false;syncMotion();}$('symptom-play').textContent=symptomPlaying?'Pause progression':'Play progression';$('symptom-play').setAttribute('aria-pressed',String(symptomPlaying));start();});
 const descriptions={plant:['Inspect<br>your crop.','Orbit the rice model or scroll to inspect its leaves.'],leaf:['Leaf<br>symptoms.','Orbit to inspect the leaf surface. Open the photo icon for the real reference.'],wind:['Field<br>conditions.','Move your pointer to create a gust, or adjust the wind.']};
 $('botanical-description').textContent=descriptions.plant[1];
 hero.querySelectorAll('[data-botanical]').forEach(button=>button.addEventListener('click',()=>{
  mode=button.dataset.botanical;hero.dataset.mode=mode;
  hero.querySelectorAll('[data-botanical]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
  $('botanical-title').innerHTML=descriptions[mode][0];$('botanical-description').textContent=descriptions[mode][1];
  hero.querySelector('.botanical-condition').hidden=mode!=='leaf';hero.querySelector('.wind-explorer').hidden=mode!=='wind';
  realButton.hidden=mode!=='leaf';if(referenceModal.open)referenceModal.close();symptomLast=0;updateReference();
  hero.querySelector('.specimen-caption>span').textContent=mode==='leaf'?'3D / SYMPTOM INSPECTION':'RICE / 3D SPECIMEN';draw(0);start();
 }));
 function currentCondition(){return atlas.find(c=>c.id===conditionSelect.value)||atlas[0];}
 function updateReference(){const condition=currentCondition(),photo=condition.photo||window.CropHealth.referencePhotos[condition.id];
  const reference=$('botanical-reference');referenceFrame.style.setProperty('--reference-zoom','1');referenceFrame.classList.toggle('is-panel',Boolean(photo.region));
  referenceFrame.style.removeProperty('aspect-ratio');reference.removeAttribute('style');
  if(photo.region){const [x,y,w,h]=photo.region;referenceFrame.style.aspectRatio=w+'/'+h;reference.style.width=(1417/w*100)+'%';reference.style.height=(633/h*100)+'%';reference.style.left=(-x/w*100)+'%';reference.style.top=(-y/h*100)+'%';}
  $('botanical-reference').src=photo.file;$('botanical-reference').alt=photo.title;$('botanical-reference').style.setProperty('--reference-zoom','1');$('symptom-zoom').value=1;$('symptom-zoom-value').textContent='1.0×';sourceLink.href=photo.url;sourceLink.textContent=(photo.credit||'Donald Groth / LSU AgCenter')+' · '+photo.license+' ↗';
  symptomSigns.textContent=condition.signs;organLabel.textContent=mode==='leaf'?condition.position+' / '+condition.part:'';
  if(mode==='leaf')$('botanical-title').textContent=condition.title;
  symptomControls.hidden=Boolean(condition.noProgression);
  const index=atlas.indexOf(condition);
  Array.from(locationRail.children).forEach((button,i)=>button.setAttribute('aria-pressed',String(mode==='leaf'&&index===i)));
  scrollHint.textContent=mode==='leaf'?String(index+1).padStart(2,'0')+' / '+atlas.length+' · Scroll ↓':'Scroll to inspect ↓';
 }
 $('botanical-disease').addEventListener('change',()=>{focusLeaf=null;overview=false;baseYaw=targetYaw=targetPitch=0;targetZoom=1;updateReference();symptomProgress=.5;symptomLast=0;symptomPlaying=!reduced.matches;$('symptom-play').textContent=symptomPlaying?'Pause progression':'Play progression';$('symptom-play').setAttribute('aria-pressed',String(symptomPlaying));draw(0);start();});
 $('botanical-wind').addEventListener('input',()=>{$('botanical-wind-value').textContent=Number($('botanical-wind').value).toFixed(1)+' m/s';draw(0);});
 const canvas=$('rice-canvas'),wrap=canvas.parentElement;
 canvas.removeAttribute('aria-hidden');canvas.tabIndex=0;canvas.setAttribute('role','img');canvas.setAttribute('aria-label','3D rice model. Drag to orbit around the plant or selected leaf. Arrow keys turn or tilt; plus and minus zoom; Page Down follows the next symptom. Home resets orbit.');
 const cameraControls=document.createElement('div');cameraControls.className='specimen-camera';cameraControls.setAttribute('aria-label','Rice view controls');cameraControls.innerHTML='<button type="button" data-camera="left" aria-label="Turn rice left">↶</button><button type="button" data-camera="right" aria-label="Turn rice right">↷</button><button type="button" data-camera="out" aria-label="Zoom rice out">−</button><button type="button" data-camera="in" aria-label="Zoom rice in">+</button><button type="button" data-camera="reset" aria-label="Reset rice view">⌖</button>';
 wrap.append(cameraControls);
 // Keep interaction chrome below, never on top of the specimen.
 const viewColumn=document.createElement('div');viewColumn.className='botanical-view';wrap.before(viewColumn);viewColumn.append(wrap);
 const toolbar=document.createElement('div');toolbar.className='specimen-toolbar';toolbar.setAttribute('aria-label','3D specimen controls');
 toolbar.append(cameraControls,realButton,wrap.querySelector('.specimen-caption'));viewColumn.append(toolbar,scrollHint);
 let width=600,height=650,frame=0,visible=false,paused=reduced.matches,last=0,yaw=0,targetYaw=0,pitch=0,targetPitch=0,zoom=1,targetZoom=1,baseYaw=0,drag=null,windAmount=.65,focusLeaf=null,overview=false;
 let mouseGust=0,gustTarget=0,mouseHeight=.5,pointerSample=null;
 let threeScene=null;
 const sceneStatus=document.createElement('span');sceneStatus.className='scene-status';sceneStatus.setAttribute('role','status');sceneStatus.textContent='Loading 3D specimen';wrap.append(sceneStatus);
 import('./rice-scene.js').then(module=>{
  threeScene=module.createRiceScene(canvas);sceneStatus.remove();draw(0);start();
 }).catch(error=>{sceneStatus.textContent='3D view unavailable. Enable hardware acceleration / WebGL.';console.error('Rice 3D scene:',error);});
 function draw(time){
  yaw+=(targetYaw-yaw)*.09;pitch+=(targetPitch-pitch)*.09;zoom+=(targetZoom-zoom)*.09;
  mouseGust+=(gustTarget-mouseGust)*.09;gustTarget*=.96;
  if(paused||reduced.matches)mouseGust=0;
  const desiredWind=mode==='wind'?Number($('botanical-wind').value):.65;windAmount+=(desiredWind-windAmount)*.025;
  if(mode==='leaf'){$('symptom-progress').value=String(Math.round(symptomProgress*100));$('symptom-progress-label').textContent=Math.round(symptomProgress*100)+'%';}
  threeScene?.render({mode,condition:currentCondition().id,progress:symptomProgress,time,wind:windAmount,gust:mouseGust,yaw,pitch,zoom,paused,reduced:reduced.matches,compare:$('compare-leaf-symptoms').checked,focusLeaf,overview});
 }
 function loop(now){if(!visible||paused||referenceModal.open){frame=0;return;}if(now-last>15){last=now;
   if(mode==='leaf'&&symptomPlaying){if(symptomLast)symptomProgress=Math.min(1,symptomProgress+Math.min((now-symptomLast)/1000,.08)/12);symptomLast=now;
    if(symptomProgress===1){symptomPlaying=false;$('symptom-play').textContent='Replay progression';$('symptom-play').setAttribute('aria-pressed','false');}}
   draw(now*.001);}frame=requestAnimationFrame(loop);}
 function start(){if(visible&&!paused&&!frame)frame=requestAnimationFrame(loop);else if(paused)draw(0);}
 function syncMotion(){const button=$('motion-toggle');button.setAttribute('aria-pressed',String(paused));button.setAttribute('aria-label',paused?'Play botanical animation':'Pause botanical animation');button.textContent=paused?'▷':'Ⅱ';start();}
 $('motion-toggle').addEventListener('click',()=>{paused=!paused;syncMotion();});
 reduced.addEventListener('change',()=>{paused=reduced.matches;$('symptom-play').disabled=reduced.matches;if(reduced.matches){symptomPlaying=false;$('symptom-play').textContent='Play progression';$('symptom-play').setAttribute('aria-pressed','false');}syncMotion();});
 new ResizeObserver(()=>{width=wrap.clientWidth;height=wrap.clientHeight;draw(0);}).observe(wrap);
 new IntersectionObserver(entries=>{visible=entries[0].isIntersecting&&!document.hidden;start();},{threshold:.01}).observe(wrap);
 document.addEventListener('visibilitychange',()=>{visible=!document.hidden&&!$('health').hidden;start();});
 function constrain(value,limit){return Math.max(-limit,Math.min(limit,value));}
 function interact(){if(paused){yaw=targetYaw;pitch=targetPitch;zoom=targetZoom;draw(0);}else start();}
 function cameraAction(action){
  if(action==='left'||action==='right'){baseYaw+=(action==='left'?-.25:.25);targetYaw=baseYaw;}
  if(action==='in'||action==='out')targetZoom=Math.max(.8,Math.min(1.45,targetZoom+(action==='in'?.1:-.1)));
  if(action==='reset'){baseYaw=targetYaw=targetPitch=0;targetZoom=1;overview=false;}
  if(action==='overview'){overview=true;baseYaw=targetYaw=targetPitch=0;targetZoom=1;}
  interact();
 }
 cameraControls.querySelectorAll('button').forEach(button=>button.addEventListener('click',()=>cameraAction(button.dataset.camera)));
 canvas.addEventListener('pointerdown',event=>{if(event.button!==0)return;drag={id:event.pointerId,x:event.clientX,y:event.clientY,yaw:baseYaw};canvas.setPointerCapture(event.pointerId);canvas.classList.add('is-turning');});
 canvas.addEventListener('pointermove',event=>{const rect=canvas.getBoundingClientRect(),now=performance.now();
  if(!drag&&pointerSample&&!reduced.matches){const dt=Math.max(8,now-pointerSample.time);gustTarget=constrain(gustTarget+(event.clientX-pointerSample.x)/dt*.5,1.8);mouseHeight=1-Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height));}
  pointerSample={x:event.clientX,time:now};
  if(drag){baseYaw=drag.yaw+(event.clientX-drag.x)/rect.width*Math.PI*2;targetYaw=baseYaw;targetPitch=constrain((event.clientY-drag.y)/rect.height*2,1.1);}
  else{targetYaw=baseYaw;}
  interact();
 });
 const endTurn=()=>{drag=null;canvas.classList.remove('is-turning');};canvas.addEventListener('pointerup',endTurn);canvas.addEventListener('pointercancel',endTurn);
 let tapStart=null;canvas.addEventListener('pointerdown',event=>{tapStart=[event.clientX,event.clientY];});
 canvas.addEventListener('click',event=>{if(!tapStart||Math.hypot(event.clientX-tapStart[0],event.clientY-tapStart[1])>6)return;const leaf=threeScene?.pickLeaf(event.clientX,event.clientY);if(!leaf)return;if(mode!=='leaf')hero.querySelector('[data-botanical="leaf"]').click();conditionSelect.value=leaf.condition;conditionSelect.dispatchEvent(new Event('change'));focusLeaf=leaf;overview=false;draw(performance.now()*.001);start();});
 canvas.addEventListener('pointerleave',()=>{pointerSample=null;if(!drag){targetYaw=baseYaw;targetPitch=0;gustTarget=0;interact();}});
 canvas.addEventListener('keydown',event=>{const actions={ArrowLeft:'left',ArrowRight:'right','+':'in','=':'in','-':'out',Home:'reset'};if(actions[event.key]){event.preventDefault();cameraAction(actions[event.key]);}else if(event.key==='ArrowUp'||event.key==='ArrowDown'){event.preventDefault();targetPitch=constrain(targetPitch+(event.key==='ArrowUp'?-.1:.1),.45);interact();}});
 function inspectCondition(index){
  const next=Math.max(0,Math.min(atlas.length-1,index));
  if(mode!=='leaf')hero.querySelector('[data-botanical="leaf"]').click();
  conditionSelect.value=atlas[next].id;conditionSelect.dispatchEvent(new Event('change'));
 }
 let scrollAccumulation=0,lastScrollStep=0,lastScrollEvent=0;
 hero.addEventListener('wheel',event=>{
  if(event.ctrlKey||event.metaKey||referenceModal.open||mode==='wind'||!event.target.closest('.botanical-canvas-wrap')||event.target.closest('input,select,button,.botanical-upload'))return;
  const direction=Math.sign(event.deltaY);if(!direction)return;
  const current=mode==='plant'?-1:conditionSelect.selectedIndex;
  if((current===atlas.length-1&&direction>0)||(current===-1&&direction<0))return;
  event.preventDefault();const now=performance.now();if(now-lastScrollEvent>180)scrollAccumulation=0;lastScrollEvent=now;
  scrollAccumulation+=event.deltaY;if(Math.abs(scrollAccumulation)<75||now-lastScrollStep<650)return;
  lastScrollStep=now;scrollAccumulation=0;
  if(current===0&&direction<0){hero.querySelector('[data-botanical="plant"]').click();return;}
  inspectCondition(current+direction);
 },{passive:false});
 canvas.addEventListener('keydown',event=>{if(event.key==='PageDown'||event.key==='PageUp'){event.preventDefault();inspectCondition((mode==='plant'?-1:conditionSelect.selectedIndex)+(event.key==='PageDown'?1:-1));}});
 syncMotion();
 referenceModal.addEventListener('close',()=>{symptomLast=0;start();});
 const screeningState=document.createElement('div');screeningState.className='screening-state';screeningState.setAttribute('role','status');screeningState.innerHTML='<span aria-hidden="true"></span>Analysing photograph';hero.querySelector('.photo-actions').append(screeningState);
 new MutationObserver(()=>hero.classList.toggle('has-photo',!$('photo-preview').hidden)).observe($('photo-preview'),{attributes:true,attributeFilter:['hidden']});
 // Progressive land/weather controls preserve the existing map and inference.
 const form=$('yield-form'),groups=Array.from(form.querySelectorAll('.input-group'));
 const steps=document.createElement('div');steps.className='field-steps';steps.setAttribute('aria-label','Field input steps');steps.innerHTML='<button type="button" aria-pressed="true">Land & crop</button><button type="button" aria-pressed="false">Weather</button>';
 groups[0].before(steps);
 const next=document.createElement('button');next.type='button';next.className='field-continue';next.innerHTML='Weather <span aria-hidden="true">→</span>';
 const plot=document.createElement('div');plot.className='land-composition';plot.innerHTML='<svg viewBox="0 0 360 160" role="img" aria-label="Proportion of entered land planted with rice"><defs><pattern id="rice-rows" width="9" height="9" patternUnits="userSpaceOnUse"><path d="M0 0V9" stroke="#b9d191" stroke-width="2"/></pattern><clipPath id="planted-clip"><rect id="planted-rect" x="0" y="0" width="0" height="110"/></clipPath></defs><g transform="translate(55 7) rotate(24 130 55) skewX(-23) scale(.84 .83)"><rect width="260" height="110" fill="#11160c" stroke="#546140"/><g clip-path="url(#planted-clip)"><rect width="260" height="110" fill="#2c3c1b"/><rect width="260" height="110" fill="url(#rice-rows)"/></g><path d="M0 116H260M266 0V110" stroke="#354327" stroke-width=".6"/></g><text x="180" y="148" text-anchor="middle" fill="#6f7d5b" font-size="9">ENTERED LAND / RICE COVERAGE</text></svg>';
 form.querySelector('.field-live').before(plot);
 function updatePlot(){const land=Number($('land-area').value),rice=Number($('area').value);$('planted-rect').setAttribute('width',String(land>0?260*Math.max(0,Math.min(rice/land,1)):0));}
 ['land-area','area'].forEach(id=>$(id).addEventListener('input',updatePlot));updatePlot();
 form.querySelector('.form-bottom').before(next);
 function showStep(index){if(index===1&&Array.from(groups[0].querySelectorAll('input')).some(input=>!input.reportValidity()))return;
  groups.forEach((group,i)=>group.hidden=i!==index);Array.from(steps.children).forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));
  next.hidden=index===1;plot.hidden=index===1;form.querySelector('.form-bottom').hidden=index===0;
 }
 Array.from(steps.children).forEach((button,i)=>button.addEventListener('click',()=>showStep(i)));next.addEventListener('click',()=>showStep(1));showStep(0);
 form.addEventListener('invalid',event=>{if(groups[0].contains(event.target))showStep(0);},true);
 document.addEventListener('pointerover',event=>{const button=event.target.closest('.primary,.field-continue');if(button){const r=button.getBoundingClientRect();button.style.setProperty('--hover-x',(event.clientX-r.left)+'px');button.style.setProperty('--hover-y',(event.clientY-r.top)+'px');}});
 // Architecture becomes an interactive model-path view, with technical detail
 // retained on demand instead of another wall of boxed paragraphs.
 function enhanceArchitecture(){
  for(const kind of ['yield','disease'])window.PaddyWorkspace?.mountArchitecture($('architecture-'+kind+'-panel'),kind);
 }
 new MutationObserver(enhanceArchitecture).observe($('architecture'),{childList:true});enhanceArchitecture();
})();
