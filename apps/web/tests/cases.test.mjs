import { test } from 'node:test';
import assert from 'node:assert/strict';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { loadComponent } from './component-runtime.mjs';
const model = await loadComponent('components/cases/case-list-model.ts');
const { CasesWorkspace } = await loadComponent('components/cases/cases-workspace.tsx');
const cases = [
  { id: 1, case_code: 'OP-10', title: 'Análisis sintético', description: 'Private fixture', incident_type: 'Phishing', status: 'abierto', updated_at: '2026-01-01T12:00:00Z' },
  { id: 2, case_code: 'OP-2', title: 'Caso reservado', description: 'Closed fixture', incident_type: 'Activos digitales', status: 'cerrado', updated_at: '2026-02-01T12:00:00Z' }
];
const props = { cases, selectedId: '', loading: false, authenticated: true, canCreate: false, onOpen() {}, onCreate() {}, onRefresh() {}, onSignIn() {} };

test('search supports accents, codes and incident types', () => {
  for (const query of ['analisis', 'OP-10', 'phish']) assert.deepEqual(Array.from(model.filterCases(cases, query, 'all', 'recent'), item => item.id), [1]);
  assert.equal(model.filterCases(cases, 'missing', 'all', 'recent').length, 0);
});
test('filtering and numeric sorting preserve the original array and records', () => {
  const before = JSON.stringify(cases);
  assert.deepEqual(Array.from(model.filterCases(cases, '', 'closed', 'recent'), item => item.id), [2]);
  assert.deepEqual(Array.from(model.filterCases(cases, '', 'open', 'recent'), item => item.id), [1]);
  assert.deepEqual(Array.from(model.filterCases(cases, '', 'all', 'code'), item => item.id), [2, 1]);
  assert.equal(JSON.stringify(cases), before);
});
test('invalid dates do not fabricate timestamps', () => {
  assert.equal(model.formatCaseDate('invalid'), 'Sin fecha registrada');
  assert.equal(model.formatCaseDate(undefined), 'Sin fecha registrada');
});
test('read-only users get disabled creation and semantic case tables', () => {
  const html = renderToStaticMarkup(React.createElement(CasesWorkspace, props));
  assert.match(html, /<button[^>]*disabled[^>]*>[^]*?Nuevo expediente/);
  assert.match(html, /<table[^]*?<caption[^]*?Expedientes autorizados/);
  assert.match(html, /aria-label="Abrir expediente OP-10"/);
});
test('unauthenticated views never expose stale case names or counts', () => {
  const html = renderToStaticMarkup(React.createElement(CasesWorkspace, { ...props, authenticated: false, canCreate: true }));
  assert.doesNotMatch(html, /OP-10|OP-2|Caso reservado|Private fixture/);
  assert.match(html, /0 de 0 expedientes disponibles/);
  assert.match(html, /<button[^>]*disabled[^>]*>[^]*?Nuevo expediente/);
});
test('loading and failure states are distinct from a legitimate empty result', () => {
  const loading = renderToStaticMarkup(React.createElement(CasesWorkspace, { ...props, cases: [], loading: true }));
  assert.match(loading, /role="status" aria-label="Cargando expedientes"/);
  const error = renderToStaticMarkup(React.createElement(CasesWorkspace, { ...props, cases: [], error: 'Synthetic network failure' }));
  assert.match(error, /No pudimos cargar tus expedientes/);
  assert.match(error, /Reintentar/);
});
