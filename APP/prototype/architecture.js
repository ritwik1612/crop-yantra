/* One model architecture at a time, shared by browser and desktop views. */
(function(root){
 'use strict';
 const step=(title,text)=>`<li><b>${title}</b><span>${text}</span></li>`;
 function markup(offline=false,configuration=null){
  const context=configuration?.model_kind==='contextual_mlp';
  const yieldSteps=[
   ['Inputs','Select district, historical crop year, season and cultivation area.'],
   ['Historical feature lookup','Rice crop records + district coordinates + NASA POWER seasonal weather. No matching record → no prediction.'],
   ['SimpleImputer → StandardScaler → OneHotEncoder','Training medians fill missing numbers; numerical fields are standardized. State and season become indicators: 21 numerical + 7 indicators = 28 inputs.'],
   [context?'Contextual Residual MLP regressor · neural network':'MLP regressor · neural network',context?'Weather branch: 28 → Linear(64) → GELU → Dropout(0.5) → Linear(32) → GELU → Linear(1). Add a learned district-season embedding and a linear crop-year trend. Together: 30 input fields. Initialize regional offsets on training data, then jointly train with AdamW + MSE; validation selects the checkpoint.':'28 → Linear(64) → GELU → Dropout(0.2) → Linear(32) → GELU → Linear(1). Training uses AdamW and mean squared error; validation selects the epoch.'],
   ['HistGradientBoostingRegressor · comparison','An alternative trained tree model receives the same 28 inputs. Select the predictor in Yield studio; the two predictions are not averaged.'],
   ['Yield and derived outputs',`${context?'Normalized neural yield = weather branch + learned district offset + year-trend term. ':''}Neural output × training-target standard deviation + training-target mean → t/ha. Yield × entered hectares → tonnes; tonnes × 1,000 → kg; kg × optional price → gross value.`]
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
    <div class="architecture-contract"><b>How the model learns</b><p>1,485 training records (2001–2015), 245 validation records (2016–2017), 288 test records (2018–2019). The label is observed rice yield in tonnes/hectare; it is never a predictor. Preprocessing is fitted on training rows only.</p><p>The Denoising Autoencoder (DAE) is a separate representation experiment: 21 numerical inputs → 8 latent features + reconstruction error, plus 7 category indicators. It is not a required step in the standard MLP route.</p><p>Feature sensitivities explain model behaviour, not causation. Historical district estimates are not live farm forecasts. Image predictions do not alter yield.</p></div>
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
