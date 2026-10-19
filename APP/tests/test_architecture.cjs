const assert=require('node:assert/strict');
const {markup,mount}=require('../prototype/architecture.js');
const html=markup(true);
assert.match(html,/architecture-disease-panel[^>]+hidden/);
assert.match(html,/MLP regressor/);assert.match(html,/EfficientNet-B0/);
assert.match(html,/Linear\(1280, 10\)/);
assert.match(html,/85.04% test accuracy/);
assert.doesNotMatch(html,/not yet the deployed model|model has four classes/);
const panels=[{},{}],events=[{},{}];let prevented=false,focused=false;
const buttons=[0,1].map(i=>({attributes:{'aria-controls':`p${i}`},tabIndex:0,
 getAttribute(k){return this.attributes[k]},setAttribute(k,v){this.attributes[k]=v},
 addEventListener(k,v){events[i][k]=v},focus(){focused=true}}));
const container={innerHTML:'',querySelectorAll:()=>buttons,querySelector:s=>panels[Number(s.slice(-1))]};
mount(container,true);
events[1].click();assert.equal(panels[0].hidden,true);assert.equal(panels[1].hidden,false);
assert.equal(buttons[1].attributes['aria-selected'],'true');
events[1].keydown({key:'ArrowLeft',preventDefault(){prevented=true}});
assert.equal(panels[0].hidden,false);assert.equal(panels[1].hidden,true);
assert.ok(prevented&&focused);assert.equal(buttons[0].tabIndex,0);assert.equal(buttons[1].tabIndex,-1);
events[0].keydown({key:'End',preventDefault(){}});
assert.equal(panels[0].hidden,true);assert.equal(panels[1].hidden,false);
console.log('Exclusive architecture tabs, keyboard navigation and model details: passed.');
