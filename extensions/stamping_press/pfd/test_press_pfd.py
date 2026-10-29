"""Public drawing contract, not a physical or native-plant qualification gate."""
from dataclasses import asdict
import hashlib
import importlib.util
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('press_pfd_builder',HERE/'build_pfd.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_pfd_is_bound_to_current_actual_tags_loops_and_sources():
    contract=json.loads((HERE/'pfd_contract.json').read_text())
    assert contract['tags']==[asdict(t) for t in builder.plant_tags()]
    assert contract['loops']==[lp.model_dump(mode='json') for lp in builder.plant_loops()]
    for name,digest in contract['source_sha256'].items():
        assert hashlib.sha256((HERE.parent/name).read_bytes()).hexdigest()==digest, name
    assert builder.check_contract(HERE/'PFD.svg',contract)


def test_every_control_path_uses_actual_pairing_and_both_directional_legs():
    contract=json.loads((HERE/'pfd_contract.json').read_text())
    loops={loop['name']:loop for loop in contract['loops']}
    assert set(loops)=={path['loop'] for path in contract['control_pathways']}
    for path in contract['control_pathways']:
        actual=loops[path['loop']]
        assert path['pv_source']==actual['pv_source']
        assert path['mv']==actual['mv_tag']
        assert path['measurement_path'] in [p['path'] for p in contract['signal_paths']]
        assert path['output_path'] in [p['path'] for p in contract['signal_paths']]
    # Frozen drawings must preserve process-source pairing, not merely tag spelling.
    text=' '.join(ET.parse(HERE/'PFD.svg').getroot().itertext())
    assert 'DI-272 is the feed-complete latch, not an inspection status.' in text
    assert 'die <=80 degC' in text and 'die <75 degC' in text
    assert 'oil <=80' not in text
    assert 'SIC-271.SP = 0' in text and 'clutch' in text


def test_material_utility_destinations_and_public_render_are_present():
    contract=json.loads((HERE/'pfd_contract.json').read_text())
    paths={path['meaning']:path for path in contract['process_paths']}
    for meaning in ['coil input','decoiler to buffer','buffer to feeder','completed feed to die',
        'formed parts to delayed inspection','good product outlet','rejected product outlet','geometric trim outlet',
        'cooling water supply to die','heated cooling water return','electrical drive energy','electrical pump input',
        'filtered oil header to bearings','bearing return to reservoir','die guide film branch']:
        assert paths[meaning]['arrow'] is True
    with Image.open(HERE/'PFD.png') as image:
        assert image.width==3200 and image.height>2500
        assert image.convert('RGB').getextrema() != ((255,255),(255,255),(255,255))
    svg=(HERE/'PFD.svg').read_text()
    for forbidden in contract['excluded_public_signals']:
        assert forbidden not in svg


def test_no_process_lines_cross_in_their_interiors():
    """Unmarked process crossings are forbidden; endpoint junctions remain valid."""
    import re
    contract=json.loads((HERE/'pfd_contract.json').read_text())
    segments=[]
    for path in contract['process_paths']:
        points=[tuple(map(float,m)) for m in re.findall(r'[ML]\s*([-\d.]+),([-\d.]+)',path['path'])]
        segments.extend((a,b,path['meaning']) for a,b in zip(points,points[1:]))
    for a,b,name in segments:
        if a[0]!=b[0]:continue
        x=a[0];lo,hi=sorted((a[1],b[1]))
        for c,d,other in segments:
            if c[1]!=d[1]:continue
            y=c[1];left,right=sorted((c[0],d[0]))
            assert not (left<x<right and lo<y<hi),(name,other,(x,y))


def test_delayed_measured_inspection_and_acquisition_semantics():
    text=' '.join(ET.parse(HERE/'PFD.svg').getroot().itertext())
    assert 'COUNT-274' in text
    assert 'accepted + rejected + pending' in text
    assert 'MEASURED QI-271' in text and 'code 3' in text
    assert '16-bit' in text and '10 um' in text
    contract=json.loads((HERE/'pfd_contract.json').read_text())
    assert 'instruments.py' in contract['source_sha256']
    assert '../../patches/0007-native-event-instrument-acquisition.patch' in contract['source_sha256']


def test_builder_import_preserves_selected_runtime_and_search_path():
    import sys
    import historiansim
    before=list(sys.path)
    selected=historiansim.__file__
    spec=importlib.util.spec_from_file_location('press_pfd_isolation_probe',HERE/'build_pfd.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert sys.path==before
    assert historiansim.__file__==selected
