const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const file=path.join(__dirname,'../ui/editor-navigation.js');
assert.ok(fs.existsSync(file),'workspace navigation must preserve mounted editor DOM');
const {mount}=require(file);
const KEYS=['model','photo','parameters','delivery'];

class Element {
  constructor(document,attributes={}){this.document=document;this.attributes={...attributes};this.events=new Map();this.hidden=false;this.tabIndex=0;this.value='kept value';this.childNodes=[{geometry:[1,2,3],annotation:{points:[[12,34],[56,78]]}}];}
  getAttribute(name){return this.attributes[name]??null;}
  setAttribute(name,value){this.attributes[name]=String(value);}
  addEventListener(type,callback){if(!this.events.has(type))this.events.set(type,[]);this.events.get(type).push(callback);}
  focus(){this.document.activeElement=this;}
  emit(type,extra={}){const event={type,target:this,button:0,defaultPrevented:false,preventDefault(){this.defaultPrevented=true;},...extra};for(const callback of this.events.get(type)||[])callback(event);return event;}
  set innerHTML(value){throw Error('navigation must not replace DOM');}
  replaceChildren(){throw Error('navigation must not replace DOM');}
}
function fixture({hash='',stored=null,storageThrows=false}={}){
  const document={activeElement:null,events:[],addEventListener(type){this.events.push(type);}};
  const tabs=KEYS.map(key=>new Element(document,{'data-workspace-tab':key,id:`tab-${key}`,'aria-controls':`workspace-${key}`}));
  const panels=KEYS.map(key=>new Element(document,{'data-workspace-panel':key,id:`workspace-${key}`,role:'tabpanel','aria-labelledby':`tab-${key}`}));
  const link=new Element(document,{'data-workspace-link':'#photoEditor',href:'#photoEditor'});
  document.querySelectorAll=selector=>({'[data-workspace-tab]':tabs,'[data-workspace-panel]':panels,'[data-workspace-link]':[link]})[selector]||[];
  const events=new Map(),storageWrites=[],entries=[hash];let position=0;
  const window={location:{hash},addEventListener(type,callback){if(!events.has(type))events.set(type,[]);events.get(type).push(callback);},emit(type){for(const callback of events.get(type)||[])callback({type});},history:{pushState(state,title,url){entries.splice(position+1);entries.push(url);position++;window.location.hash=url;}}};
  window.back=()=>{if(position){position--;window.location.hash=entries[position];window.emit('popstate');window.emit('hashchange');}};
  window.forward=()=>{if(position<entries.length-1){position++;window.location.hash=entries[position];window.emit('popstate');window.emit('hashchange');}};
  if(storageThrows)Object.defineProperty(window,'localStorage',{get(){throw Error('storage blocked');}});
  else window.localStorage={getItem(){return stored;},setItem(key,value){storageWrites.push([key,value]);stored=value;}};
  const changes=[];const navigation=mount({document,window,onChange:change=>changes.push(change)});
  return {document,window,tabs,panels,link,changes,navigation,storageWrites,entries};
}

const f=fixture({hash:'#photo',stored:'parameters'});
assert.equal(f.navigation.activeKey,'photo','explicit hash wins over preference');
assert.equal(f.changes.length,1);
assert.deepEqual(f.panels.map(panel=>panel.hidden),[true,false,true,true]);
assert.deepEqual(f.tabs.map(tab=>tab.tabIndex),[-1,0,-1,-1]);
assert.deepEqual(f.tabs.map(tab=>tab.getAttribute('aria-selected')),['false','true','false','false']);
const identities=f.panels.map(panel=>panel.childNodes[0]),values=f.panels.map(panel=>panel.value);
f.navigation.activate('delivery');f.navigation.activate('model');f.navigation.activate('photo');
f.panels.forEach((panel,index)=>{assert.equal(panel.childNodes[0],identities[index]);assert.equal(panel.value,values[index]);assert.deepEqual(panel.childNodes[0].annotation.points,[[12,34],[56,78]]);});
const same={history:f.entries.length,changes:f.changes.length,writes:f.storageWrites.length};
f.navigation.activate('photo');
assert.deepEqual({history:f.entries.length,changes:f.changes.length,writes:f.storageWrites.length},same);
f.navigation.activate('photo',{focus:true});assert.equal(f.document.activeElement,f.tabs[1]);
const right=f.tabs[1].emit('keydown',{key:'ArrowRight'});
assert.equal(right.defaultPrevented,true);assert.equal(f.navigation.activeKey,'parameters');assert.equal(f.document.activeElement,f.tabs[2]);
f.tabs[2].emit('keydown',{key:'Home'});assert.equal(f.navigation.activeKey,'model');
f.tabs[0].emit('keydown',{key:'ArrowLeft'});assert.equal(f.navigation.activeKey,'delivery');
f.tabs[3].emit('keydown',{key:'Home'});f.tabs[0].emit('keydown',{key:'End'});assert.equal(f.navigation.activeKey,'delivery');
assert.equal(f.tabs[3].emit('keydown',{key:'ArrowLeft',altKey:true}).defaultPrevented,false);
assert.equal(f.tabs[3].emit('keydown',{key:'Backspace'}).defaultPrevented,false);
assert.equal(f.tabs[3].emit('keydown',{key:'toString'}).defaultPrevented,false,'only the four documented navigation keys are intercepted');
assert.ok(!f.document.events.includes('keydown'),'canvas and text editing retain their keyboard scope');

const aliases={startSection:'model',modelStudio:'model',photoEditor:'photo',axesSection:'parameters',parameterSection:'parameters',saveArea:'delivery',reviewSection:'delivery'};
for(const [hash,key] of Object.entries(aliases))assert.equal(fixture({hash:'#'+hash,stored:'photo'}).navigation.activeKey,key);
const unknown=fixture({hash:'#unrelated-anchor',stored:'photo'});assert.equal(unknown.navigation.activeKey,'photo');assert.equal(unknown.window.location.hash,'#unrelated-anchor');
unknown.navigation.activate('parameters');unknown.window.location.hash='#other';unknown.window.emit('hashchange');assert.equal(unknown.navigation.activeKey,'parameters');
const unknownCount=unknown.changes.length;assert.equal(unknown.navigation.activate('toString'),false);assert.equal(unknown.changes.length,unknownCount);
assert.equal(fixture({hash:'#toString',stored:'__proto__'}).navigation.activeKey,'model');
assert.equal(fixture({hash:'#%E0%A4%A',stored:'delivery'}).navigation.activeKey,'delivery');

const blocked=fixture({storageThrows:true});assert.equal(blocked.navigation.activeKey,'model');blocked.navigation.activate('photo');assert.equal(blocked.navigation.activeKey,'photo');
const initial=fixture({stored:'photo'});initial.navigation.activate('delivery');initial.window.back();assert.equal(initial.navigation.activeKey,'photo','back to the original empty hash restores its initial workspace');
initial.window.forward();assert.equal(initial.navigation.activeKey,'delivery');
initial.window.location.hash='#axesSection';initial.window.emit('hashchange');assert.equal(initial.navigation.activeKey,'parameters');
const count=initial.entries.length;initial.navigation.activate('model',{updateHistory:false});assert.equal(initial.entries.length,count);

const links=fixture();assert.equal(links.link.emit('click',{ctrlKey:true}).defaultPrevented,false);assert.equal(links.navigation.activeKey,'model');
assert.equal(links.link.emit('click').defaultPrevented,true);assert.equal(links.navigation.activeKey,'photo');assert.equal(links.document.activeElement,links.tabs[1]);
links.tabs[3].emit('click');assert.equal(links.navigation.activeKey,'delivery');assert.equal(links.window.location.hash,'#delivery');
const vm=require('node:vm'),browser=vm.createContext({});vm.runInContext(fs.readFileSync(file,'utf8'),browser);
assert.equal(typeof browser.AtlasEditorNavigation.mount,'function','browser global can load before receiving a DOM instance');
console.log('PASS workspace navigation: retained DOM/state, ARIA/roving focus, scoped keyboard, canonical/legacy hashes, history and unavailable storage');
