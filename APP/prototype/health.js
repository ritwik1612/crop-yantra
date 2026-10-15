/* Disease awareness and a local photo workflow. No classifier or remote upload. */
(function(root){
 'use strict';
 const source='https://agritech.tnau.ac.in/org_farm/orgfarm_prac_agri_paddy_diseases.html';
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
 root.CropHealth={advisories,validateFile,makeRequest};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.CropHealth;
 if(typeof document==='undefined')return;
 const $=id=>document.getElementById(id),esc=value=>String(value).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 let context=null,imageMeta=null,objectURL=null,selectionVersion=0;
 function refresh(){
  $('health-context').textContent=context?.district?`${context.district}, ${context.state} · ${context.season} ${context.year} · ${context.areaHa??'—'} ha · Rice`:'No district selected. Choose one in the yield workspace; context will appear here automatically.';
  $('health-cards').innerHTML=advisories(context,$('growth-stage').value,$('field-conditions').value).map(d=>`<article class="disease-card"><img src="${d.image}" alt="Illustrative placeholder for ${d.name}; not a diagnostic photograph" loading="lazy"><div class="disease-body"><span class="small-badge">GENERAL AWARENESS · NOT A DIAGNOSIS</span><h3>${d.name}</h3><p>${d.symptoms}</p><details><summary>Why this reference appears</summary><p>${esc(d.reason)}</p><p>${d.favourable}</p><p>${d.stageMatch?'Your reported growth stage matches the handbook entry.':'No growth-stage match established.'} ${d.conditionMatch?'Your reported field conditions match the handbook entry.':'No condition match established.'} Season alone does not prove favourable weather.</p></details><a href="${d.source}" target="_blank" rel="noopener">Read agricultural source ↗</a></div></article>`).join('');
  $('prepare-screening').disabled=!imageMeta||!context?.district;
  if(imageMeta)$('photo-status').textContent='Photo stays on your device. Current context is linked; no disease classifier is connected.';
 }
 root.CropHealth.setContext=value=>{context=value;refresh();};
 ['growth-stage','field-conditions'].forEach(id=>$(id).addEventListener('change',refresh));
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
  try{const request=makeRequest(context,imageMeta,$('growth-stage').value,$('field-conditions').value);$('photo-status').textContent='Screening workflow prepared. Disease name: unavailable — no image classifier is connected. The selected context is included, but no image bytes leave your device.';
   const url=URL.createObjectURL(new Blob([JSON.stringify(request,null,2)],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='crop-yantra-photo-context.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
  }catch(error){$('photo-error').textContent=error.message;}
 });
 refresh();
})(typeof window!=='undefined'?window:globalThis);
