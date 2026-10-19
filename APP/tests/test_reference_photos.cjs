/* Run against source or the packaged site: node test_reference_photos.cjs <site> */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const site=path.resolve(process.argv[2]||path.join(__dirname,'../prototype'));
const conditions=require(path.join(site,'health-conditions.js'));
const legacy=require(path.join(site,'health.js')).referencePhotos;
assert.equal(conditions.length,10);
for(const condition of conditions){
 const photo=condition.photo||legacy[condition.id];
 assert.ok(photo,condition.id+' missing reference mapping');
 assert.ok(!photo.localOnly,condition.id+' still uses excluded competition data');
 assert.ok(!photo.file.includes('local-references'));
 const file=path.resolve(site,photo.file);
 assert.ok(file.startsWith(site+path.sep));
 assert.ok(fs.statSync(file).size>10000,condition.id+' missing/empty photo');
 assert.match(photo.url,/^https:\/\//);
 assert.ok(photo.license);
 if(photo.region){const [x,y,w,h]=photo.region;assert.ok(x>=0&&y>=0&&w>0&&h>0&&x+w<=1417&&y+h<=633);}
}
assert.ok(fs.existsSync(path.join(site,'assets/PHOTO_CREDITS.md')));
console.log('All 10 condition references exist, are attributed and do not use excluded local photos:',site);
