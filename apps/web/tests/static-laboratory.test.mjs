import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import {renderToStaticMarkup} from 'react-dom/server';
import {JSDOM} from 'jsdom';
import axe from 'axe-core';
import {loadComponent} from './component-runtime.mjs';
const {LaboratoryView,labPermissions}=await loadComponent('components/static-lab/static-laboratory.tsx',{localStorage:{getItem:()=>''},window:{}});
const job={id:1,case_id:1,evidence_id:1,state:'completed',runtime_identity:'fixture-runtime',error_code:'',result_sha256:'a'.repeat(64)};
const detail={...job,report:{provider:'cpython-ast',provider_version:'3.12 fixture',limitations:'Static syntax only; synthetic accessibility fixture',observations:[{id:'o1',member:'sample.py',offset:0,text:'<img src=x onerror=alert(1)> displayed as text'}]},reviews:[{version:1,decision:'accepted',rationale:'Synthetic professional review for UI testing',actor_id:1,result_sha256:'a'.repeat(64)}],events:[{state:'completed',reason:'',recorded_at:'2026-10-18'}]};
const data={evidence:[{id:1,description:'Synthetic source',sha256_hash:'b'.repeat(64)}],jobs:[job],provider:{execution_enabled:true,providers:[{id:'cpython-ast',scope:'Python source',ready:true}]},detail,projections:[{id:1,report_id:1,finding_id:1,snapshot_sha256:'c'.repeat(64)}]};
const handlers=Object.fromEntries(['onEvidence','onRationale','onDecision','onSelect','onLoad','onQueue','onCancel','onReview','onProject','onReports','onClear'].map(key=>[key,()=>{}]));
for(const [name,role,caps] of [['authorized',['*'],['read','analysis','evidence','review','reports']],['reader',['evidence:read'],['read']],['no-grant',['*'],[]]]){
 test('laboratory accessible and permission-aware: '+name,async()=>{
 const rights=labPermissions(role,caps);
 const markup=renderToStaticMarkup(React.createElement(LaboratoryView,{...handlers,data:rights.read?data:{evidence:[],jobs:[],provider:null,detail:null,projections:[]},rights,busy:false,message:'',error:'',evidenceId:'1',rationale:'Synthetic rationale',decision:'accepted',selected:['o1'],contextLabel:'SYN-1 · Synthetic authorized case'}));
 const dom=new JSDOM('<!doctype html><html lang="es"><head><title>OPERIA</title></head><body><main><h1>Laboratorio</h1>'+markup+'</main></body></html>',{runScripts:'outside-only'});
 try{
 dom.window.HTMLCanvasElement.prototype.getContext=()=>null;dom.window.eval(axe.source);
 const results=await dom.window.axe.run(dom.window.document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa','best-practice']},rules:{'color-contrast':{enabled:false}}});
 assert.equal(results.violations.length,0,JSON.stringify(results.violations.map(x=>({id:x.id,nodes:x.nodes.map(n=>n.target)}))));
 assert.equal(dom.window.document.querySelectorAll('img').length,0);
 if(name==='reader'){
 const buttons=[...dom.window.document.querySelectorAll('button')].filter(b=>/Encolar|Guardar nueva|Incorporar selección/.test(b.textContent));assert.ok(buttons.every(b=>b.matches(':disabled')));
 }
 if(name==='no-grant')assert.doesNotMatch(markup,/Trabajo #1|Synthetic source|img src/);
 }finally{dom.window.close();}
 });
}
test('case grants remain an upper bound even for privileged roles',()=>{
 assert.ok(Object.values(labPermissions(['*'],[])).every(value=>value===false));
 assert.equal(labPermissions(['evidence:write','cases:write','reports:write'],['analysis','evidence']).project,false);
});
