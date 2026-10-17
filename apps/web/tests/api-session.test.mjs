import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import ts from 'typescript';

async function runtime(fetch) {
  const values = new Map([['operia_access_token', 'first-session']]);
  const events = [];
  const context = vm.createContext({ fetch, Event, Response,
    localStorage: { getItem: key => values.get(key) ?? null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key) },
    window: { dispatchEvent(event) { events.push(event.type); } } });
  const source = await readFile(new URL('../src/api.ts', import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 } });
  const module = new vm.SourceTextModule(outputText, { context, initializeImportMeta: meta => { meta.env = {}; } });
  await module.link(() => { throw new Error('Unexpected import'); });
  await module.evaluate();
  return { api: module.namespace, events, switchSession: () => values.set('operia_access_token', 'second-session') };
}

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('authorized response remains readable', async () => {
  const { api } = await runtime(async () => Response.json({ synthetic: true }));
  assert.equal((await api.apiGet('/cases')).synthetic, true);
});

test('late response from previous session is discarded', async () => {
  const response = deferred();
  const { api, switchSession } = await runtime(() => response.promise);
  const request = api.apiGet('/cases');
  switchSession(); response.resolve(Response.json({ private: 'previous-session' }));
  await assert.rejects(request, /cambio de sesión/);
});

test('session change while parsing a body is checked again', async () => {
  const body = deferred(), entered = deferred();
  const response = Response.json({});
  response.json = () => { entered.resolve(); return body.promise; };
  const { api, switchSession } = await runtime(async () => response);
  const request = api.apiGet('/cases');
  await entered.promise; switchSession(); body.resolve({ private: 'old-session' });
  await assert.rejects(request, /cambio de sesión/);
});

test('old unauthorized response cannot clear a new session', async () => {
  const body = deferred(), entered = deferred();
  const response = new Response('', { status: 401 });
  response.text = () => { entered.resolve(); return body.promise; };
  const { api, switchSession } = await runtime(async () => response);
  const request = api.apiGet('/cases');
  await entered.promise; switchSession(); body.resolve('Unauthorized');
  await assert.rejects(request, /cambio de sesión/);
  assert.equal(api.getAuthToken(), 'second-session');
});

test('current unauthorized response clears the session and notifies the interface', async () => {
  const { api, events } = await runtime(async () => new Response('Unauthorized', { status: 401 }));
  await assert.rejects(api.apiGet('/cases'), /Sesión requerida/);
  assert.equal(api.getAuthToken(), '');
  assert.deepEqual(events, ['operia:auth-changed']);
});
