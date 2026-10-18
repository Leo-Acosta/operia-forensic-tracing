"""CPython AST adapter: parse only; never import, compile to bytecode or execute samples."""
import ast
import base64
import hashlib
import json
import sys
from operia.security.child_guard import require_containment

MAX_INPUT = 131072

def analyze(source):
    if len(source) > MAX_INPUT:
        raise ValueError('source_limit')
    text = source.decode('utf-8')
    tree = ast.parse(text, filename='sample.py', mode='exec')
    lines = text.splitlines(keepends=True)
    offsets, total = [], 0
    for line in lines:
        offsets.append(total)
        total += len(line.encode('utf-8'))
    observations = []
    for count, node in enumerate(ast.walk(tree)):
        if count > 10000:
            raise ValueError('node_limit')
        description = None
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            description = type(node).__name__ + ': ' + node.name
        elif isinstance(node, ast.Import):
            description = 'Import: ' + ', '.join(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            description = 'ImportFrom: ' + ('.' * node.level) + (node.module or '')
        if description:
            if len(observations) >= 200:
                raise ValueError('observation_limit')
            observations.append({'id': 'ast_' + str(len(observations)+1), 'member': 'sample.py',
                'offset': offsets[node.lineno-1] + node.col_offset, 'text': description[:4000]})
    return {'schema_version':'operia-static-report/1', 'sample_sha256':hashlib.sha256(source).hexdigest(),
        'provider':'cpython-ast','provider_version':sys.version.split()[0], 'provider_revision':'operia-ast-adapter/1',
        'operation':'static-observations','coverage':'partial' if observations else 'empty',
        'limitations':'Static Python syntax only. No execution, behavior, safety verdict or attribution. Import names do not establish network connections.',
        'observations':observations}

def main():
    require_containment()
    raw = sys.stdin.buffer.read(180001)
    if len(raw) > 180000:
        raise ValueError('input_limit')
    source = base64.b64decode(json.loads(raw)['source'], validate=True)
    result = analyze(source)
    sys.stdout.buffer.write(json.dumps(result, ensure_ascii=True, sort_keys=True).encode('utf-8'))

if __name__ == '__main__':
    main()
