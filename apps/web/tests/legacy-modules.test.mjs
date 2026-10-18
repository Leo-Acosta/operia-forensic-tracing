import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { JSDOM } from 'jsdom';
import axe from 'axe-core';
import { loadComponent } from './component-runtime.mjs';

const globals = { localStorage: { getItem: () => null, setItem() {}, removeItem() {} }, window: {}, fetch: () => { throw new Error('SSR must not make a network request'); } };
const { App } = await loadComponent('App.tsx', globals);
const views = ['dashboard', 'history', 'legalKnowledge', 'cybercrime', 'deepfakeMedia', 'blockchainForensics', 'iotForensics', 'externalTools', 'ai', 'aiSecurity', 'identity', 'settings', 'casePresentation', 'mind', 'mobileForensics', 'geoTrace', 'geoProximity', 'exports'];
for (const initialModule of views) {
  test('axe and accessible names: legacy module ' + initialModule, async () => {
    const html = renderToStaticMarkup(React.createElement(App, { initialModule }));
    const dom = new JSDOM('<!doctype html><html lang="es"><head><title>OPERIA</title></head><body>' + html + '</body></html>', { runScripts: 'outside-only' });
    try {
      dom.window.HTMLCanvasElement.prototype.getContext = () => null;
      dom.window.eval(axe.source);
      const results = await dom.window.axe.run(dom.window.document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] },
        rules: { 'color-contrast': { enabled: false } },
      });
      assert.equal(results.violations.length, 0, JSON.stringify(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))));
      for (const control of dom.window.document.querySelectorAll('input:not([type=hidden]),textarea,select')) {
        assert.ok(control.labels?.length || control.getAttribute('aria-label') || control.getAttribute('aria-labelledby'), 'unnamed control: ' + control.outerHTML.slice(0, 100));
      }
      assert.ok(dom.window.document.querySelector('[data-module]'), 'shared module surface missing');
    } finally { dom.window.close(); }
  });
}

test('late case result is rejected before its caller can publish it', async () => {
  const { guardCaseResult } = await loadComponent('lib/case-result.ts');
  let resolve;
  const pending = new Promise(done => { resolve = done; });
  let current = true, published = false;
  const task = guardCaseResult(pending, () => current).then(() => { published = true; });
  current = false;
  resolve({ synthetic: true });
  await assert.rejects(task, /cambio de expediente/);
  assert.equal(published, false);
  assert.equal(await guardCaseResult(7, () => true), 7);
});

test('mobile capabilities require both role permission and an explicit case grant', async () => {
  const { mobilePermissions } = await loadComponent('lib/mobile-permissions.ts');
  const noGrants = mobilePermissions(['*'], []);
  assert.ok(Object.values(noGrants).every(value => value === false));
  const reader = mobilePermissions(['evidence:read'], ['read', 'export']);
  assert.equal(reader.download, true);
  assert.equal(reader.acquire, false);
  assert.equal(reader.analyze, false);
  const acquisitionOnly = mobilePermissions(['evidence:write'], ['read', 'evidence']);
  assert.equal(acquisitionOnly.acquire, true);
  assert.equal(acquisitionOnly.review, false);
  assert.equal(acquisitionOnly.generateExport, false);
  const analyst = mobilePermissions(['evidence:write', 'evidence:read', 'reports:write', 'cases:write'], ['read', 'evidence', 'analysis', 'review', 'reports', 'export']);
  assert.ok(Object.values(analyst).every(value => value === true));
});

for (const [source, props] of [
  ['MobileForensics.tsx', { caseId: 7, caseCapabilities: [] }],
  ['LocalAiGateway.tsx', { caseId: 7, allowed: false, sessionKey: '' }],
  ['CaseAccessPanel.tsx', { caseId: 7, users: [] }],
]) {
  test('axe: full shared panel ' + source, async () => {
    const { default: Component } = await loadComponent(source, globals);
    const html = renderToStaticMarkup(React.createElement(Component, props));
    const dom = new JSDOM('<!doctype html><html lang="es"><head><title>OPERIA</title></head><body><main><h1>Expediente sintético</h1><h2>Datos del expediente</h2>' + html + '</main></body></html>', { runScripts: 'outside-only' });
    try {
      for (const details of dom.window.document.querySelectorAll('details')) details.open = true;
      dom.window.HTMLCanvasElement.prototype.getContext = () => null;
      dom.window.eval(axe.source);
      const results = await dom.window.axe.run(dom.window.document, {
        runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'best-practice'] },
        rules: { 'color-contrast': { enabled: false } },
      });
      assert.equal(results.violations.length, 0, JSON.stringify(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.target) }))));
    } finally { dom.window.close(); }
  });
}
