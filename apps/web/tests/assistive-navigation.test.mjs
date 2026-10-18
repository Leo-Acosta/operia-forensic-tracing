import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { JSDOM } from 'jsdom';
import { loadComponent } from './component-runtime.mjs';
const { ApplicationShell } = await loadComponent('components/layout/application-shell.tsx');
const { CasesWorkspace } = await loadComponent('components/cases/cases-workspace.tsx');
test('loading announcement remains outside busy content and main has its heading as accessible name', () => {
 const dom=new JSDOM(renderToStaticMarkup(React.createElement(ApplicationShell,{active:'cases',items:[{key:'cases',label:'Casos',section:'Operación',icon:()=>null}],sections:['Operación'],loading:true,onNavigate(){},onIdentity(){}},React.createElement('p',null,'Contenido sintético'))));
 try {
 const doc=dom.window.document, main=doc.querySelector('main');
 assert.equal(main.getAttribute('aria-busy'),'true');
 assert.equal(doc.getElementById(main.getAttribute('aria-labelledby')).textContent,'Casos');
 const status=doc.querySelector('[role=status]');
 assert.equal(status.closest('[aria-busy=true]'),null);
 assert.equal(status.textContent,'Actualizando datos…');
 assert.equal(status.getAttribute('aria-atomic'),'true');
 assert.equal(doc.querySelector('a').getAttribute('href'),'#'+main.id);
 } finally {dom.window.close();}
});
test('wide authorized case table is a named keyboard focus stop', () => {
 const dom=new JSDOM(renderToStaticMarkup(React.createElement(CasesWorkspace,{cases:[{id:1,case_code:'SYN-1',title:'Sintético',status:'abierto'}],selectedId:'',loading:false,authenticated:true,canCreate:false,onOpen(){},onCreate(){},onRefresh(){},onSignIn(){}})));
 try {const region=dom.window.document.querySelector('[role=region]'); assert.equal(region.tabIndex,0); assert.ok(region.getAttribute('aria-label')); assert.ok(region.querySelector('table caption'));} finally {dom.window.close();}
});
