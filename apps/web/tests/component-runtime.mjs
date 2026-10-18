import { readFile } from 'node:fs/promises';
import vm from 'node:vm';
import ts from 'typescript';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const sourceRoot = fileURLToPath(new URL('../src/', import.meta.url));

export async function loadComponent(relative, globals = {}) {
  const context = vm.createContext({ console, setTimeout, clearTimeout, URL, TextEncoder, TextDecoder, ...globals });
  const cache = new Map();
  const resolutions = new Map();
  async function load(file) {
    if (cache.has(file)) return cache.get(file);
    const source = await readFile(file, 'utf8');
    const { outputText } = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX } });
    const module = new vm.SourceTextModule(outputText, { context, identifier: file, initializeImportMeta: meta => { meta.env = {}; } });
    cache.set(file, module);
    const imports = new Map(); resolutions.set(file, imports);
    for (const { fileName: specifier } of ts.preProcessFile(outputText).importedFiles) {
      if (specifier.startsWith('@/') || specifier.startsWith('.')) {
        const base = specifier.startsWith('@/') ? path.join(sourceRoot, specifier.slice(2)) : path.resolve(path.dirname(file), specifier);
        let resolved;
        for (const extension of ['.tsx', '.ts']) {
          try { await readFile(base + extension); resolved = await load(base + extension); break; } catch (error) { if (error.code !== 'ENOENT') throw error; }
        }
        if (!resolved) throw new Error('Unresolved component: ' + specifier);
        imports.set(specifier, resolved);
      } else {
        if (!cache.has(specifier)) {
          const namespace = await import(specifier);
          cache.set(specifier, new vm.SyntheticModule(Object.keys(namespace), function () {
            for (const key of Object.keys(namespace)) this.setExport(key, namespace[key]);
          }, { context }));
        }
        imports.set(specifier, cache.get(specifier));
      }
    }
    return module;
  }
  const module = await load(path.join(sourceRoot, relative));
  await module.link((specifier, parent) => resolutions.get(parent.identifier).get(specifier));
  await module.evaluate();
  return module.namespace;
}
