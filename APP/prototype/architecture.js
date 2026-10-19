/* One model architecture at a time, shared by browser and desktop views. */
(function(root){
 'use strict';
 const step=(title,text)=>`<li><b>${title}</b><span>${text}</span></li>`;
 function markup(offline=false,configuration=null){
  const context=configuration?.model_kind==='contextual_mlp';
  const count=configuration?.architecture?.[0]||28, categories=count-21, dataset=configuration?.dataset;
  const yieldSteps=[
   ['Inputs','Map-selected district → season → average seasonal temperature → cultivation area. Prediction date is automatic; no year/month selector.'],
   ['Seasonal reference construction','Use local training-season references where available. Otherwise, use synthetic references from three nearest same-season/year training districts and a separately trained neighbour-augmented HistGradientBoostingRegressor. Donors never use validation/test years. Apply supplied weather and recompute dependent features.'],
   ['SimpleImputer → StandardScaler → OneHotEncoder',`Reuse training-only transforms: 21 numerical + ${categories} state/season indicators = ${count} standard inputs.`],
   [context?'Contextual Residual MLP regressor · neural network':'MLP regressor · neural network',`Weather branch: ${count} → Linear(64) → GELU → Dropout → Linear(32) → GELU → Linear(1). ${context?'Add a learned district-season embedding. '+(configuration?.use_year_trend===false?'Year trend is disabled in this selected candidate.':'Add a learned linear crop-year trend; extrapolation is unvalidated.') :''} AdamW + MSE; validation selects the checkpoint. This neural route is experimental, not the default.`],
   ['HistGradientBoostingRegressor · default',`Receives ${count} standard inputs. Selected as default by validation RMSE; predictions are not averaged with the neural model.`],
   ['Yield and derived outputs',`The default tree returns yield directly in t/ha. The separate neural comparison is converted back using training-target standard deviation and mean; it is not part of the default tree calculation. Yield × entered rice-planted hectares → tonnes; tonnes × 1,000 → kg; kg × optional price → gross value.`]
  ];
  const imageSteps=[
   ['Input · rice photograph','JPEG, PNG or WebP. Check dimensions, contrast, blur and lighting before inference.'],
   ['Image preprocessing','Correct orientation → RGB → bicubic resize shorter edge to 256 → centre crop 224 × 224 → divide pixels by 255 → ImageNet channel normalization.'],
   ['EfficientNet-B0 · convolutional neural network','ImageNet-initialized backbone extracts visual patterns. Fine-tuning adapts its final two backbone blocks and classification head. Global pooling → dropout → Linear(1280, 10) → ten output logits.'],
   ['Softmax → screening guard','Convert logits to model scores. Return the highest-scoring candidate, or mark the result uncertain when the score is below 65% or quality warnings occur. Scores are not calibrated diagnostic confidence.'],
   ['Output','Candidate disease / normal label, class scores and input-quality warnings. Open Show prediction flow on the output page for actual logits and calculations.']
  ];
  return `<div class="page-intro"><div><p class="eyebrow">MODEL ARCHITECTURE</p><h1>Architecture</h1><p class="intro-copy">Select a task to inspect its inputs, models and outputs.</p></div><span class="small-badge">${offline?'OFFLINE INFERENCE':'INTERFACE PREVIEW'}</span></div>
   <div class="architecture-tabs" role="tablist" aria-label="Prediction architecture">
    <button type="button" id="architecture-yield-tab" role="tab" aria-selected="true" aria-controls="architecture-yield-panel" data-architecture="yield">Yield Prediction</button>
    <button type="button" id="architecture-disease-tab" role="tab" aria-selected="false" aria-controls="architecture-disease-panel" tabindex="-1" data-architecture="disease">Disease Identification</button>
   </div>
   <section id="architecture-yield-panel" role="tabpanel" aria-labelledby="architecture-yield-tab" tabindex="0">
    <article class="architecture-lane"><h2>Yield Prediction</h2><ol>${yieldSteps.map(v=>step(...v)).join('')}</ol></article>
    <div class="architecture-contract"><b>Training and evaluation</b><p>${dataset?`${dataset.rows} measured source-derived records, through agricultural year ${dataset.last_agricultural_year}. Train ${dataset.split_rows.train} (2001–2020), validation ${dataset.split_rows.validation} (2021–2022), test ${dataset.split_rows.test} (2023–2024).`:'Chronological training, validation and held-out test partitions.'} The label is production divided by area, in tonnes/hectare; production and yield are never predictors. Fit preprocessing on training rows only.</p><p>Denoising Autoencoder (DAE) is a preserved older representation experiment, not the deployed preprocessing route. Current training uses standard scaling and category encoding.</p><p>Retrospective scores use complete seasonal weather. They do not establish current-season or farm-level forecasting accuracy. Image screening does not alter yield.</p></div>
   </section>
   <section id="architecture-disease-panel" role="tabpanel" aria-labelledby="architecture-disease-tab" tabindex="0" hidden>
    <article class="architecture-lane"><h2>Disease Identification</h2><ol>${imageSteps.map(v=>step(...v)).join('')}</ol></article>
    <div class="architecture-contract"><b>Training and supported scope</b><p>8,419 duplicate-filtered Paddy Doctor photographs: 5,905 training, 1,257 validation and 1,257 test. The validation-selected EfficientNet-B0 reached 85.04% test accuracy and 83.59% macro-F1. MobileNetV3-Small is the comparison model, not a second classifier combined with this output.</p><p>Ten supported conditions: bacterial leaf blight, bacterial leaf streak, bacterial panicle blight, blast, brown spot, dead heart, downy mildew, hispa, normal and tungro. These include disease, pest-symptom and normal labels—not ten separate diseases.</p><p>Bacterial leaf blight has the lowest held-out recall (67.21%). Data were collected near Tirunelveli, Tamil Nadu; performance across all South Indian farms is not established. Unsupported crops and conditions are not reliably rejected.</p><p>District, season and weather remain separate reference context; they are not classifier inputs. No disease-related yield loss is inferred. Scores are not calibrated diagnostic confidence. The previous four-class result is not a directly comparable accuracy benchmark.</p></div>
   </section>`;
 }
 function mount(container,offline=false,configuration=null){
  container.innerHTML=markup(offline,configuration);
  const buttons=Array.from(container.querySelectorAll('[data-architecture]'));
  function select(button,focus=false){
   buttons.forEach(tab=>{
    const active=tab===button;tab.setAttribute('aria-selected',String(active));tab.tabIndex=active?0:-1;
    container.querySelector('#'+tab.getAttribute('aria-controls')).hidden=!active;
   });
   if(focus)button.focus();
  }
  buttons.forEach((button,index)=>{
   button.addEventListener('click',()=>select(button));
   button.addEventListener('keydown',event=>{
    let next;if(event.key==='ArrowRight'||event.key==='ArrowLeft')next=1-index;
    else if(event.key==='Home')next=0;else if(event.key==='End')next=buttons.length-1;else return;
    event.preventDefault();select(buttons[next],true);
   });
  });
 }
 root.PaddyArchitecture={markup,mount};
 if(typeof module!=='undefined'&&module.exports)module.exports=root.PaddyArchitecture;
})(typeof window!=='undefined'?window:globalThis);
