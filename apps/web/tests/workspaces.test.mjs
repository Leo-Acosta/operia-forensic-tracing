import test from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { JSDOM } from 'jsdom';
import axe from 'axe-core';
import { loadComponent } from './component-runtime.mjs';
import { readFile } from 'node:fs/promises';

const { EvidenceWorkspace } = await loadComponent('components/evidence/evidence-workspace.tsx');
const { ReportRegister } = await loadComponent('components/reports/report-register.tsx');
const { FormField } = await loadComponent('components/forms/form-field.tsx');
const noop = () => {};
test('permission notice meets AA text contrast with its declared background', async () => {
  const css = await readFile(new URL('../src/design-system.css', import.meta.url), 'utf8');
  const block = css.match(/\.premium-permissions-note\s*\{([^}]+)/)[1];
  const color = block.match(/\bcolor:\s*(#[\da-f]{6})/i)[1];
  const background = block.match(/\bbackground:\s*(#[\da-f]{6})/i)[1];
  const luminance = hex => hex.slice(1).match(/../g).map(part => {
    const c = parseInt(part, 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }).reduce((sum, value, index) => sum + value * [0.2126, 0.7152, 0.0722][index], 0);
  const values = [luminance(color), luminance(background)].sort((a, b) => a - b);
  assert.ok((values[1] + 0.05) / (values[0] + 0.05) >= 4.5);
});
const evidence = [
  { id: 1, case_id: 7, description: 'Archivo sintético reservado', evidence_type: 'archivo', sha256_hash: 'abc123', integrity_status: 'pendiente' },
  { id: 2, case_id: 8, description: 'OTRO EXPEDIENTE', evidence_type: 'archivo', sha256_hash: 'private', integrity_status: 'pendiente' },
];
const evidenceProps = { items: evidence, caseId: 7, caseCode: 'SYN-7', loading: false, canVerify: false, canDownload: false, busy: false, upload: React.createElement('p', null, 'Acceso de consulta'), onVerify: noop, onDownload: noop };
function documentFor(component) {
  return new JSDOM(`<!doctype html><html lang="es"><head><title>Prueba de accesibilidad OPERIA</title></head><body><main><h1>Expediente sintético</h1>${renderToStaticMarkup(component)}</main></body></html>`, { runScripts: 'outside-only' });
}
async function audit(component) {
  const dom = documentFor(component);
  try {
    dom.window.HTMLCanvasElement.prototype.getContext = () => null;
    dom.window.eval(axe.source);
    const results = await dom.window.axe.run(dom.window.document, {
      runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'] },
      rules: { 'color-contrast': { enabled: false } },
    });
    assert.equal(results.violations.length, 0, JSON.stringify(results.violations.map(v => ({ id: v.id, nodes: v.nodes.map(n => n.html) }))));
  } finally { dom.window.close(); }
}
test('evidence workspace filters another case and denies export and verification for read-only access', () => {
  const dom = documentFor(React.createElement(EvidenceWorkspace, evidenceProps));
  assert.match(dom.window.document.body.textContent, /Archivo sintético reservado/);
  assert.doesNotMatch(dom.window.document.body.textContent, /OTRO EXPEDIENTE|private/);
  assert.ok([...dom.window.document.querySelectorAll('button')].every(b => b.disabled));
  assert.equal(dom.window.document.querySelectorAll('a[href]').length, 0);
  dom.window.close();
});
test('evidence errors are not presented as an empty successful inventory', () => {
  const dom = documentFor(React.createElement(EvidenceWorkspace, { ...evidenceProps, items: [], error: 'denied' }));
  assert.match(dom.window.document.querySelector('[role=alert]').textContent, /No se pudo consultar/);
  assert.doesNotMatch(dom.window.document.body.textContent, /Todavía no hay evidencia/);
  dom.window.close();
});
test('reports retain recorded versions and deny export without the case capability', () => {
  const dom = documentFor(React.createElement(ReportRegister, { reports: [{ id: 4, case_id: 7, title: 'Histórico', status: 'revisado', version: 'v3', review_score: 80 }, { id: 5, case_id: 8, title: 'AJENO', status: 'final', version: 1, review_score: 0 }], caseId: 7, canRead: true, canExport: false, busy: false, onPreview: noop, onDownload: noop }));
  assert.match(dom.window.document.body.textContent, /Versión v3/);
  assert.doesNotMatch(dom.window.document.body.textContent, /AJENO/);
  assert.equal(dom.window.document.querySelector('button[aria-label="Descargar PDF de informe 4"]').disabled, true);
  assert.equal(dom.window.document.querySelector('button[aria-label="Vista previa de informe 4"]').disabled, false);
  dom.window.close();
});
test('field labels, required state, hints and errors have stable programmatic associations', () => {
  const dom = documentFor(React.createElement(FormField, { label: 'Motivo', hint: 'Se conserva el original', error: 'Explicá el motivo' }, React.createElement('textarea', { required: true })));
  const control = dom.window.document.querySelector('textarea');
  assert.equal(dom.window.document.querySelector('label').htmlFor, control.id);
  assert.equal(control.getAttribute('aria-invalid'), 'true');
  for (const id of control.getAttribute('aria-describedby').split(' ')) assert.ok(dom.window.document.getElementById(id));
  dom.window.close();
});
test('axe: evidence workspace in consultation and loading states', async () => {
  await audit(React.createElement(EvidenceWorkspace, evidenceProps));
  await audit(React.createElement(EvidenceWorkspace, { ...evidenceProps, loading: true }));
});
test('axe: report register and labeled upload fields', async () => {
  await audit(React.createElement(ReportRegister, { reports: [{ id: 4, case_id: 7, title: 'Sintético', status: 'borrador', version: 1, review_score: 20 }], caseId: 7, canRead: true, canExport: false, busy: false, onPreview: noop, onDownload: noop }));
  await audit(React.createElement('form', { 'aria-label': 'Incorporar evidencia' }, React.createElement(FormField, { label: 'Archivo original', hint: 'Se calcula su hash' }, React.createElement('input', { type: 'file', required: true }))));
});
test('downloads use Bearer, no-store and refuse redirects', async () => {
  let received;
  const { fetchScopedDownload } = await loadComponent('lib/scoped-download.ts', { fetch: async (...args) => { received = args; return { ok: true, blob: async () => 'bytes' }; } });
  assert.equal(await fetchScopedDownload('/local', 'synthetic-token', () => true), 'bytes');
  assert.equal(received[1].headers.Authorization, 'Bearer synthetic-token');
  assert.equal(received[1].cache, 'no-store');
  assert.equal(received[1].redirect, 'error');
});
test('downloads discard old context before fetch, after headers and after body', async () => {
  let current = false, calls = 0, bodyCalls = 0;
  const { fetchScopedDownload } = await loadComponent('lib/scoped-download.ts', { fetch: async () => { calls++; current = false; return { ok: true, blob: async () => { bodyCalls++; return 'secret'; } }; } });
  assert.equal(await fetchScopedDownload('/local', 'token', () => current), null);
  assert.equal(calls, 0);
  current = true;
  assert.equal(await fetchScopedDownload('/local', 'token', () => current), null);
  assert.equal(bodyCalls, 0);
  const bodyRace = await loadComponent('lib/scoped-download.ts', { fetch: async () => ({ ok: true, blob: async () => { current = false; return 'old'; } }) });
  current = true;
  assert.equal(await bodyRace.fetchScopedDownload('/local', 'token', () => current), null);
});
