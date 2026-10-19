import pytest

from operia.forensic_engine.analysis import analyze
from operia.forensic_engine.canonical import canonical_bytes, sha256
from operia.forensic_engine.logical_files import pack_logical
from test_logical_files import IDS, ROWS, source
from test_manifest_sqlite import image


def examine(raw):
    rows = list(ROWS)
    rows[0] = (IDS[0], 'HomeDomain', 'Library/sample.JSON', 1, b'private')
    return analyze(source(pack_logical(image(rows=rows), [(IDS[0], raw)])))


def test_json_manual_oracle_types_escaping_null_context_and_no_time():
    raw = canonical_bytes({'a/b~c': [True, None, 2, 2.5, '2024-01-02T00:00:00Z'],
                           'empty': [], 'url': 'https://synthetic.invalid/no-fetch'})
    result = examine(raw)
    values = [a for a in result['artifacts'] if a['kind'] == 'logical_json_scalar']
    assert len(values) == 6 and not result['timeline']
    assert [a['normalized']['value'] for a in values[:5]] == [True, None, 2, 2.5, '2024-01-02T00:00:00Z']
    assert values[1]['normalized']['value_type'] == 'null'
    assert values[0]['locator'].endswith('/json/a~1b~0c/0')
    assert all(a['normalized']['file_sha256'] == sha256(raw) for a in values)
    assert all(a['normalized']['file_id'] == IDS[0] for a in values)
    assert canonical_bytes(result) == canonical_bytes(examine(raw))


@pytest.mark.parametrize('raw', [
    b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e999}',
    b'{"x":"\\ud800"}', b'{"x":"\\u0000"}', b'{} trailing', b'\xff',
    b'"scalar"', b'null', b'[' * 25 + b']' * 25,
    canonical_bytes({str(i): i for i in range(129)}),
    canonical_bytes({'x': 'v' * 2049}), canonical_bytes({'k' * 129: 1}),
    canonical_bytes([[] for _ in range(1024)]), b' ' * 65537,
], ids=['duplicate','nan','infinity','overflow','surrogate','control','trailing','encoding',
        'scalar-root','null-root','depth','value-count','string-size','key-size','nodes','bytes'])
def test_json_invalid_or_excessive_excludes_entire_content(raw):
    result = examine(raw)
    assert [a['kind'] for a in result['artifacts']] == ['logical_selection_provenance', 'logical_file_preservation']
    assert result['artifacts'][1]['normalized']['sha256'] == sha256(raw)
    assert any(e['locator'].endswith('/content') for e in result['coverage']['sources'][0]['excluded'])


def test_json_boundary_bom_and_equal_values_keep_positions():
    raw = b'\xef\xbb\xbf' + canonical_bytes(['equal', 'equal'] + list(range(126)))
    values = [a for a in examine(raw)['artifacts'] if a['kind'] == 'logical_json_scalar']
    assert len(values) == 128
    assert all(a['duplicate_of'] is None for a in values)
    assert len({a['normalized']['content_locator'] for a in values}) == 128


def test_json_empty_containers_have_no_invented_values():
    result = examine(b'{"a":[],"b":{}}')
    assert len(result['artifacts']) == 2
    exclusions = result['coverage']['sources'][0]['excluded']
    assert any(e['locator'].endswith('/json/a') for e in exclusions)
    assert any(e['locator'].endswith('/json/b') for e in exclusions)


def test_json_node_budget_is_enforced_independently_of_scalar_count():
    branch = 1
    for _ in range(8):
        branch = [branch]
    result = examine(canonical_bytes([branch] * 128))
    assert len(result['artifacts']) == 2
    assert any('1024 nodos' in e['reason'] for e in result['coverage']['sources'][0]['excluded'])


def test_json_exact_byte_limit_and_no_json_lines_or_key_controls():
    raw = b'{"ok":true}'
    values = [a for a in examine(raw + b' ' * (65536 - len(raw)))['artifacts']
              if a['kind'] == 'logical_json_scalar']
    assert len(values) == 1 and values[0]['normalized']['value'] is True
    for invalid in (b'{}\n{}', b'{"\\u007f":1}', b'{"\\u000a":1}'):
        assert len(examine(invalid)['artifacts']) == 2
