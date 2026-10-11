"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const source = fs.readFileSync(require.resolve("../static/app.js"), "utf8").replace(/bindEvents\(\);\s*loadInventory\(\);\s*navigate\(\);\s*$/, "");
const context = vm.createContext({TemplateFamilies: {models: {}}, CloneSubmissionGuard: class {}, DetailLoadGuard: class {}, DialogFocusManager: class {}, DialogOperationGuard: class {}, window: {EslDesigner: {create: () => ({})}}});
vm.runInContext(source, context);
function run(code) { return vm.runInContext(code, context); }
run(`state.mode = 'live_enabled'; state.publications = [{controller_id:'c', vendor_id:30, model_id:'m', bindings:{product:{field:'Name'},price:{field:'Price'},fixed:{field:'',static_value:'x'}}}];
state.templates = [{id:'local-12',vendor_id:30,controller_id:'c'}];
var tag = {id:'tag-1',mac:'MAC',controller_id:'c',device_model_id:'m',management_supported:true,staged:false};
var template = state.templates[0];`);
assert.equal(run("typeof templateApplyEligibility"), "function", "manual apply eligibility must exist");
assert.equal(run("templateApplyEligibility(tag, template).allowed"), true);
for (const mode of ['live', 'read_only', 'simulation', undefined]) {
 context.mode = mode; run("state.mode = mode"); assert.equal(run("templateApplyEligibility(tag, template).allowed"), false);
}
run("state.mode = 'live_enabled'");
assert.equal(run("templateApplyEligibility({...tag,staged:true},template).allowed"), false);
assert.equal(run("templateApplyEligibility({...tag,management_supported:false},template).allowed"), false);
assert.equal(run("templateApplyEligibility(tag,{...template,vendor_id:31}).allowed"), false);
assert.equal(run("templateApplyEligibility({...tag,device_model_id:'other'},template).allowed"), false);
assert.equal(run("templateApplyEligibility(tag,{...template,vendor_id:null}).allowed"), false);
run('state.publications.push({...state.publications[0],vendor_id:undefined})');
assert.equal(run("templateApplyEligibility(tag,{...template,vendor_id:undefined}).allowed"), false, 'missing native ID must fail closed');
context.realLoadInventory = run('loadInventory');
console.log('template apply eligibility: PASS');
assert.equal(run("typeof templateApplyValidation"), 'function', 'JSON/phrase guard must exist');
run("var pub = state.publications[0]");
assert.equal(run(`templateApplyValidation('{}', 'I CONFIRM LIVE ESL UPDATE', pub).valid`), false);
assert.equal(run(`templateApplyValidation('{"Name":"A","Price":0}', 'I CONFIRM LIVE ESL UPDATE', pub).valid`), true);
for (const json of ['[]', 'null', '{', '{"Name":"","Price":1}', '{"Name":"A","Price":null}']) {
 context.dataJSON = json;
 assert.equal(run("templateApplyValidation(dataJSON, 'I CONFIRM LIVE ESL UPDATE', pub).valid"), false);
}
assert.equal(run(`templateApplyValidation('{"Name":"A","Price":1}', ' I CONFIRM LIVE ESL UPDATE', pub).valid`), false);
assert.equal(run(`templateApplyOutcome({status:'success'}).verified`), false, 'HTTP/status alone never proves hardware success');
assert.equal(run(`templateApplyOutcome({verified:true,status:'success'}).verified`), true);
assert.equal(run(`templateApplyOutcome({verified:true,status:'updating'}).verified`), true);
assert.equal(run(`templateApplyOutcome({verified:true,status:'ready'}).verified`), false);
console.log('template apply data and outcomes: PASS');
assert.equal(run('typeof submitTemplateApply'), 'function', 'explicit manual submission must exist');
(async () => {
 const nodes = {};
 for (const id of ['template-apply-modal','tag-drawer','template-apply-submit','template-apply-data','template-apply-confirm','template-apply-state','controller-select','detail-id','detail-template','detail-model']) nodes[id] = {id,value:'',disabled:false,open:true, querySelectorAll:()=>[], classList:{toggle(){}}};
 nodes['detail-id'].value='tag-1'; nodes['detail-template'].value='local-12'; nodes['detail-model'].value='m';
 nodes['template-apply-data'].value='{"Name":"A","Price":0}'; nodes['template-apply-confirm'].value='I CONFIRM LIVE ESL UPDATE';
 context.nodes=nodes; context.Guard=require('../static/dialog-operation-guard.js');
 run(`byId = id => nodes[id]; dialogOperationGuard.generations = new Map(); dialogOperationGuard.busy = new Set();
 Object.setPrototypeOf(dialogOperationGuard, Guard.prototype); detailGuard.activeId='tag-1';
 applyContext = {tag,template,publication:pub,attempted:false}; state.detailTag=tag;
 var calls=[]; var refreshes=0; var resolveRequest;
 api = async (path, options) => {calls.push({path,options}); return new Promise(resolve=>{resolveRequest=resolve;});};
 loadInventory=async()=>{refreshes++;};`);
 const pending=run('submitTemplateApply({preventDefault(){}})');
 assert.equal(run('calls.length'),1);
 assert.equal(run('calls[0].path'),'/api/tags/tag-1/apply-template');
 const payload=JSON.parse(run('calls[0].options.body'));
 assert.deepEqual(payload,{template_id:'local-12',data:{Name:'A',Price:0},confirmation:'I CONFIRM LIVE ESL UPDATE'});
 assert.equal(run('dialogOperationGuard.canClose(byId("tag-drawer"))'),false);
 assert.equal(run('dialogOperationGuard.canClose(byId("template-apply-modal"))'),false);
 context.history={replaceState(_a,_b,hash){context.savedHash=hash;}};
 context.location={hash:'#templates'};
 run('navigate()');
 assert.equal(context.savedHash,'#tags','pending navigation preserves active view');
 assert.equal(run('state.activeView'),'tags');
 await run('submitTemplateApply({preventDefault(){}})');
 assert.equal(run('calls.length'),1,'no duplicate pending dispatch');
 run('resolveRequest({status:"success"})'); await pending;
 assert.match(nodes['template-apply-state'].textContent,/nie je overený/);
 assert.equal(nodes['template-apply-confirm'].value,'');
 assert.equal(run('refreshes'),1);
 nodes['template-apply-confirm'].value='I CONFIRM LIVE ESL UPDATE';
 await run('submitTemplateApply({preventDefault(){}})');
 assert.equal(run('calls.length'),1,'no retry after unknown outcome');
 for (const result of [{verified:true,status:'success'},{verified:true,status:'updating'},null]) {
  context.result=result;
  run(`applyContext={tag,template,publication:pub,attempted:false};
    api=async(path,options)=>{calls.push({path,options});if(result===null)throw new Error('Network lost');return result;};`);
  nodes['template-apply-confirm'].value='I CONFIRM LIVE ESL UPDATE';
  await run('submitTemplateApply({preventDefault(){}})');
  assert.equal(nodes['template-apply-confirm'].value,'');
  assert.match(nodes['template-apply-state'].textContent,result ? (result.status==='success' ? /úspešne aktualizovaná/ : /dokončenie ešte nie je potvrdené/) : /nie je overený/);
 }
 assert.equal(run('calls.length'),4,'one request per explicit action, including failed network');
 nodes['template-apply-confirm'].value='I CONFIRM LIVE ESL UPDATE';
 run('applyContext = {tag,template,publication:pub,attempted:false}; state.mode="read_only"');
 await run('submitTemplateApply({preventDefault(){}})'); assert.equal(run('calls.length'),4,'physical-disabled never sends');
 nodes['apply-tag-template']={disabled:false}; nodes['detail-model'].value='other';
 run('state.mode="live_enabled"; updateTemplateApplyButton()');
 assert.equal(nodes['apply-tag-template'].disabled,true,'mismatched edited model must disable entry action');
 nodes['detail-model'].value='m';
 run('updateTemplateApplyButton()'); assert.equal(nodes['apply-tag-template'].disabled,false);
 nodes['template-apply-modal'].querySelector=()=>({reset(){}});
 nodes['template-apply-modal'].close=()=>{nodes['template-apply-modal'].open=false;};
 run('focusManager.restore=()=>{}; dialogOperationGuard.begin(byId("template-apply-modal"))');
 assert.equal(run('closeTemplateApply()'),false,'cancel blocked pending');
 assert.equal(nodes['template-apply-confirm'].value,'I CONFIRM LIVE ESL UPDATE');
 run('dialogOperationGuard.invalidate(byId("template-apply-modal"))');
 assert.equal(run('closeTemplateApply()'),true);
 assert.equal(nodes['template-apply-confirm'].value,'','cancel clears confirmation');
 console.log('template apply single-target/pending/unknown/no-retry guards: PASS');
 class Node {
  constructor(tagName) {this.tagName=tagName.toUpperCase();this.children=[];this.events={};this.dataset={};this.classList={toggle(){},remove(){},add(){}};this.value='';this.open=false;}
  set id(value){this._id=value;nodes[value]=this;} get id(){return this._id;}
  append(...children){this.children.push(...children);} replaceChildren(...children){this.children=children;}
  setAttribute(){} addEventListener(name,handler){this.events[name]=handler;}
  showModal(){this.open=true;} focus(){}
  querySelectorAll(){return [];} close(){this.open=false;} querySelector(){return null;} reportValidity(){return true;}
 }
 nodes['tag-detail-form']=new Node('form');
 nodes['tag-test-data']=new Node('textarea');
 nodes['detail-template'].addEventListener=()=>{}; nodes['detail-model'].addEventListener=()=>{};
 context.document={createElement:tag=>new Node(tag),body:new Node('body'),querySelector:()=>new Node('span')};
 context.HTMLElement=Node;
 run('focusManager.remember=()=>{}; installTemplateApplyUI()');
 assert.equal(run('calls.length'),4,'building UI never calls physical endpoint');
 nodes['detail-template'].value='local-12'; nodes['detail-model'].value='m';
 nodes['tag-test-data'].value='{"Name":"edited now","Price":0}';
 run('state.detailTag={...tag,test_data:{Name:"stored",Price:2}}; openTemplateApply()');
 assert.equal(nodes['template-apply-modal'].open,true);
 assert.equal(nodes['template-apply-confirm'].value,'');
 assert.deepEqual(JSON.parse(nodes['template-apply-data'].value),{Name:'edited now',Price:0},'use current edited content rather than stale stored data, no samples');
 assert.equal(nodes['template-apply-submit'].disabled,true);
 nodes['template-apply-confirm'].value='I CONFIRM LIVE ESL UPDATE';
 run('updateTemplateApplySubmit()'); assert.equal(nodes['template-apply-submit'].disabled,false);
 run('closeTemplateApply()'); assert.equal(nodes['template-apply-confirm'].value,'');
 nodes['tag-test-data'].value='{}';
 run('state.detailTag={...tag,test_data:undefined}; openTemplateApply()');
 assert.equal(nodes['template-apply-data'].value,'{}','missing stored data stays empty');
 run('closeTemplateApply()');
 for (const id of ['mode-label','mode-title','mode-description','safety-banner','app-status','tags-state','templates-state','controllers-state']) nodes[id]=new Node('div');
 run(`renderControllerSelect=()=>{}; currentRenderer=()=>{}; calls=[];
 api=async(path,options)=>{calls.push({path,options});
 if(path==='/api/controllers')return {items:[{id:'c'}]};
 if(path==='/api/health')return {mode:'live_enabled'};
 if(path.startsWith('/api/template-publications'))return {items:[pub]};
 return {items:[]};};`);
 await run('realLoadInventory()');
 assert.equal(run('state.mode'),'live_enabled');
 assert.equal(run('state.publications.length'),1);
 assert.equal(run('calls.every(call=>!call.options || !call.options.method || call.options.method==="GET")'),true);
 assert.equal(run('calls.some(call=>call.path==="/api/template-publications?controller_id=c")'),true);
 console.log('template apply modal/storage/GET-refresh: PASS');
})().catch(error=>{console.error(error);process.exitCode=1;});
