const assert=require('node:assert/strict');
const fs=require('node:fs');const path=require('node:path');
const {advisories,imageCard,referencePhotos}=require('../prototype/health.js');
for(const card of advisories(null)){
 const html=imageCard(card,'Kharif','unknown');
 assert.ok(html.includes('class="flip-front"'));
 assert.ok(html.includes('class="flip-back"'));
 assert.ok(html.includes('aria-pressed="false"'));
 assert.ok(html.includes('Donald Groth'));
 assert.ok(html.includes('not local outbreak evidence'));
 const photo=referencePhotos[card.id];
 const bytes=fs.readFileSync(path.join(__dirname,'../prototype',photo.file));
 assert.equal(bytes[0],255);assert.equal(bytes[1],216);
 assert.ok(bytes.length>10000);
 assert.ok(photo.url.startsWith('https://commons.wikimedia.org/wiki/File:'));
}
assert.notEqual(imageCard(advisories(null)[0],'Kharif','unknown'),imageCard(advisories(null)[0],'Rabi','unknown'));
console.log('Three real reference photos, preserved season illustrations, credits and accessible flip controls: passed.');
