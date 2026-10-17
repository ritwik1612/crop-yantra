/* Disease awareness and a local photo workflow. No classifier or remote upload. */
(function(root){
 'use strict';
 const source='https://agritech.tnau.ac.in/org_farm/orgfarm_prac_agri_paddy_diseases.html';
 const referencePhotos={
  blast:{file:'assets/blast-real.jpg',title:'Rice blast symptoms',url:'https://commons.wikimedia.org/wiki/File:Rice_blast_symptoms.jpg',license:'Public domain',licenseURL:'https://creativecommons.org/publicdomain/mark/1.0/'},
  bacterial_blight:{file:'assets/blight-real.jpg',title:'Bacterial blight of rice',url:'https://commons.wikimedia.org/wiki/File:Bacterial_blight_of_rice.jpeg',license:'CC BY 3.0 US',licenseURL:'https://creativecommons.org/licenses/by/3.0/us/'},
  brown_spot:{file:'assets/brown-spot-real.jpg',title:'Brown spot of rice',url:'https://commons.wikimedia.org/wiki/File:Cochliobolus_miyabeanus.jpg',license:'CC BY 3.0 US',licenseURL:'https://creativecommons.org/licenses/by/3.0/us/'}
 };
 function imageCard(d,season,stage){
  const photo=referencePhotos[d.id];
  return `<div class="disease-visual"><button class="disease-flip" type="button" aria-pressed="false" aria-label="Show real ${d.name} reference photo"><span class="flip-inner"><span class="flip-front"><img src="${illustration(d.id,season,stage)}" alt="${d.name}: rice illustration, ${season}; not a diagnostic photograph"><span class="flip-caption">Illustration · hover or click for photo ↻</span></span><span class="flip-back" aria-hidden="true"><img src="${photo.file}" alt="${photo.title}: real symptom reference photo by Donald Groth" loading="lazy"><span class="flip-caption">Real symptom example · click to switch ↻</span></span></span></button><small class="photo-credit"><a href="${photo.url}" target="_blank" rel="noopener">${photo.title}</a> · Donald Groth, LSU AgCenter / Bugwood.org · <a href="${photo.licenseURL}" target="_blank" rel="noopener">${photo.license}</a>. Display cropped to fit. General reference, not local outbreak evidence.</small></div>`;
 }
 const catalogue=[
  {id:'blast',name:'Rice blast',stages:['seedling','tillering','booting','flowering','grain_filling'],conditions:['wet_cloudy'],symptoms:'Look for spindle-shaped leaf lesions with pale centres. Other disorders can look similar.',favourable:'Wet/cloudy conditions, frequent rain or drizzle and high humidity are described in the handbook.',image:'assets/blast-placeholder.svg'},
  {id:'bacterial_blight',name:'Bacterial leaf blight',stages:['tillering','booting','flowering'],conditions:['wet_cloudy','warm_humid'],symptoms:'Watch for lesions extending along the leaf. A photograph alone may not distinguish look-alike disorders.',favourable:'The handbook lists wet conditions and high temperature/humidity; growth stages include tillering to heading.',image:'assets/blight-placeholder.svg'},
  {id:'brown_spot',name:'Brown spot',stages:['flowering','grain_filling'],conditions:['warm_humid'],symptoms:'Look for small brown round-to-oval leaf spots. Seek expert confirmation rather than identifying from the placeholder.',favourable:'The handbook describes warm, humid conditions and flowering-to-maturity stages.',image:'assets/brown-spot-placeholder.svg'}
 ];
 function advisories(context,stage='unknown',conditions='unknown'){
  return catalogue.map(d=>({...d,source,
   stageMatch:d.stages.includes(stage),conditionMatch:d.conditions.includes(conditions),
   geographicEvidence:'general_rice_handbook_not_district_outbreak',
   reason:context?.district?`Selected: ${context.district}, ${context.state} · ${context.season} ${context.year}. No verified district/season outbreak record is connected.`:'Choose a district in the yield workspace. These are general rice references, not local outbreak alerts.'
  })).sort((a,b)=>(Number(b.stageMatch)+Number(b.conditionMatch))-(Number(a.stageMatch)+Number(a.conditionMatch)));
 }
 function validateFile(meta,bytes){
  if(!meta||meta.size<=0||meta.size>10*1024*1024)return 'Choose an image up to 10 MB.';
  const b=Array.from(bytes),png=[137,80,78,71,13,10,26,10].every((v,i)=>b[i]===v),jpg=b[0]===255&&b[1]===216&&b[2]===255;
  const webp=String.fromCharCode(...b.slice(0,4))==='RIFF'&&String.fromCharCode(...b.slice(8,12))==='WEBP';
  if(!((meta.type==='image/png'&&png)||(meta.type==='image/jpeg'&&jpg)||(meta.type==='image/webp'&&webp)))return 'Use a genuine JPEG, PNG or WebP image. SVG, HEIC and renamed non-images are not supported.';
  return null;
 }
 function makeRequest(context,image,stage,conditions){
  if(!context?.district)throw new Error('Select a district in the yield workspace first.');
  if(!image)throw new Error('Choose a supported photo first.');
  return {schemaVersion:1,mode:'pretraining_photo_workflow',crop:'Rice',
   context:{districtId:context.districtId,state:context.state,district:context.district,season:context.season,year:context.year,areaHa:context.areaHa},
   userReported:{growthStage:stage,conditions},image:{mimeType:image.mimeType,bytes:image.bytes,width:image.width,height:image.height},
   imageIncluded:false,photoTransmitted:false,imageClassifierConnected:false,diseaseName:null,
   result:'No diagnosis: image model not connected',
   notes:'Context can support a future image classifier but must not override visual evidence. No disease-related yield loss is inferred.'};
 }
 function illustration(disease,season='Kharif',stage='unknown'){
  const palettes={Kharif:['#e1ebe7','#315b48'],Rabi:['#e8ecdf','#536d43'],Summer:['#f2ead9','#6a7947'],Autumn:['#ede5d9','#736344'],Winter:['#e2e9ee','#46675d']};
  const [background,leaf]=palettes[season]||palettes.Kharif;
  const stages={unknown:'Unspecified stage',seedling:'Seedling',tillering:'Tillering',booting:'Booting',flowering:'Flowering',grain_filling:'Grain filling'};
  const label=stages[stage]||stages.unknown;
  const count=stage==='seedling'?2:stage==='tillering'?4:6;
  const leaves=Array.from({length:count},(_,i)=>{const side=i%2?-1:1,cy=216-i*21;return `<path d="M292 ${cy} Q${292+side*120} ${cy-32} ${292+side*134} ${cy-78} Q${292+side*30} ${cy-65} 292 ${cy}" fill="${leaf}" opacity="${.65+i*.05}"/>`;}).join('');
  const lesions=disease==='blast'?'<path d="M355 114l12-15 4 21-12 10zM219 161l-8-18-6 17 7 12z" fill="#bba36e" stroke="#6e513d" stroke-width="2"/>':disease==='brown_spot'?'<g fill="#a78459" stroke="#604b36" stroke-width="2"><ellipse cx="362" cy="110" rx="6" ry="4"/><ellipse cx="333" cy="127" rx="5" ry="3"/><ellipse cx="224" cy="155" rx="6" ry="4"/></g>':'<path d="M306 142 Q357 112 420 69 Q385 115 315 153" fill="#c1b378"/>';
  const panicle=['booting','flowering','grain_filling'].includes(stage)?'<path d="M292 124q-6-83 42-92" fill="none" stroke="#9e8a4a" stroke-width="3"/><g fill="#baa569">'+[0,1,2,3,4].map(i=>`<ellipse cx="${304+i*6}" cy="${50+i*12}" rx="6" ry="4" transform="rotate(-30 ${304+i*6} ${50+i*12})"/>`).join('')+'</g>':'';
  const safeSeason=palettes[season]?season:'Kharif';
  const markup=`<svg xmlns="http://www.w3.org/2000/svg" width="600" height="300" viewBox="0 0 600 300"><rect width="600" height="300" fill="${background}"/><circle cx="300" cy="138" r="113" fill="white" opacity=".35"/><path d="M292 248V92" stroke="${leaf}" stroke-width="5" fill="none"/>${leaves}${panicle}${lesions}<text x="24" y="27" fill="#354a3c" font-family="Arial,sans-serif" font-size="12">RICE / ${safeSeason.toUpperCase()}</text><text x="576" y="27" text-anchor="end" fill="#354a3c" font-family="Arial,sans-serif" font-size="12">${label.toUpperCase()}</text><path d="M170 251h250" stroke="#788774" opacity=".35"/><text x="300" y="281" text-anchor="middle" fill="#526453" font-family="Arial,sans-serif" font-size="10" letter-spacing="1">ILLUSTRATION ONLY · NOT A DIAGNOSIS</text></svg>`;
  return 'data:image/svg+xml;charset=utf-8,'+encodeURIComponent(markup);
 }
 root.CropHealth={advisories,validateFile,makeRequest,illustration,imageCard,referencePhotos};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.CropHealth;
 if(typeof document==='undefined')return;
 const $=id=>document.getElementById(id),esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let context=null,imageMeta=null,objectURL=null,selectionVersion=0;
 function refresh(){
  $('health-context').textContent=context?.district?`${context.district}, ${context.state} · ${context.season} ${context.year} · ${context.areaHa??'—'} ha · Rice`:'No district selected. Choose one in the yield workspace; context will appear here automatically.';
  $('health-cards').innerHTML=advisories(context,$('growth-stage').value,$('field-conditions').value).map(d=>`<article class="disease-card">${imageCard(d,$('health-season').value,$('growth-stage').value)}<div class="disease-body"><span class="small-badge">DISEASE REFERENCE</span><h3>${d.name}</h3><p>${d.symptoms}</p><details><summary>Conditions and source</summary><p>${esc(d.reason)}</p><p>${d.favourable}</p><p>${d.stageMatch?'Growth stage matches the reference.':'No growth-stage match.'} ${d.conditionMatch?'Reported conditions match the reference.':'No condition match.'}</p></details><a href="${d.source}" target="_blank" rel="noopener">TNAU reference ↗</a></div></article>`).join('');
  $('prepare-screening').disabled=!imageMeta||!context?.district;
  if(imageMeta)$('photo-status').textContent=root.CropDesktop?.ready?'Ready for offline rice screening. The photo is not uploaded.':'Photo stays on your device. Current context is linked; no disease classifier is connected.';
 }
 root.CropHealth.setContext=value=>{context=value;if(value?.season)$('health-season').value=value.season;refresh();};
 $('health-cards').addEventListener('click',event=>{
  const button=event.target.closest('.disease-flip');if(!button)return;
  const flipped=button.getAttribute('aria-pressed')!=='true';
  button.setAttribute('aria-pressed',String(flipped));
  button.classList.remove('hover-preview');
  button.querySelector('.flip-front').setAttribute('aria-hidden',String(flipped));
  button.querySelector('.flip-back').setAttribute('aria-hidden',String(!flipped));
  button.setAttribute('aria-label',flipped?'Show disease illustration':'Show real disease reference photo');
 });
 // Hover previews temporarily; clicking pins the real photo. Keyboard users can
 // toggle the same native button with Space or Enter, without needing hover.
 $('health-cards').addEventListener('pointerover',event=>{const button=event.target.closest('.disease-flip');if(button&&event.pointerType==='mouse'&&button.getAttribute('aria-pressed')!=='true'&&!button.contains(event.relatedTarget))button.classList.add('hover-preview');});
 $('health-cards').addEventListener('pointerout',event=>{const button=event.target.closest('.disease-flip');if(button&&!button.contains(event.relatedTarget))button.classList.remove('hover-preview');});
 ['growth-stage','field-conditions','health-crop'].forEach(id=>$(id).addEventListener('change',refresh));
 $('health-season').addEventListener('change',()=>{$('season').value=$('health-season').value;$('season').dispatchEvent(new Event('input',{bubbles:true}));});
 function clearPhoto(){selectionVersion++;if(objectURL)URL.revokeObjectURL(objectURL);objectURL=null;imageMeta=null;$('crop-photo').value='';$('photo-preview').removeAttribute('src');$('photo-preview').hidden=true;$('photo-empty').hidden=false;$('photo-info').textContent='JPEG / PNG / WebP · up to 10 MB';$('photo-status').textContent='No image selected. No photos are uploaded or stored by this demo.';$('photo-error').textContent='';$('prepare-screening').disabled=true;}
 $('remove-photo').addEventListener('click',clearPhoto);
 async function loadPhoto(file){
  clearPhoto();const version=selectionVersion;if(!file)return;
  const header=new Uint8Array(await file.slice(0,16).arrayBuffer());if(version!==selectionVersion)return;
  const error=validateFile(file,header);if(error){$('photo-error').textContent=error;return;}
  const url=URL.createObjectURL(file),image=new Image();
  image.onload=()=>{if(version!==selectionVersion){URL.revokeObjectURL(url);return;}
   if(image.naturalWidth<128||image.naturalHeight<128||image.naturalWidth*image.naturalHeight>24000000){URL.revokeObjectURL(url);$('photo-error').textContent='Use a clear photo at least 128 × 128 pixels and no more than 24 megapixels.';return;}
   objectURL=url;imageMeta={mimeType:file.type,bytes:file.size,width:image.naturalWidth,height:image.naturalHeight};
   $('photo-preview').src=url;$('photo-preview').hidden=false;$('photo-empty').hidden=true;$('photo-info').textContent=`${file.name} · ${image.naturalWidth} × ${image.naturalHeight} · ${(file.size/1024/1024).toFixed(2)} MB`;refresh();
  };
  image.onerror=()=>{URL.revokeObjectURL(url);if(version===selectionVersion)$('photo-error').textContent='The image could not be decoded. Try another JPEG, PNG or WebP.';};image.src=url;
 }
 $('crop-photo').addEventListener('change',event=>loadPhoto(event.target.files[0]).catch(()=>{$('photo-error').textContent='Could not read that image. Please try another file.';}));
 $('photo-drop').addEventListener('dragover',event=>{event.preventDefault();$('photo-drop').classList.add('drag-over');});
 $('photo-drop').addEventListener('dragleave',()=>$('photo-drop').classList.remove('drag-over'));
 $('photo-drop').addEventListener('drop',event=>{event.preventDefault();$('photo-drop').classList.remove('drag-over');loadPhoto(event.dataTransfer.files[0]).catch(()=>{$('photo-error').textContent='Could not read that image.';});});
 $('prepare-screening').addEventListener('click',()=>{
  try{const request=makeRequest(context,imageMeta,$('growth-stage').value,$('field-conditions').value);if(root.CropDesktop?.ready){root.CropDesktop.classifyImage(request,objectURL);return;}$('photo-status').textContent='Screening workflow prepared. Disease name: unavailable — no image classifier is connected. The selected context is included, but no image bytes leave your device.';
   root.PredictionFlow.showImage(request);
  }catch(error){$('photo-error').textContent=error.message;}
 });
 refresh();
})(typeof window!=='undefined'?window:globalThis);
