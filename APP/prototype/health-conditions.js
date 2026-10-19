/* Educational views correspond exactly to the ten deployed classifier labels. */
(function(root){
 'use strict';
 const tnau='https://agritech.tnau.ac.in/';
 const dataset='https://www.kaggle.com/competitions/paddy-disease-classification/data';
 const conditions=[
  {id:'bacterial_panicle_blight',label:'Bacterial panicle blight',title:'Panicle blight',part:'Panicle / grain',position:'Grain head',texture:'rice-condition-bacterial_panicle_blight.png',healthyTexture:'plant',
   signs:'Discoloured spikelets and poorly filled grain. Blighted grain may show a pale base with a darker margin.',source:'https://www.lsuagcenter.com/topics/crops/rice/diseases/photos/bacterial-panicle-blight'},
  {id:'blast',label:'Rice blast',title:'Rice blast',part:'Leaf / neck',position:'Upper leaf',texture:'rice-leaf-blast.png',healthyTexture:'leaf',
   signs:'Spindle-shaped lesions with pale grey centres and brown margins. Blast can also affect nodes and the panicle neck.',source:tnau+'expert_system/paddy/cpdisblast.html'},
  {id:'bacterial_leaf_streak',label:'Bacterial leaf streak',title:'Leaf streak',part:'Leaf',position:'Upper blade',texture:'rice-leaf-bacterial_leaf_streak.png',healthyTexture:'leaf',
   signs:'Narrow translucent streaks run lengthwise between veins and can turn brown as affected tissue expands.',source:tnau+'crop_protection/rice_diseases/rice_8.html'},
  {id:'bacterial_blight',modelClass:'bacterial_leaf_blight',label:'Bacterial leaf blight',title:'Leaf blight',part:'Leaf',position:'Middle leaf',texture:'rice-leaf-bacterial_blight.png',healthyTexture:'leaf',
   signs:'Water-soaked, yellowing lesions extend from leaf tips or margins. Affected tissue can become pale and dry.',source:tnau+'org_farm/orgfarm_agridiseases.html'},
  {id:'brown_spot',label:'Brown spot',title:'Brown spot',part:'Leaf',position:'Lower leaf',texture:'rice-leaf-brown_spot.png',healthyTexture:'leaf',
   signs:'Small brown round-to-oval spots with lighter centres. Nearby lesions can merge into larger damaged areas.',source:tnau+'org_farm/orgfarm_prac_agri_paddy_diseases.html'},
  {id:'hispa',label:'Hispa damage',title:'Hispa damage',part:'Leaf / pest damage',position:'Leaf surface',texture:'rice-leaf-hispa.png',healthyTexture:'leaf',
   signs:'Whitish scraped streaks and translucent mines run along leaf veins. This is insect-feeding damage, not a separate fungal disease.',source:tnau+'expert_system/paddy/cppests_ricehispa.html'},
  {id:'downy_mildew',label:'Downy mildew',title:'Downy mildew',part:'Leaf / dataset class',position:'Affected foliage',texture:'rice-leaf-downy_mildew.png',healthyTexture:'leaf',
   signs:'This view illustrates pale, yellow-green affected tissue for the dataset class. Similar discolouration has many causes; compare the real example and seek expert confirmation.',source:'https://github.com/paddydoc/paddy-doctor-dataset/blob/main/dataset.md'},
  {id:'dead_heart',label:'Dead heart',title:'Dead heart',part:'Central shoot / pest symptom',position:'Central tiller',texture:'rice-condition-dead_heart.png',healthyTexture:'plant',
   signs:'The central growing shoot dries while surrounding tillers can remain green. Stem-borer feeding is one important cause.',source:tnau+'expert_system/paddy/cppests_SB.html'},
  {id:'tungro',label:'Tungro',title:'Tungro',part:'Whole plant',position:'Whole plant',texture:'rice-condition-tungro.png',healthyTexture:'plant',
   signs:'Stunting, reduced tillering and yellow-to-orange leaf discolouration can occur. A photograph alone cannot confirm a viral infection.',source:tnau+'crop_protection/rice_diseases/rice_4.html'},
  {id:'normal',label:'Normal rice',title:'Normal rice',part:'Comparison / no condition',position:'Healthy comparison',texture:'rice-leaf-healthy.png',healthyTexture:'leaf',
   signs:'A green comparison leaf without illustrated lesions. The normal model label does not rule out every crop problem.',source:dataset,noProgression:true}
 ];
 conditions.forEach(condition=>{
  condition.modelClass=condition.modelClass||condition.id;
  // Pixel bounds of the labelled photographic panels in the unaltered Figure 1.
  // CSS frames the appropriate panel; no generated or retouched symptoms.
  const regions={normal:[9,17,261,261],bacterial_leaf_streak:[294,17,261,261],
   bacterial_panicle_blight:[579,17,261,261],dead_heart:[294,326,261,261],
   downy_mildew:[579,326,261,261],hispa:[863,326,261,261],tungro:[1148,326,261,261]};
  if(regions[condition.id])condition.photo={
   file:'assets/references/rice-conditions-zhang-2026.webp',title:condition.label+' — published photographic reference',
   region:regions[condition.id],
   url:'https://doi.org/10.3389/fpls.2026.1935930',credit:'Zhang et al. (2026), Frontiers in Plant Science, Figure 1',
   license:'CC BY 4.0 · selected panel'};
 });
 root.PaddyConditions=conditions;
 if(typeof module!=='undefined'&&module.exports)module.exports=conditions;
})(typeof window!=='undefined'?window:globalThis);
