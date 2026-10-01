// Logic regression tests run the actual inline game in a small DOM/Canvas stub.
// Real rendering, touch layout and browser errors are checked separately in Chrome.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const html=readFileSync(new URL('../www/index.html',import.meta.url),'utf8');
const source=html.split('<script>')[1].split('</script>')[0];
const expose=`globalThis.game={G,SAVE,input,PLANES,THEMES,RULESET,start,reset,frame,pauseFlight,resumeFlight,showStart,gameOver,loadBest,persist,collect,touchdown,beginLanding,update,updateActivities,progressEvent,dailyMissions,dailyProgress,discoverIsland,makeIsland,ensureWorld,handleDelivery,trick,render,showSettings,showLogbook,applySettings,redeem,ghostKey,loadGhosts,
get state(){return state},set state(v){state=v},get mode(){return flightMode},set mode(v){flightMode=v},get plane(){return PL},get theme(){return TM},get height(){return H},get jetX(){return jetX},get seaY(){return seaY},get skyTop(){return skyTop},get resumeAt(){return resumeAt},get cacheSize(){return sceneryCache.size}};`;
function boot({width=852,height=393,saved,fetcher}={}){
  const elements=new Map(),windowEvents={},documentEvents={},storage=new Map();
  if(saved)storage.set('skyIslandsSave',JSON.stringify(saved));
  const gradient={addColorStop(){}};
  const drawing=new Proxy({}, {get(o,k){return o[k]??(k==='measureText'?()=>({width:100}):k.startsWith('create')?()=>gradient:()=>{});},set(o,k,v){o[k]=v;return true;}});
  class Element{
    constructor(id){this.id=id;this.listeners={};this.style={setProperty(){}};this.dataset={};this.value='';this.disabled=false;this.clientWidth=width;this.clientHeight=height;this.width=320;this.height=150;const classes=new Set();this.classList={add:(...v)=>v.forEach(x=>classes.add(x)),remove:(...v)=>v.forEach(x=>classes.delete(x)),contains:x=>classes.has(x),toggle:(x,on)=>{if(on??!classes.has(x))classes.add(x);else classes.delete(x);}};}
    getContext(){return drawing;}
    addEventListener(k,fn){(this.listeners[k]??=[]).push(fn);}
    dispatch(k,extra={}){const e={target:this,key:'',pointerId:1,preventDefault(){},...extra};for(const fn of this.listeners[k]||[])fn(e);return e;}
    set innerHTML(v){this.html=v;for(const match of v.matchAll(/id="([^"]+)"/g))elements.set(match[1],new Element(match[1]));}
    get innerHTML(){return this.html||'';}
    closest(){return null;}
    querySelectorAll(){return [];}
    setPointerCapture(){}
    focus(){}
    getBoundingClientRect(){return {height:0};}
  }
  const get=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
  const all=sel=>sel==='.rb'?['btnU','btnL','btnR'].map(get):[];
  const document={hidden:false,body:get('body'),documentElement:get('html'),getElementById:get,createElement:()=>new Element(''),querySelectorAll:all,addEventListener:(k,f)=>(documentEvents[k]??=[]).push(f)};
  let now=0,requests=[];
  const context={document,console,Math,Date,Set,Map,JSON,Number,Object,Array,String,RegExp,Promise,AbortController,Uint8Array,performance:{now:()=>now},getComputedStyle:()=>({paddingLeft:'0',paddingRight:'0',height:'0'}),location:{protocol:'http:',hostname:'localhost'},localStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v)},setTimeout:()=>0,clearTimeout(){},requestAnimationFrame(){},crypto:{randomUUID:()=> 'test-player-12345678'},fetch:async(...args)=>{requests.push(args);return fetcher?fetcher(...args):{ok:true,json:async()=>({ghosts:[]})};},innerWidth:width,innerHeight:height,matchMedia:()=>({matches:false}),addEventListener:(k,f)=>(windowEvents[k]??=[]).push(f)};
  context.window=context;
  vm.createContext(context);vm.runInContext(source.replace(/\}\)\(\);\s*$/,expose+'})();'),context);
  return {g:context.game,get,storage,requests,document,windowEvents,documentEvents,advance(ms){now+=ms;context.game.frame(now);},event(k,e={}){for(const fn of windowEvents[k]||[])fn(e);}};
}
const saved={bank:420,best:90,plane:'scarlet',theme:'sunset',planes:{bluebird:1,scarlet:1},themes:{emerald:1,sunset:1},pid:'existing-player-123',tutorial:true};
test('old saved games keep currency, equipment and defaults',()=>{const {g}=boot({saved});assert.equal(g.SAVE.bank,420);assert.equal(g.plane.id,'scarlet');assert.equal(g.SAVE.settings.sound,true);assert.equal(g.SAVE.pid,saved.pid);});
test('releasing one touch preserves the other held controls, including two fingers on one button',()=>{
  const b=boot({saved});b.g.start();const up=b.get('btnU'),right=b.get('btnR');up.dispatch('pointerdown',{pointerId:1});up.dispatch('pointerdown',{pointerId:3});right.dispatch('pointerdown',{pointerId:2});right.dispatch('pointerup',{pointerId:2});b.event('pointerup',{pointerId:2});assert.equal(b.g.input.up,true);assert.equal(b.g.input.right,false);up.dispatch('pointercancel',{pointerId:1});assert.equal(b.g.input.up,true);up.dispatch('lostpointercapture',{pointerId:3});assert.equal(b.g.input.up,false);
});
test('pause freezes flight and resumes only after countdown; backgrounding resets countdown',()=>{
  const b=boot({saved});b.g.start();b.advance(100);b.g.pauseFlight();const x=b.g.G.scroll,t=b.g.G.runT;b.advance(10000);assert.equal(b.g.G.scroll,x);assert.equal(b.g.G.runT,t);b.g.resumeFlight();b.advance(2000);assert.equal(b.g.state,'countdown');b.document.hidden=true;for(const f of b.documentEvents.visibilitychange)f();assert.equal(b.g.state,'paused');b.document.hidden=false;b.g.resumeFlight();b.advance(3001);assert.equal(b.g.state,'play');b.advance(20);assert.ok(b.g.G.scroll>x);
});
test('daily mode fixes aircraft and ignores saved invincibility without changing owned equipment',()=>{
  const b=boot({saved:{...saved,god:true}});b.g.mode='daily';b.g.start();assert.equal(b.g.plane.id,'bluebird');assert.equal(b.g.G.assisted,false);assert.equal(b.g.SAVE.plane,'scarlet');b.g.mode='free';b.g.start();assert.equal(b.g.plane.id,'scarlet');assert.equal(b.g.G.assisted,true);
});
test('course geometry and pickups agree across phone dimensions and viewport lookahead',()=>{
  const a=boot({width:852,height:393,saved}),b=boot({width:1024,height:768,saved});for(const t of [a,b]){t.g.mode='daily';t.g.start();}
  const world=t=>JSON.stringify(t.g.G.islands.slice(0,2).map(i=>({x:i.x,heights:i.heights,landmark:i.landmark,rings:i.rings})));
  assert.equal(a.g.height,b.g.height);assert.equal(a.g.jetX,b.g.jetX);assert.equal(world(a),world(b));assert.equal(JSON.stringify(a.g.G.pickups.slice(0,2)),JSON.stringify(b.g.G.pickups.slice(0,2)));
});
test('mission rewards are granted once, persist, and do not inflate competitive score',()=>{
  const {g}=boot({saved});g.start();const m=g.dailyMissions()[0],bank=g.SAVE.bank,score=g.G.gold;g.progressEvent(m.id,m.target);assert.equal(g.SAVE.bank,bank+m.reward);assert.equal(g.G.gold,score);g.progressEvent(m.id,m.target);assert.equal(g.SAVE.bank,bank+m.reward);g.loadBest();assert.equal(g.SAVE.daily.claimed[m.id],true);
});
test('tutorial is safe, teaches climb/fuel/landing, and does not grant mission currency',()=>{
  const {g}=boot({saved});g.mode='tutorial';g.start();const bank=g.SAVE.bank;g.input.up=true;for(let i=0;i<41;i++)g.updateActivities(1);assert.equal(g.G.tutorialStep,1);g.collect({got:false,type:{id:'fuel',name:'Fuel',color:'#fff',sub:'Fuel'},x:0,y:0});assert.equal(g.G.tutorialStep,2);const is=g.G.islands[0];g.G.land={is};g.touchdown();assert.equal(g.G.tutorialStep,3);assert.equal(g.SAVE.tutorial,true);assert.equal(g.SAVE.bank,bank);
});
test('discoveries record landmarks and landing twice cannot farm rewards',()=>{
  const {g}=boot({saved});g.start();const is=g.G.islands[0];is.landmark='lighthouse';g.discoverIsland(is);g.discoverIsland(is);assert.equal(g.G.found,1);assert.equal(g.SAVE.landmarks.lighthouse,true);g.G.land={is};g.touchdown();const score=g.G.gold;g.touchdown();assert.equal(g.G.gold,score);
});
test('deliveries pay only at the assigned next island, then load the next parcel',()=>{
  const {g}=boot({saved});g.start();g.G.islands=[g.makeIsland(500,5),g.makeIsland(1500,10),g.makeIsland(2500,20)];const [a,b,c]=g.G.islands;g.handleDelivery(a);assert.equal(g.G.parcel.toX,b.x);g.handleDelivery(a);assert.equal(g.G.deliveries,0);g.handleDelivery(b);assert.equal(g.G.deliveries,1);assert.equal(g.G.parcel.toX,c.x);
});
test('rings pay once, chain a combo, and missed rings break the chain',()=>{
  const {g}=boot({saved});g.start();const is=g.G.islands[0];is.rings=[{x:g.jetX,y:g.G.jetY,got:false,missed:false}];g.updateActivities(1);assert.equal(g.G.rings,1);g.updateActivities(1);assert.equal(g.G.rings,1);g.trick('Test',25);assert.equal(g.G.combo,2);is.rings.push({x:g.jetX-30,y:10,got:false,missed:false});g.updateActivities(1);assert.equal(g.G.combo,0);
});
test('finishing a daily race banks once and retains an offline personal ghost',()=>{
  const {g}=boot({saved});g.mode='daily';g.start();g.G.gold=123;g.G.runT=20;g.G.rec=[0,.4,20,.4];const bank=g.SAVE.bank;g.gameOver();g.gameOver();assert.equal(g.SAVE.bank,bank+123);assert.equal(g.SAVE.dailyBest[g.G.course],123);assert.equal(g.SAVE.ghosts[g.ghostKey()].score,123);
});
test('assisted flights cannot enter personal records or publish a ranked score',()=>{
  const b=boot({saved:{...saved,god:true}});b.g.start();b.g.G.gold=500;b.g.gameOver();assert.equal(b.g.SAVE.best,90);assert.equal(Object.keys(b.g.SAVE.ghosts).length,0);assert.equal(b.get('card').innerHTML.includes('id="lb"'),false);
});
test('render all five biomes and aircraft; cached scenery is bounded and menus open',()=>{
  const {g}=boot({saved});for(const theme of g.THEMES){g.SAVE.theme=theme.id;for(const plane of g.PLANES){g.SAVE.plane=plane.id;g.start();g.render();}}assert.ok(g.cacheSize<=48);g.showSettings();g.showLogbook();
});
test('180-second race ends automatically',()=>{
  const {g}=boot({saved});g.mode='daily';g.start();g.G.runT=179.995;g.update(1);assert.equal(g.state,'over');assert.equal(g.G.reason,'Race complete');
});
test('physics and ghost sampling are identical at 60 Hz and 120 Hz',()=>{
  const a=boot({saved}),b=boot({saved});for(const t of [a,b]){t.g.mode='daily';t.g.start();t.g.input.up=true;}
  for(let i=0;i<120;i++)a.advance(1000/60);
  for(let i=0;i<240;i++)b.advance(1000/120);
  assert.equal(a.g.G.scroll,b.g.G.scroll);assert.equal(a.g.G.jetY,b.g.G.jetY);assert.equal(JSON.stringify(a.g.G.rec),JSON.stringify(b.g.G.rec));assert.equal(a.g.G.rec.length,42);
});
test('late ghost response cannot replace the ghost for a restarted run',async()=>{
  const pending=[];
  const b=boot({saved,fetcher:()=>new Promise(resolve=>pending.push(resolve))});
  b.g.mode='daily';b.g.start();b.g.start();
  pending[0]({ok:true,json:async()=>({ghosts:[{track:[0,.4,20,.4],name:'Old race'}]})});
  for(let i=0;i<8;i++)await Promise.resolve();
  assert.equal(b.g.G.ghosts.length,0);
  pending[1]({ok:true,json:async()=>({ghosts:[{track:[0,.4,20,.4],name:'Current race'}]})});
  for(let i=0;i<8;i++)await Promise.resolve();
  assert.equal(b.g.G.ghosts[0].name,'Current race');
});
