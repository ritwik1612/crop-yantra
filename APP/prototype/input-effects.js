/* Additive grouping of actual tree-path contributions, not causal attribution. */
(function(root){
 'use strict';
 function groupEffects(result){
  if(result.modelKind!=='gbdt'||!Number.isFinite(result.baseline))return null;
  const definitions=[['location','Location'],['season','Season'],['temperature','Temperature features'],['rainfall','Rainfall / water balance'],['humidity','Relative humidity'],['wind','Wind speed'],['radiation','Solar radiation'],['shared','Shared weather features'],['reference','Other saved references']];
  const groups=definitions.map(([id,label])=>({id,label,value:0,features:[]}));
  function category(name){
   if(name.startsWith('STATE_')||['CENTROID_X','CENTROID_Y'].includes(name))return 'location';
   if(name.startsWith('SEASON_'))return 'season';
   if(['TAVG_MEAN','TMIN_MEAN','TMAX_MEAN','TEMP_RANGE_MEAN','GDD_BASE10'].includes(name))return 'temperature';
   if(['PREC_TOTAL','WATER_BALANCE_PROXY'].includes(name))return 'rainfall';
   if(name==='RELH_MEAN')return 'humidity';if(name==='WSPD_MEAN')return 'wind';if(name==='RAD_TOTAL')return 'radiation';
   if(['VPRES_MEAN','RAIN_PER_GDD','RADIATION_PER_GDD'].includes(name))return 'shared';return 'reference';
  }
  for(const row of result.contributions){if(!Number.isFinite(row.contribution))throw Error('Invalid model contribution');const group=groups.find(g=>g.id===category(row.feature));group.value+=row.contribution;group.features.push(row);}
  const sum=groups.reduce((total,g)=>total+g.value,0);
  if(Math.abs(result.baseline+sum-result.yieldTPerHa)>1e-6)throw Error('Contribution decomposition does not match model output');
  return {baseline:result.baseline,sum,prediction:result.yieldTPerHa,groups};
 }
 root.PaddyInputEffects={groupEffects};if(typeof module!=='undefined'&&module.exports)module.exports=root.PaddyInputEffects;
})(typeof window==='undefined'?globalThis:window);
