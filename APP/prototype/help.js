/* Short section explanations and a clearly hypothetical worked example. */
(function(root){
 'use strict';
 const explanations=[
  ['#studio>.page-intro h1','Select a location and crop context, preview yield arithmetic, then review rice health references below. This is a pretraining beta.'],
  ['#info .info-intro h1','Project sources, fitted preprocessing, proposed yield predictors and the hypothetical calculation are documented here.'],
  ['.source:nth-child(1) h3','Government observations provide crop year, season, district, area and production. Yield is derived as production divided by area.'],
  ['.source:nth-child(2) h3','GADM provides administrative boundaries and representative district coordinates for weather matching and map display.'],
  ['.source:nth-child(3) h3','NASA POWER daily weather is summarized over fixed seasonal windows. These aggregates are inputs, not disease labels.'],
  ['.representation-grid>div:nth-child(1) h3','Standard inputs retain 21 scaled numerical features and 7 encoded state/season indicators.'],
  ['.representation-grid>div:nth-child(2) h3','DAE inputs contain 8 learned numerical features, 7 category indicators and 1 reconstruction score.'],
  ['.model-grid>div:nth-child(1) h3','The MLP is a neural-network regressor to be trained against observed yield. Its supervised weights are not trained yet.'],
  ['.model-grid>div:nth-child(2) h3','Gradient-boosted trees provide a non-DL comparison using the same training, validation and test partitions.'],
  ['.map-card h2','Select a state, then a district. Boundaries use GADM 4.1; historical training coverage is marked separately.'],
  ['.context-card h2','Set district, season, year and area. Representation and predictor select a proposed model route; no trained yield model is connected.'],
  ['.result-section> .section-title h2','This is a pretraining demonstration. Yield is a manual assumption; production is yield multiplied by hectares.'],
  ['.metric-heading h3','Change the yield assumption or cultivation area. Arithmetic and charts update immediately; no model is run.'],
  ['.visual-output>.section-title h2','Production, mass and area are derived from your inputs. Recorded district yield is an independent historical reference.'],
  ['.chart-card:nth-child(1) h3','Compare the demo yield with one matching district, year and season observation. Missing history is not treated as zero.'],
  ['.chart-card:nth-child(2) h3','The line shows production at a fixed yield as cultivation area changes. The marker follows the area slider; it is not a confidence interval.'],
  ['.chart-card:nth-child(3) h3','These are recorded yields for the selected season, through the selected year. Hover or focus a point to see its value.'],
  ['.chart-card:nth-child(4) h3','Gross value equals production in kilograms multiplied by your assumed price. It excludes costs and does not estimate profit.'],
  ['.explanation-card h3','The current demo uses a yield assumption, not trained inference. Production equals tonnes per hectare multiplied by entered hectares.'],
  ['#health h1','Rice disease references and local photo preview. Season and growth stage change the illustrations, not a predicted disease probability.'],
  ['.disease-body h3','This is a reference illustration, not an analysed crop photo. Growth stage and reported conditions determine reference ordering.'],
  ['.photo-card h2','JPEG, PNG and WebP photos are previewed locally. The current export includes context and image metadata only, not image bytes or a diagnosis.'],
  ['.photo-method h2','The proposed classifier is ImageNet-pretrained EfficientNet-B0, to be fine-tuned on a small Tamil Nadu rice-image subset. Training is pending.'],
  ['#sources-section h2','Government rice statistics, district locations and NASA POWER weather are joined by location, crop year and season.'],
  ['#preprocessing-section h2','Imputation, scaling, category encoding and DAE are fitted on training data only. Validation and test rows reuse the fitted transforms.'],
  ['#models-section h2','Compare MLP and HistGradientBoostingRegressor on standard and DAE features. Accuracy and improvement must be measured after training.'],
  ['#output-section h2','The future predictor estimates yield in t/ha. Multiplying by supplied hectares produces tonnes. The worked example uses invented inputs and weights.'],
  ['.calculation-example h3','A hand-checkable, three-input toy network demonstrates the arithmetic. It is not the planned full-size MLP, DAE or a trained forecast.']
 ];
 const number=(v,d=2)=>Number(v).toLocaleString('en-IN',{maximumFractionDigits:d});
 function calculation(request={areaHa:12,illustrativeYieldTPerHa:4.2}){
  return `<section class="calculation-example" aria-label="Hypothetical yield calculation"><div class="calculation-top"><div><p class="eyebrow">WORKED EXAMPLE</p><h3>Hypothetical yield calculation</h3></div><span class="small-badge">INVENTED INPUTS & WEIGHTS</span></div><p>A simplified 3 → 2 → 1 neural network. This example does not use the selected district's weather or run the proposed trained model.</p><details><summary>Show the complete calculation</summary><div class="calculation-steps"><article><b>1. Example inputs and scaling</b><p>Use z = (input − training mean) ÷ training standard deviation. All values and training statistics below are hypothetical.</p><div class="table-scroll"><table><thead><tr><th>Feature</th><th>Input</th><th>Mean</th><th>Std.</th><th>Scaled z</th></tr></thead><tbody><tr><td>Temperature</td><td>28 °C</td><td>26 °C</td><td>4 °C</td><td>(28 − 26) / 4 = 0.5</td></tr><tr><td>Rainfall</td><td>900 mm</td><td>800 mm</td><td>200 mm</td><td>(900 − 800) / 200 = 0.5</td></tr><tr><td>Radiation</td><td>18 MJ/m²/day</td><td>20 MJ/m²/day</td><td>4 MJ/m²/day</td><td>(18 − 20) / 4 = −0.5</td></tr></tbody></table></div></article><article><b>2. Hidden-layer weighted sums</b><p>Example activation: ReLU(x) = max(0, x).</p><code>h₁ = ReLU(0.4 × 0.5 + 0.2 × 0.5 − 0.2 × (−0.5) + 0.1)<br>h₁ = ReLU(0.2 + 0.1 + 0.1 + 0.1) = 0.5<br><br>h₂ = ReLU(−0.2 × 0.5 + 0.6 × 0.5 + 0.2 × (−0.5) + 0.2)<br>h₂ = ReLU(−0.1 + 0.3 − 0.1 + 0.2) = 0.3</code></article><article><b>3. Output-layer yield</b><code>Yield = output bias + w₁ × h₁ + w₂ × h₂<br>Yield = 3.8 + 0.5 × 0.5 + 0.5 × 0.3<br>Yield = 3.8 + 0.25 + 0.15 = <strong>4.20 t/ha</strong></code><p>The values 3.8, 0.5 and 0.5 are invented output parameters, not agricultural rules. After training, parameters are learned from observed YIELD labels.</p></article><article><b>4. Production from yield and area</b><code>Example production = 4.20 t/ha × <span class="calc-area">${number(request.areaHa)}</span> ha = <span class="calc-example-tonnes">${number(4.2*request.areaHa)}</span> tonnes<br>Mass = production × 1,000 = <span class="calc-example-kg">${number(4200*request.areaHa,0)}</span> kg</code><p class="calc-current">Current dashboard assumption: ${number(request.illustrativeYieldTPerHa)} t/ha × ${number(request.areaHa)} ha = ${number(request.illustrativeYieldTPerHa*request.areaHa)} tonnes.</p></article></div><p class="calculation-limit">Actual planned MLP: 28 or 16 inputs → 64 → 32 → 1, with GELU activation. This toy uses 3 inputs and ReLU for simple arithmetic. The DAE route and category encoding are not demonstrated here. Neither the toy result nor the dashboard assumption is a trained prediction.</p></details></section>`;
 }
 root.CropHelp={calculation};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.CropHelp;
 if(typeof document==='undefined')return;
 const popup=document.createElement('div');popup.id='section-help';popup.className='section-help';popup.hidden=true;popup.setAttribute('role','dialog');popup.setAttribute('aria-label','Section explanation');
 popup.innerHTML='<button type="button" aria-label="Close explanation">×</button><p></p>';document.body.append(popup);
 let trigger=null;
 function close(restore=false){popup.hidden=true;if(trigger){trigger.setAttribute('aria-expanded','false');if(restore)trigger.focus();}trigger=null;}
 function open(button,text){if(trigger===button&&!popup.hidden){close();return;}close();trigger=button;button.setAttribute('aria-expanded','true');popup.querySelector('p').textContent=text;popup.hidden=false;const rect=button.getBoundingClientRect(),width=Math.min(320,innerWidth-24);popup.style.width=width+'px';popup.style.left=Math.max(12,Math.min(rect.left,innerWidth-width-12))+'px';const height=popup.getBoundingClientRect().height;popup.style.top=(rect.bottom+height+12<innerHeight?rect.bottom+10:Math.max(12,rect.top-height-10))+'px';}
 popup.querySelector('button').addEventListener('click',()=>close(true));
 document.addEventListener('keydown',event=>{if(event.key==='Escape')close(true);});
 document.addEventListener('pointerdown',event=>{if(!popup.hidden&&!popup.contains(event.target)&&event.target!==trigger)close();});
 window.addEventListener('resize',()=>close());window.addEventListener('hashchange',()=>close());window.addEventListener('scroll',()=>close(),{passive:true});
 function enhance(){for(const [selector,text] of explanations)document.querySelectorAll(selector).forEach(heading=>{if(heading.querySelector('.section-help-button'))return;const button=document.createElement('button');button.type='button';button.className='section-help-button';button.textContent='i';button.setAttribute('aria-label','About '+heading.textContent.trim());button.setAttribute('aria-expanded','false');button.setAttribute('aria-controls',popup.id);button.addEventListener('click',()=>open(button,text));heading.append(button);});}
 const output=document.getElementById('output-section');output.insertAdjacentHTML('beforeend',calculation());
 enhance();new MutationObserver(enhance).observe(document.getElementById('main'),{childList:true,subtree:true});
})(typeof window!=='undefined'?window:globalThis);
