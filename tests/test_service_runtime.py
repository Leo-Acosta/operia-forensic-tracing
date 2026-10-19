import base64
import hashlib
from importlib.metadata import Distribution
from pathlib import Path
import pytest

from operia.security.service_runtime import resolve_dependencies, dependency_payload


def distribution(tmp_path, name='demo', requires='', startup=False):
    site=tmp_path/'Lib/site-packages'; site.mkdir(parents=True,exist_ok=True)
    info=site/(name+'-1.0.dist-info'); info.mkdir()
    package=site/(name+'.pth' if startup else name+'.py'); package.write_bytes(b'# synthetic dependency\n')
    meta=info/'METADATA'; meta.write_text(f'Metadata-Version: 2.1\nName: {name}\nVersion: 1.0\n'+requires+'\n')
    record=[]
    for path in (package,meta):
        raw=path.read_bytes(); digest=base64.urlsafe_b64encode(hashlib.sha256(raw).digest()).decode().rstrip('=')
        record.append(f'{path.relative_to(site).as_posix()},sha256={digest},{len(raw)}')
    (info/'RECORD').write_text('\n'.join(record+[f'{info.name}/RECORD,,'])+'\n')
    return Distribution.at(info), package


def test_dependency_closure_resolves_extras_markers_and_rejects_missing(tmp_path):
    demo,_=distribution(tmp_path,requires='Requires-Dist: leaf>=1; extra == "audit"\n')
    leaf,_=distribution(tmp_path,'leaf')
    assert set(resolve_dependencies(['demo==1.0'],[demo,leaf]))=={'demo'}
    assert set(resolve_dependencies(['demo[audit]==1.0'],[demo,leaf]))=={'demo','leaf'}
    with pytest.raises(RuntimeError,match='missing_or_incompatible'):
        resolve_dependencies(['demo[audit]==1.0'],[demo])
    with pytest.raises(RuntimeError,match='not_pinned'):
        resolve_dependencies(['demo>=1'],[demo])
    with pytest.raises(RuntimeError,match='missing_or_incompatible'):
        resolve_dependencies(['demo==2.0'],[demo])


def test_record_tampering_and_startup_hook_are_rejected(tmp_path):
    demo,path=distribution(tmp_path)
    assert len(dependency_payload({'demo':demo}))==3
    path.write_bytes(b'changed')
    with pytest.raises(RuntimeError,match='hash_mismatch'):
        dependency_payload({'demo':demo})
    path.unlink()
    with pytest.raises(FileNotFoundError):
        dependency_payload({'demo':demo})
    hook,_=distribution(tmp_path,'hook',startup=True)
    with pytest.raises(RuntimeError,match='startup_or_link_rejected'):
        dependency_payload({'hook':hook})


def test_record_escape_and_hardlink_are_rejected(tmp_path):
    import os
    demo,path=distribution(tmp_path)
    record=Path(demo.locate_file('demo-1.0.dist-info/RECORD'))
    record.write_text(record.read_text()+'../../../../escape.py,,\n')
    with pytest.raises(RuntimeError,match='path_rejected'):
        dependency_payload({'demo':demo})
    leaf,path=distribution(tmp_path,'leaf')
    os.link(path,tmp_path/'linked.py')
    with pytest.raises(RuntimeError,match='startup_or_link_rejected'):
        dependency_payload({'leaf':leaf})
