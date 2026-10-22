/* Native-only presentation and asynchronous local inference bridge. */
(function(root){
 'use strict';
 const $=id=>document.getElementById(id),esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])),n=(v,d=3)=>Number(v).toLocaleString('en-IN',{maximumFractionDigits:d});
 const labels={bacterial_leaf_blight:'Bacterial leaf blight',bacterial_leaf_streak:'Bacterial leaf streak',bacterial_panicle_blight:'Bacterial panicle blight',blast:'Rice blast',brown_spot:'Brown spot',dead_heart:'Dead heart',downy_mildew:'Downy mildew',hispa:'Hispa',normal:'Healthy / normal',tungro:'Tungro'};
 const table=(head,rows)=>`<div class="audit-table"><table><thead><tr>${head.map(v=>`<th>${esc(v)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
 const lane=(title,items)=>`<article class="architecture-lane"><h2>${title}</h2><ol>${items.map(([a,b])=>`<li><b>${a}</b><span>${b}</span></li>`).join('')}</ol></article>`;
 let yieldVersion=0;
 const native={ready:false};root.CropDesktop=native;
 native.helpText=(button,fallback)=>{
  if(button.closest('.chart-card'))return button.closest('.chart-card').querySelector('p:last-child')?.textContent||'Visual comparison of computed model outputs.';
  if(button.closest('.metric-heading'))return 'Change cultivation area to update production and value instantly. The model yield stays fixed; area scenarios are arithmetic, not a new forecast.';
  if(button.closest('.explanation-card,.result-section'))return 'The trained model estimates a seasonal scenario from your temperature and historical reference inputs. Production equals t/ha × hectares. This is not a validated current-season forecast.';
  if(button.closest('.context-card,#studio>.page-intro'))return 'Select a district on the map, season, average seasonal temperature and area. Today’s date is automatic. Unspecified weather uses training-season medians, not live observations.';
  if(button.closest('#health'))return 'Rice references are general guidance. Screening runs the trained EfficientNet-B0 locally on your photo. Season and district do not determine the image class.';
  if(button.closest('.info-intro'))return 'Sources, fitted preprocessing, trained predictors and limitations of the offline application.';
  if(button.closest('#preprocessing-section'))return 'Fit median imputation, scaling and category encoding on training rows only. Recent supervised models use standard features. DAE remains an older comparison, not the active route.';
  if(button.closest('#models-section'))return 'The validation-selected yield predictor is chosen automatically. The contextual residual MLP remains a research comparison. EfficientNet-B0 screens rice photographs.';
  if(button.closest('#output-section'))return 'Current-season scenario yield, derived production and optional gross value. Photo class scores are separate from yield; no disease-loss percentage is inferred.';
  return fallback;
 };
 native.predictYield=async function(request){
  const version=++yieldVersion,button=$('preview-button'),original=button.innerHTML;
  button.disabled=true;button.textContent='Computing locally…';$('form-error').textContent='';
  try{
   const result=await root.pywebview.api.predict_seasonal_yield(request);
   if(version!==yieldVersion||JSON.stringify(request)!==JSON.stringify(snapshot()))return;
   if(!result.ok)throw new Error(result.error);
   renderYield(request,result);native.yieldExportId=result.exportId;root.PredictionFlow.mode='yield';location.hash='results';
  }catch(error){$('form-error').textContent=error.message||'Local inference failed. Try again.';}
  finally{button.disabled=false;button.innerHTML=original;}
 };
 function renderSeasonalYield(request,r){
  const neural=r.modelKind==='mlp';let area=request.areaHa;
  const effects=r.contributions.slice(0,7),top=Math.max(...effects.map(v=>Math.abs(v.contribution)),.01);
  $('empty-result').hidden=true;$('result').hidden=false;
  $('result').innerHTML=`<div class="output-grid"><article class="yield-card"><p class="eyebrow">CURRENT-SEASON SCENARIO</p><div class="big-number">${n(r.yieldTPerHa)} <span>t/ha</span></div><p>${esc(request.district)} · ${esc(r.season)}<br>${esc(r.predictionDate)} · ${n(r.averageTemperatureC,1)} °C</p><div class="output-production"><span>Estimated production</span><b id="season-production"></b></div><p>${esc(r.model)}</p></article><article class="explanation-card"><h3>Seasonal estimate</h3><div class="formula" id="season-formula"></div><p>Temperature is your assumption. Other inputs use ${r.referenceCount} training-season records (${r.referenceYears[0]}–${r.referenceYears.at(-1)}).</p><p>Not a validated live-weather or farm-level forecast.</p>${neural?'<p class="error">Experimental neural option: weaker recent held-out results than the default tree model.</p>':''}<button class="primary" id="analyse-health" type="button">Analyse crop health →</button></article></div>
  <section class="metric-controls"><div class="metric-heading"><h3>Production scenarios</h3></div><div class="metric-fields"><label>Area (ha)<input id="season-area" type="number" min="0.01" max="1000000" step="0.01" value="${area}"></label><label>Area scenario <output id="season-area-label"></output><input id="season-area-slider" type="range" min="0.5" max="1.5" step="0.01" value="1"></label><label>Assumed price (₹/kg)<input id="season-price" type="number" min="0" max="100000" step="0.01" placeholder="Optional"></label></div><p id="season-error" class="error" role="alert"></p></section>
  <div class="output-kpis"><article><span>Production</span><strong id="season-tonnes"></strong></article><article><span>Harvest mass</span><strong id="season-kg"></strong></article><article><span>Area</span><strong id="season-hectares"></strong></article><article><span>Gross value</span><strong id="season-value">—</strong></article></div>
  <div class="charts-grid"><article class="chart-card"><h3>Production by area</h3><div id="season-chart"></div><p>Fixed model yield × area. Not confidence bounds.</p></article><article class="chart-card"><h3>${neural?'Input sensitivities':'Input contributions'}</h3><div class="local-influences">${effects.map(v=>`<div><span>${esc(v.feature)}</span><b>${v.contribution>=0?'+':''}${n(v.contribution)} t/ha</b><meter min="0" max="${top}" value="${Math.abs(v.contribution)}"></meter></div>`).join('')}</div><p>${neural?'Training-reference occlusion effects; not additive or causal.':'Tree-path contributions; not causal importance.'}</p></article></div>
  <details class="prediction-audit"><summary>Show prediction flow <span>Inputs · references · calculations</span></summary><div class="prediction-audit-body"><ol class="request-flow"><li><b>1. Take current-season inputs</b>${table(['Input','Value'],[['Prediction date',r.predictionDate],['District',request.district],['Season',r.season],['Average seasonal temperature',r.averageTemperatureC+' °C'],['User area',request.areaHa+' ha']])}</li><li><b>2. Construct the seasonal scenario</b><p>Saved training-season medians supply weather and district crop-area references. No observed yield is retrieved as a predictor. No neighbouring labels are invented. ${esc(r.temperatureMethod)}</p><p>The prediction date labels the request. Its crop-start year enters the learned trend and is extrapolated beyond training; this has not been validated as a current forecast.</p></li><li><b>3. Preprocess and run ${esc(r.model)}</b><p>Training median imputation → standardization → state/season one-hot encoding → ${neural?'weather MLP + district-season embedding + year trend':'boosted-tree traversal'}.</p>${table(['Feature','Scenario value','Imputed','Scaled'],r.features.map(f=>[f.name,n(f.raw,6),n(f.imputed,6),n(f.scaled,6)]))}${table(['Category','Encoded value'],Object.entries(r.encodedCategories))}${neural?`<code>Normalized network output × target std + target mean<br>${n(r.normalizedNetworkOutput,6)} × ${n(r.networkConfiguration.target_scale,6)} + ${n(r.networkConfiguration.target_mean,6)} = ${n(r.yieldTPerHa,6)} t/ha</code>`:`<code>Baseline + sum(tree-path contributions)<br>${n(r.baseline,6)} + ${n(r.contributions.reduce((sum,v)=>sum+v.contribution,0),6)} = ${n(r.yieldTPerHa,6)} t/ha</code>`}${table(['Feature',neural?'Occlusion effect t/ha':'Contribution t/ha'],r.contributions.map(v=>[v.feature,n(v.contribution,6)]))}</li><li><b>4. Derive output quantities</b><code id="season-audit-formula"></code><p>User hectares scale production; they do not replace the district-scale crop-area feature.</p></li></ol><p>Retrospective test MAE ${n(r.testMetrics.MAE)} t/ha; RMSE ${n(r.testMetrics.RMSE)}; R² ${n(r.testMetrics.R2)}. These scores do not validate the current-season scenario.</p></div></details>`;
  function refresh(){
   const tonnes=r.yieldTPerHa*area,kg=tonnes*1000;
   $('season-production').textContent=n(tonnes)+' t';$('season-formula').textContent=`${r.yieldTPerHa.toFixed(6)} t/ha × ${n(area,2)} ha ≈ ${n(tonnes)} tonnes`;
   $('season-audit-formula').textContent=`${r.yieldTPerHa.toFixed(6)} × ${area} = ${tonnes.toFixed(6)} tonnes; × 1,000 = ${kg.toFixed(3)} kg`;
   $('season-tonnes').textContent=n(tonnes)+' t';$('season-kg').textContent=n(kg,0)+' kg';$('season-hectares').textContent=n(area,2)+' ha';$('season-area-label').textContent=n(area,2)+' ha';
   const price=$('season-price'),hasPrice=price.value!==''&&price.validity.valid;
   $('season-value').textContent=hasPrice?'₹ '+n(kg*Number(price.value),0):'—';
   $('season-audit-formula').textContent+=(hasPrice?`\nGross value = ${kg.toFixed(3)} kg × ₹${Number(price.value)} / kg ≈ ₹${n(kg*Number(price.value),0)} (before costs).`:'\nGross value is not calculated until a valid price is supplied.');
   $('season-chart').innerHTML=`<svg class="result-chart" viewBox="0 0 560 220" role="img" aria-label="Production at half, entered and one-and-a-half times area">${[.5,1,1.5].map((f,i)=>`<rect x="${70+i*165}" y="${170-f/1.5*125}" width="95" height="${f/1.5*125}" rx="6" class="${i===1?'demo-bar':'observed-bar'}"/><text x="${117+i*165}" y="${158-f/1.5*125}" text-anchor="middle">${n(tonnes*f)} t</text><text x="${117+i*165}" y="198" text-anchor="middle">${n(area*f,2)} ha</text>`).join('')}</svg>`;
  }
  $('season-area').addEventListener('input',()=>{const el=$('season-area');if(!el.value||!el.validity.valid){$('season-error').textContent='Enter a valid positive area.';return;}area=Number(el.value);$('season-error').textContent='';refresh();});
  $('season-area-slider').addEventListener('input',()=>{area=Math.max(.01,Math.min(1e6,request.areaHa*Number($('season-area-slider').value)));$('season-area').value=area.toFixed(2);refresh();});
  $('season-price').addEventListener('input',refresh);
  const weatherNames={averageTemperatureC:'Average temperature (°C)',seasonalRainfallMm:'Total rainfall (mm)',relativeHumidityPct:'Relative humidity (%)',windSpeedMps:'Wind speed (m/s)',solarRadiationKwhM2Day:'Solar radiation (kWh/m²/day)'};
  const supplied=Object.entries(r.suppliedWeather||{averageTemperatureC:r.averageTemperatureC});
  $('result').querySelector('.explanation-card p').textContent=`${supplied.length} weather input${supplied.length===1?'':'s'} supplied by you. Blank fields use ${r.referenceCount} district-season reference records.`;
  const flow=$('result').querySelector('.request-flow');
  flow.children[0].insertAdjacentHTML('beforeend',table(['Additional input','Value'],[['Total land size',n(r.landAreaHa??request.areaHa,3)+' ha'],['Rice-planted area',n(request.areaHa,3)+' ha'],...supplied.map(([k,v])=>[weatherNames[k],n(v,3)])]));
  flow.children[1].querySelector('p').textContent='Your supplied weather values replace their matching features. Blank weather fields and district-level crop-area context use training-season medians. Derived ratios, vapour pressure, radiation totals and growing-degree-day approximations are recalculated. No observed yield is an input.';
  flow.children[2].querySelector('.audit-table').outerHTML=table(['Feature','Input source','Value','Imputed','Scaled'],r.features.map(f=>[f.name,r.inputProvenance?.[f.name]||'Training reference',n(f.raw,6),n(f.imputed,6),n(f.scaled,6)]));
  if(r.referenceKind==='synthetic_neighbour_transfer'){
   const explanation=$('result').querySelector('.explanation-card p');
   explanation.textContent='Neighbour-based estimate · synthetic geographic transfer. '+supplied.length+' weather input'+(supplied.length===1?'':'s')+' supplied by you.';
   flow.children[1].querySelector('p').textContent='Missing local references are estimated from three geographically nearest training districts in the same season and crop year. Synthetic rows receive a lower training weight. Supplied weather replaces these references; derived features are recalculated. No observed local yield is claimed.';
   const donorRows=(r.neighbourReferences||[]).flatMap(ref=>ref.donors.map(d=>[ref.year,d.district,d.state,n(d.distanceKm,1)+' km',n(d.weight*100,1)+'%']));
   flow.children[1].insertAdjacentHTML('beforeend',table(['Training year','Donor district','State','Distance','Weight'],donorRows));
   const auditNote=$('result').querySelector('.prediction-audit-body>p');
   if(auditNote)auditNote.textContent=`Coverage-model test MAE ${n(r.testMetrics.MAE)} t/ha; RMSE ${n(r.testMetrics.RMSE)}. Evaluated on measured 2023–2024 records, not on missing districts. Missing-district and current-season accuracy remain unmeasured.`;
  }
  if(!neural||r.networkConfiguration?.use_year_trend===false){const note=Array.from($('result').querySelectorAll('p')).find(p=>p.textContent.startsWith('The prediction date labels'));if(note)note.textContent='The prediction date labels the request. This predictor does not use a year trend. Season and reference features determine the estimate.';}
  $('analyse-health').addEventListener('click',()=>{root.CropHealth.setContext({...request,areaHa:area,predictionDate:r.predictionDate});location.hash='health';});
  root.PaddyWorkspace?.renderContributions?.($('result'),r,request);
  root.PaddyWorkspace?.renderRunSummary?.($('result'),r,request);
  root.PaddyHelp?.decorate?.();refresh();
 }
 function renderYield(request,r){
  if(r.scope==='current_season_scenario'){renderSeasonalYield(request,r);return;}
  const neural=r.modelKind==='mlp';
  const contextAudit=r.contextInputs?table(['Extra neural input','Observed value','Model input'],[['Crop year',r.contextInputs.year,n(r.contextInputs.scaled_year,6)],['District-season context',r.sourceState+' / '+r.district+' / '+r.season,r.contextInputs.district_index]]):'';
  const modelAudit=neural?`<li><b>3. Run the trained MLP neural network</b><code>28 standard inputs → Dense 64 → GELU → Dense 32 → GELU → weather output<br>${r.contextInputs?'Add learned district-season offset + linear year trend (30 input fields total).<br>':''}Dropout ${r.networkConfiguration.dropout} is disabled at inference.<br>Yield = network output × training-target std + training-target mean<br>${n(r.normalizedNetworkOutput,6)} × ${n(r.networkConfiguration.target_scale,6)} + ${n(r.networkConfiguration.target_mean,6)} = ${n(r.yieldTPerHa,6)} t/ha</code>${contextAudit}<p>AdamW + MSE; validation-selected epoch ${r.networkConfiguration.best_epoch}. Test RMSE ${n(r.testMetrics.RMSE)} versus tree benchmark 0.672 t/ha. ${r.contextInputs?'Year and district context are additional observed inputs. Test MAE is 0.486 t/ha versus the tree benchmark 0.532; tree RMSE remains lower. This is temporal evaluation within known districts, not new-district validation.':'The neural model has not outperformed the tree benchmark.'}</p>${table(['Input','Reference-occlusion effect (t/ha)'],r.contributions.map(v=>[v.feature,n(v.contribution,6)]))}<p>Sensitivity = original prediction minus prediction after replacing one input (or a whole category group) with its training reference. Year is referenced to the training mean; district context to the explicit unknown-context embedding. These effects do not sum to the predicted yield.</p></li>`:`<li><b>3. Traverse the trained boosted trees</b><code>Yield = baseline + sum of all feature path contributions<br>${n(r.baseline,6)} + (${n(r.contributions.reduce((s,v)=>s+v.contribution,0),6)}) = ${n(r.yieldTPerHa,6)} t/ha</code>${table(['Feature','Path contribution (t/ha)'],r.contributions.map(v=>[v.feature,n(v.contribution,6)]))}<p>Validation-selected tree benchmark. Select MLP in Yield studio to run the trained neural network instead.</p></li>`;
  let area=request.areaHa;
  const max=Math.max(r.yieldTPerHa,r.observedYield,1)*1.25;
  $('empty-result').hidden=true;$('result').hidden=false;
  $('result').innerHTML=`<div class="output-grid"><article class="yield-card"><p class="eyebrow">HISTORICAL YIELD ESTIMATE</p><div class="big-number">${n(r.yieldTPerHa)} <span>t/ha</span></div><p>${esc(request.district)} · ${esc(r.season)} ${r.year}</p><div class="output-production"><span>Estimated production</span><b id="local-production"></b></div><p>${esc(r.model)} · standard representation</p></article><article class="explanation-card"><p class="eyebrow">MODEL OUTPUT</p><h3>District-scale estimate</h3><p>Computed from the matching historical district-season weather and area record, not a live forecast or farm-level validation.</p><div class="formula" id="local-formula"></div><p>Historical observed yield: ${n(r.observedYield)} t/ha. Prediction difference: ${n(r.yieldTPerHa-r.observedYield)} t/ha.</p><p>Record split: <b>${esc(r.split)}</b> · source state: ${esc(r.sourceState)}</p>${r.warnings.map(w=>`<p class="error">${esc(w)}</p>`).join('')}</article></div><section class="metric-controls"><div class="metric-heading"><div><p class="eyebrow">AREA SCENARIOS</p><h3>Adjust cultivation area</h3><p>The predicted yield remains fixed. Production and value update instantly.</p></div></div><div class="metric-fields"><label>Area (hectares)<input id="local-area" type="number" min="0.01" max="1000000" step="0.01" value="${area}"></label><label>Area scenario <output id="local-area-label"></output><input id="local-area-slider" type="range" min="0.5" max="1.5" step="0.01" value="1"></label><label>Assumed price (₹/kg)<input id="local-price" type="number" min="0" max="100000" step="0.01" placeholder="Optional"></label></div><p id="local-area-error" class="error" role="alert"></p></section><div class="output-kpis"><article><span>Production</span><strong id="local-tonnes"></strong><p>Yield × your area</p></article><article><span>Harvest mass</span><strong id="local-kg"></strong><p>Tonnes × 1,000</p></article><article><span>Scenario area</span><strong id="local-hectares"></strong><p>User input, not district crop area</p></article><article><span>Gross harvest value</span><strong id="local-value">—</strong><p>Excludes costs and losses</p></article></div><div class="charts-grid"><article class="chart-card"><p class="eyebrow">MODEL / OBSERVATION</p><h3>Yield comparison</h3><svg class="result-chart" viewBox="0 0 560 220" role="img" aria-label="Predicted and observed historical yield">${[r.yieldTPerHa,r.observedYield].map((v,i)=>`<rect x="${100+i*230}" y="${170-v/max*125}" width="100" height="${v/max*125}" rx="6" class="${i?'observed-bar':'demo-bar'}"/><text x="${150+i*230}" y="${158-v/max*125}" text-anchor="middle">${n(v)} t/ha</text><text x="${150+i*230}" y="199" text-anchor="middle">${i?'Observed':'Predicted'}</text>`).join('')}<line x1="45" y1="170" x2="520" y2="170" class="chart-axis"/></svg><p>Observed yield is a comparison label, never a model input.</p></article><article class="chart-card"><p class="eyebrow">LOCAL MODEL EXPLANATION</p><h3>${neural?'Largest input sensitivities':'Largest path contributions'}</h3><div class="local-influences">${r.contributions.slice(0,7).map(row=>`<div><span>${esc(row.feature)}</span><b>${row.contribution>=0?'+':''}${n(row.contribution)} t/ha</b><meter min="0" max="${Math.max(...r.contributions.map(v=>Math.abs(v.contribution)),.01)}" value="${Math.abs(row.contribution)}"></meter></div>`).join('')}</div><p>${neural?'Difference when each input is replaced by its training reference (mean for numbers; training-mode state/season). Effects are not additive, causal or SHAP values.':'Tree-path contribution, not SHAP or causal importance. Correlated features can share attribution.'}</p></article></div><details class="prediction-audit"><summary>Show prediction flow <span>Actual inputs · transforms · calculations</span></summary><div class="prediction-audit-body"><ol class="request-flow"><li><b>1. Retrieve exact historical inputs</b><p>${esc(request.district)} / ${r.year} / ${esc(r.season)}. Rice crop records + district coordinates + aggregated NASA POWER weather. No neighbouring district or invented future weather is substituted.</p></li><li><b>2. Apply the saved preprocessing</b><code>Missing numeric → training median<br>Scaled = (imputed value − training mean) / training standard deviation<br>State + season → OneHotEncoder<br>21 numerical + 7 category indicators = 28 predictors</code>${table(['Feature','Historical value','After imputation','Scaled input'],r.features.map(f=>[f.name,f.raw===null?'Missing':n(f.raw,6),n(f.imputed,6),n(f.scaled,6)]))}${table(['Category indicator','Input value'],Object.entries(r.encodedCategories))}</li>${modelAudit}<li><b>4. Derive production and mass</b><code id="local-audit-formula"></code><p>User hectares only scale production. The model still receives historical district crop area, not the user's farm area.</p></li></ol><p>Held-out test MAE ${n(r.testMetrics.MAE)} t/ha · RMSE ${n(r.testMetrics.RMSE)} · R² ${n(r.testMetrics.R2)}. These are aggregate test metrics, not confidence bounds for this result.</p></div></details>`;
  function refresh(){
   const tonnes=r.yieldTPerHa*area,kg=tonnes*1000;
   $('local-production').textContent=n(tonnes)+' t';$('local-formula').textContent=`${n(r.yieldTPerHa)} t/ha × ${n(area,2)} ha = ${n(tonnes)} tonnes`;
   $('local-audit-formula').textContent=`${r.yieldTPerHa.toFixed(6)} t/ha × ${area} ha = ${tonnes.toFixed(6)} tonnes; × 1,000 = ${kg.toFixed(3)} kg`;
   $('local-tonnes').textContent=n(tonnes)+' t';$('local-kg').textContent=n(kg,0)+' kg';$('local-hectares').textContent=n(area,2)+' ha';$('local-area-label').textContent=n(area,2)+' ha';
   const p=$('local-price');$('local-value').textContent=p.value!==''&&p.validity.valid?'₹ '+n(kg*Number(p.value),0):'—';
  }
  $('local-area').addEventListener('input',()=>{const input=$('local-area');if(!input.value||!input.validity.valid){$('local-area-error').textContent='Enter a valid positive area.';return;}area=Number(input.value);$('local-area-error').textContent='';refresh();});
  $('local-area-slider').addEventListener('input',()=>{area=Math.max(.01,Math.min(1000000,request.areaHa*Number($('local-area-slider').value)));$('local-area').value=area.toFixed(2);$('local-area-error').textContent='';refresh();});
  $('local-price').addEventListener('input',refresh);refresh();
 }
 native.classifyImage=async function(request,url){
  document.querySelector('.botanical-stage')?.classList.add('is-screening');
  const button=$('prepare-screening');button.disabled=true;button.textContent='Screening locally…';$('photo-error').textContent='';
  try{
   const blob=await (await fetch(url)).blob();
   const encoded=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=reject;reader.readAsDataURL(blob);});
   const result=await root.pywebview.api.classify_image(encoded);
   if($('photo-preview').src!==url)return;
   if(!result.ok)throw new Error(result.error);
   const r=result,linkedContext=request.context;
   request={...request,context:linkedContext||{}};
   $('image-result').innerHTML=`<article class="image-output-card"><p class="eyebrow">OFFLINE RICE SCREENING</p><h2>${r.uncertain?'Result uncertain':esc(labels[r.label])}</h2><p>${r.uncertain?'Use a clearer photo and seek expert confirmation. Highest-scoring candidate: '+esc(labels[r.candidate])+'.':'Candidate classification, not a confirmed diagnosis.'}</p><div class="screening-grid"><img class="screening-photo" src="${esc(url)}" alt="Selected rice photo"><div>${root.HealthScoreBars.renderRows(r.scores,labels)}<p>Model scores, not diagnostic confidence.</p></div></div>${r.warnings.map(w=>`<p class="error">${esc(w)}</p>`).join('')}<p>${esc(r.notice)}</p><p>Context: ${esc(request.context.district)}, ${esc(request.context.state)} · ${esc(request.context.season)}. Context does not change the pixel-based class or predicted yield.</p><a href="#health" class="inline-link">Screen another photo →</a></article><details class="prediction-audit"><summary>Show prediction flow <span>Photo · image transforms · model scores</span></summary><div class="prediction-audit-body"><ol class="request-flow"><li><b>1. Validate the rice photo</b><p>${r.width} × ${r.height} pixels; ${n(request.image.bytes/1024,1)} KB. File format, dimensions, contrast and basic blur/lighting checks. Processing stays on this PC. The photo is saved only when you export it inside a PDF.</p></li><li><b>2. Prepare the pixels</b><code>Orientation correction → RGB → shorter edge 256 → centre crop 224 × 224<br>Channel = (pixel / 255 − mean) / standard deviation<br>Mean [0.485, 0.456, 0.406], std [0.229, 0.224, 0.225]</code></li><li><b>3. EfficientNet-B0 → logits → softmax</b><code>pᵢ = exp(zᵢ − max(z)) / Σ exp(zⱼ − max(z))</code>${table(['Class','Actual logit','Model score'],r.scores.map((s,i)=>[labels[s.label],n(r.logits[i],6),n(s.score*100,3)+'%']))}</li><li><b>4. Apply the screening guard</b><p>Abstain when the highest score is below ${n(r.threshold*100,0)}% or basic quality warnings occur. This threshold is a conservative heuristic, not clinically or agronomically calibrated. Unsupported crops and diseases are not reliably rejected.</p><p>Image regions are not attributed. Weather inputs do not explain the class. Held-out ten-class test accuracy: ${n(r.testMetrics.accuracy*100,2)}%; macro-F1: ${n(r.testMetrics.macro_F1*100,2)}%. These describe all test classifications before the optional screening guard.</p></li></ol></div></details>`;
   if(!linkedContext)Array.from($('image-result').querySelectorAll('p')).find(p=>p.textContent.startsWith('Context:'))?.remove();
   native.healthExport={id:r.exportId,url};
   root.PredictionFlow.mode='image';location.hash='image-results';$('photo-status').textContent='Screening completed locally. Photo not uploaded.';
  }catch(error){$('photo-error').textContent=error.message||'Local image screening failed.';}
  finally{button.disabled=$('photo-preview').hidden;button.textContent='Screen rice photo →';document.querySelector('.botanical-stage')?.classList.remove('is-screening');}
 };
 function mountPDFExport(){
  if($('export-pdf'))return;
  const open=document.createElement('button');open.id='export-pdf';open.type='button';open.className='pdf-export-button';open.textContent='Export PDF';
  $('results').querySelector('.page-intro').append(open);
  const status=document.createElement('p');status.id='pdf-export-status';status.className='pdf-export-status';status.setAttribute('role','status');open.after(status);
  const dialog=document.createElement('dialog');dialog.className='pdf-export-dialog';dialog.setAttribute('aria-labelledby','pdf-export-title');
  dialog.innerHTML='<button type="button" class="pdf-close" aria-label="Close PDF export">×</button><h2 id="pdf-export-title">Export report</h2><p>Select the results to include.</p><fieldset><legend>Report contents</legend><label><input type="radio" name="pdf-mode" value="yield">Yield prediction</label><label><input type="radio" name="pdf-mode" value="health">Crop health and uploaded photo</label><label><input type="radio" name="pdf-mode" value="combined">Yield and crop health</label></fieldset><p class="pdf-export-message" role="status"></p><button type="button" class="primary" id="save-pdf">Save PDF</button>';
  document.body.append(dialog);
  dialog.querySelector('.pdf-close').addEventListener('click',()=>dialog.close());
  open.addEventListener('click',()=>{
   const hasYield=Boolean(native.yieldExportId&&!$('result').hidden),hasHealth=Boolean(native.healthExport?.id&&!$('photo-preview').hidden&&$('photo-preview').src===native.healthExport.url);
   const allowed={yield:hasYield,health:hasHealth,combined:hasYield&&hasHealth};
   dialog.querySelectorAll('[name="pdf-mode"]').forEach(input=>{input.disabled=!allowed[input.value];input.checked=false;});
   const preferred=location.hash==='#image-results'?'health':'yield',selected=allowed[preferred]?preferred:hasYield?'yield':hasHealth?'health':null;
   if(!selected){status.textContent='Run a yield prediction or screen a photo first.';return;}
   dialog.querySelector('[value="'+selected+'"]').checked=true;dialog.querySelector('.pdf-export-message').textContent='';dialog.showModal();
  });
  $('save-pdf').addEventListener('click',async()=>{
   const button=$('save-pdf'),message=dialog.querySelector('.pdf-export-message');button.disabled=true;message.textContent='Preparing PDF…';
   try{
    const area=$('season-area'),price=$('season-price');
    const mode=dialog.querySelector('[name="pdf-mode"]:checked')?.value;
    const options={mode,yieldId:native.yieldExportId,healthId:native.healthExport?.id};
    if(mode!=='health'){
     if(!area?.value||!area.validity.valid||price?.value&&!price.validity.valid)throw new Error('Correct the area or price on the result page before exporting.');
     options.scenario={areaHa:Number(area.value),priceINRPerKg:price?.value!==''?Number(price.value):null};
    }
    const result=await root.pywebview.api.export_pdf(options);
    if(result.cancelled){message.textContent='Save cancelled.';return;}
    if(!result.ok)throw new Error(result.error||'The PDF could not be saved.');
    if(result.pdfBase64){const bytes=Uint8Array.from(atob(result.pdfBase64),c=>c.charCodeAt(0)),url=URL.createObjectURL(new Blob([bytes],{type:'application/pdf'})),link=document.createElement('a');link.href=url;link.download=result.filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
    status.textContent='Saved '+result.filename;dialog.close();
   }catch(error){message.textContent=error.message||'PDF export failed. Please try again.';}
   finally{button.disabled=false;}
  });
 }
 async function initialize(){
  if(native.ready)return;
  try{const status=await root.pywebview.api.status();if(!status.ok)return;native.ready=true;if(status.pdfExportAvailable)mountPDFExport();
   document.querySelector('.status').innerHTML='<i></i> Local models';
   document.querySelector('#studio h1').textContent='Yield estimate';
   document.querySelector('#studio .intro-copy').textContent='Choose a district on the map, then set your season, temperature and area.';
   document.querySelector('.info-intro h1').textContent='Method and models';
   $('preview-button').textContent='Estimate yield';
   native.selectedYieldModel=status.yieldDefaultModel||'gbdt';
   document.querySelector('.demo-message').innerHTML='<p>Seasonal estimate; not a live-weather forecast.</p>';
   document.querySelector('#studio .intro-note').innerHTML='<span class="leaf">↗</span><b>Runs on your PC</b><span>Trained yield model.<br>Rice-photo screening.</span>';
   document.querySelector('#health .intro-copy').textContent='Rice disease references and offline photo screening.';
   document.querySelector('.health-disclaimer').textContent='Illustrations and photographs are general references. No local outbreak data or confirmed diagnosis. Consult an agricultural expert for symptoms.';
   document.querySelector('.photo-card > p:not(.eyebrow)').textContent='Choose a clear rice-leaf photo. Screening runs on this PC. Photos are not uploaded. PDF export saves your chosen photo inside the report.';
   document.querySelector('.photo-card .eyebrow').textContent='OFFLINE IMAGE MODEL';
   $('prepare-screening').textContent='Screen rice photo →';
   $('photo-status').textContent='Select a rice photo. Nothing is uploaded.';
   document.querySelector('.info-intro .intro-copy').textContent='Sources, fitted preprocessing and trained prediction models.';
   root.PaddyWorkspace?.configure?.(status);
   root.PaddyArchitecture.mount($('architecture'),true,status.yieldConfiguration);
   $('models-section').innerHTML='<h2>Trained models</h2><p><b>Neural yield model:</b> standard preprocessing → Contextual Residual MLP regressor: weather MLP (28 → 64 → 32 → 1, GELU) + learned district-season offset + linear year trend. AdamW + MSE, validation-selected epoch 114. Test MAE 0.486 t/ha, RMSE 0.677, R² 0.447. The original non-contextual MLP had RMSE 0.733.</p><p><b>Tree benchmark:</b> HistGradientBoostingRegressor. Test MAE 0.532 t/ha, RMSE 0.672, R² 0.456. It has lower RMSE than the contextual MLP, but slightly higher MAE. Both are selectable in Yield studio. The contextual neural experiment also uses year and a learned district offset. Performance varies by state; no farm-level accuracy claim.</p><p><b>Images:</b> ImageNet-initialized EfficientNet-B0, fine-tuned on 5,905 rice photos with 1,257 validation and 1,257 test photos. Ten-class test accuracy 85.04%, macro-F1 83.59%. The classes include pest symptoms and normal plants; this is not confirmed diagnosis. Unsupported crops/diseases are not reliably rejected.</p>';
   $('output-section').innerHTML='<h2>Outputs</h2><p>Historical district yield in t/ha; production scaled by user hectares; mass and optional gross value. Yield output includes actual retrieved features, transformed values, model calculations and either neural input sensitivities or tree-path contributions under Show prediction flow.</p><p>Photo output includes a candidate rice class or uncertain result, ten model scores and actual logits. It does not calculate disease-related yield loss or change the yield estimate.</p>';
   document.querySelectorAll('.help-trigger').forEach(button=>{if(button.title?.includes('preview'))button.title='Section information';});
   const ds=status.yieldDataset,cfg=status.yieldConfiguration,tree=status.yieldTest;
   if(ds){
    const source=$('sources-section');source.querySelector('.flow-final').textContent=`Rice master · ${ds.rows} × 30`;
    source.querySelector('p:last-child').textContent='Original government crop records are extended with attributed UPAg/DES records from India Data Portal. Exact normalized same-state district matching; complete seasonal NASA weather only. Rabi and Winter cross the agricultural-year boundary; Summer uses the following calendar year. Unmatched districts are excluded, not filled with generated labels.';
    source.insertAdjacentHTML('beforeend','<p><a href="https://ckandev.indiadataportal.com/dataset/area-production-yield-apy" target="_blank" rel="noopener">UPAg/DES source via India Data Portal ↗</a> · Open Data Commons Attribution License.</p>');
    const mergeDetails=document.createElement('details');mergeDetails.className='source-details';
    const mergeSummary=document.createElement('summary');mergeSummary.textContent='Merge method & attribution';mergeDetails.append(mergeSummary);
    Array.from(source.children).filter(el=>el.tagName==='P').forEach(el=>mergeDetails.append(el));source.append(mergeDetails);
    $('preprocessing-section').innerHTML=`<h2>Preprocessing</h2><div class="split-strip"><div><b>Train</b><strong>${ds.split_rows.train}</strong><span>2001–2020</span></div><div><b>Validation</b><strong>${ds.split_rows.validation}</strong><span>2021–2022</span></div><div><b>Test</b><strong>${ds.split_rows.test}</strong><span>2023–2024</span></div></div><div class="flow"><span>21 numerical features</span><b>→</b><span>SimpleImputer</span><b>→</b><span>StandardScaler</span><b>+</b><span>OneHotEncoder</span><b>→</b><span>${cfg.architecture[0]} predictors</span></div><p>Transforms are fitted on training rows only. State and season are encoded; production and yield are excluded from predictors. District identifiers feed the optional neural embedding. DAE remains a separate older experiment and is not used by these deployed models.</p>`;
    $('models-section').innerHTML=`<h2>Trained models</h2><h3>HistGradientBoostingRegressor · default</h3><p>Selected by validation RMSE. Held-out 2023–2024: MAE ${n(tree.MAE)} t/ha, RMSE ${n(tree.RMSE)}, R² ${n(tree.R2)}.</p><h3>Contextual Residual MLP · experimental</h3><p>${cfg.architecture.join(' → ')} weather network with GELU and learned district-season offsets. ${cfg.use_year_trend===false?'No year trend in the selected candidate.':'Includes a learned linear year trend.'} Held-out MAE ${n(cfg.test.MAE)} t/ha, RMSE ${n(cfg.test.RMSE)}, R² ${n(cfg.test.R2)}. This model is weaker than the default tree on recent evaluation.</p><h3>EfficientNet-B0 · photo screening</h3><p>8,419 duplicate-filtered rice photos; 5,905 train, 1,257 validation, 1,257 test. Ten-class test accuracy 85.04%; macro-F1 83.59%. District and weather are not image-classifier inputs.</p><p>Yield metrics are retrospective, district-scale and cohort-specific. They do not establish live current-season forecast accuracy.</p>`;
    root.PaddyPipeline?.mount(ds);
   }
   $('output-section').innerHTML='<h2>Prediction and output</h2><p>Map-selected district + season + assumed average temperature + area → training-season reference features → saved preprocessing → trained yield predictor → scenario yield (t/ha). Multiply yield × hectares for tonnes; × 1,000 for kilograms; × optional price for gross value.</p><p>Unspecified weather uses training-season medians. This is a current-season scenario, not a validated live forecast. Open Show prediction flow for the exact inputs and calculations.</p><p>Photo-only screening needs no district. Analyse crop health after a yield result to carry its location and season as reference context. The image classifier uses pixels only; it does not adjust predicted yield.</p>';
  if(status.yieldCoverage){
   const coverage=document.createElement('p');coverage.textContent='Missing district-season references use a separate neighbour-augmented HistGradientBoostingRegressor. '+n(status.yieldCoverage.synthetic_train_rows,0)+' explicitly synthetic training rows supplement '+n(status.yieldCoverage.measured_train_rows,0)+' measured rows. Donors are training-only, geographically nearest districts in the same season and crop year. Local measured accuracy is not established for these transferred estimates.';
   $('models-section').append(coverage);
  }
  }catch{native.ready=false;$('form-error').textContent='Local model bridge could not initialize. Close and reopen the app.';}
 }
 root.addEventListener('pywebviewready',initialize);if(root.pywebview?.api)initialize();
})(window);
