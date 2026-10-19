import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
import {buildRicePlant} from '../prototype/rice-scene.js';

const {plant,leaves,culms,heads,targets}=buildRicePlant();
assert.equal(culms.length,4);assert.equal(leaves.length,24);assert.equal(heads.length,4);
assert.equal(Object.keys(targets).length,8);
for(const [name,leaf] of Object.entries(targets))assert.ok(leaf,name+' has an attached target mesh');
for(const leaf of leaves){
 assert.ok(culms.includes(leaf.group.parent),'leaf attaches to a culm');
 const geometry=leaf.mesh.geometry;
 assert.ok(geometry.index.count>1000);assert.ok(geometry.getAttribute('normal'));
 assert.equal(leaf.material.opacity,1);assert.equal(leaf.material.transparent,false);
 for(const value of geometry.getAttribute('position').array)assert.ok(Number.isFinite(value));
}
let grains=0,meshes=0;
assert.ok(new Set(leaves.map(l=>Array.from(l.mesh.geometry.attributes.position.array).join(','))).size>12,'leaf shapes must vary');
assert.ok(leaves.every(l=>typeof l.condition==='string'),'every leaf has a comparison example');
assert.equal(new Set(leaves.map(l=>l.condition)).size,8,'distinct comparison symptom groups');
for(const [condition,leaf] of Object.entries(targets))assert.equal(leaf.condition,condition,'camera target matches its visible symptom');
plant.traverse(object=>{if(object.isMesh)meshes++;if(object.isInstancedMesh)grains+=object.count;assert.ok(!object.isSprite,'no photographic billboard');});
assert.equal(grains,672);
const model=plant.toJSON();assert.ok(!model.images,'geometry does not embed raster plant images');
if(process.argv.includes('--export')){
 await writeFile(new URL('../prototype/assets/rice-plant.model.json',import.meta.url),JSON.stringify(model));
}
console.log(`Rice model passed: ${culms.length} culms, ${leaves.length} attached leaf meshes, ${grains} instanced grains, ${meshes} total meshes; no image billboards.`);
