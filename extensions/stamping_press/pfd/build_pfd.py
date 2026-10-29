"""Source-bound conceptual P-27 PFD, using the bundled native diagram primitives.

Coordinate plan (3000 x 2800): process x60..1870/y140..1390; five
noncrossing loop strips y1500..2190; assumptions/energy notes below.
Exact native register x1950..2935/y160..2540. Metal runs y430/610/700;
coolant y850/930; oil y1100/1300/1340. No main process crossings.
The model has lumped fluid branches: pipe geometry is conceptual, not sizing.
No catalog, scenario, scheduler or scoring-key data are included in the public assets.
"""
from dataclasses import asdict
from pathlib import Path
import hashlib
import json
import re
import importlib.util
import textwrap
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
# Load drawing-only helpers by exact file. Never change the selected native
# runtime or Python search path: callers explicitly provide PYTHONPATH.
_pid_spec = importlib.util.spec_from_file_location(
    '_press_drawing_primitives',
    ROOT / 'vendor/HistorianSim/.claude/skills/simulate/pfd-generator/scripts/pid_lib.py')
_pid = importlib.util.module_from_spec(_pid_spec)
_pid_spec.loader.exec_module(_pid)
PID, esc, render = _pid.PID, _pid.esc, _pid.render
from extensions.stamping_press.tags import plant_tags
from extensions.stamping_press.loops import plant_loops, design_point

REV = 'R6'
OUT = Path(__file__).resolve().parent
METAL = '#3c5872'
OIL = '#9b6a24'
ENERGY = '#936049'
SEMANTICS = {
    'FI-275': 'Decoiler strip delivery speed', 'SI-272': 'Independent instantaneous flywheel speed',
    'ZI-272': 'Independent last completed feed pitch', 'ZI-274': 'Independent within-cycle shaft encoder travel',
    'ZI-276': 'Independent latched shaft-travel cross-check', 'CALC-TRAVEL-GAP': 'Measured latched shaft travel minus strip pitch',
    'ZI-275': 'Within-cycle independent strip progression', 'LI-272': 'Independent buffer inventory',
    'PI-273': 'Independent lube header pressure', 'TI-272': 'Lumped circulating oil temperature',
    'JI-271': 'Electrical drive power', 'WI-271': 'Completed-cycle peak forming force envelope',
    'WI-273': 'Instantaneous triangular die force', 'FI-271': 'Pump delivery flow',
    'DPI-271': 'Filter differential pressure', 'PI-271': 'Strip tension (native name; force units)',
    'FI-272': 'Die coolant flow', 'TI-273': 'Cooling-water supply temperature',
    'QI-271': 'Part dimension after 10 s transport', 'QI-272': 'Independent check of the same delayed part',
    'AI-271': 'Incoming strip strength ratio', 'AI-272': 'Incoming strip thickness',
    'EI-271': 'Drive/pump electrical supply voltage', 'FI-273': 'Die-guide lubricating-film branch flow',
    'DI-271': 'Permissive AND clutch engaged AND no stop', 'DI-272': 'Feed-complete latch; clears after stroke',
    'PHASE-271': 'Physical crank phase, 0 to 1 revolution', 'COUNT-271': 'Completed permitted strokes',
    'COUNT-272': 'Accepted measured deliveries', 'COUNT-273': 'Rejected measured deliveries',
    'COUNT-274': 'Pending transported-part inspections',
    'CALC-WORK': 'DCS work estimate from measured peak force',
    'CALC-SUPPLY': 'DCS copy of measured decoiler delivery',
    'CALC-CONSUMPTION': 'DCS pitch x mean speed x permissive estimate',
    'WI-272': 'Transverse forming-force difference', 'ZI-273': 'Independent mechanical lost-motion travel',
    'FI-274': 'Measured oil return/bypass branch flow', 'JI-272': 'Electrical pump input power',
}
LOOP_NAMES = {
    'SIC-271': ('Mean cycle speed', 'Press drive / mean flywheel speed', 'DRIVE-271'),
    'FDC-271': ('Last completed encoder pitch', 'Servo feeder drive / commanded pitch', 'FEED-271'),
    'LIC-271': ('Mean buffer inventory', 'Decoiler delivery / loose inventory control', 'DECOIL-271'),
    'PIC-272': ('Lube header pressure', 'Lubrication pump delivery', 'PUMP-272'),
    'TIC-271': ('Lumped die temperature', 'Coolant demand / heat removal', 'COOL-271'),
}


def txt(d, x, y, text, size=12, bold=False, color=None, anchor='start'):
    d.txt(x, y, esc(str(text)), size=size, weight='bold' if bold else 'normal',
          fill=color or d.INK, anchor=anchor)


def lines(d, x, y, text, width=110, size=12, step=19):
    for index, line in enumerate(textwrap.wrap(text, width=width)):
        txt(d, x, y + index * step, line, size)


def box(d, x, y, w, h, title, subtitle='', fill='#f6f8fa'):
    d.add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="5" fill="{fill}" stroke="{d.EQ}" stroke-width="1.6"/>')
    txt(d, x + w/2, y + 28, title, 15, True, anchor='middle')
    if subtitle:
        for index, line in enumerate(textwrap.wrap(subtitle, width=max(12, int(w/8)))):
            txt(d, x+w/2, y+51+index*18, line, 11.5, anchor='middle')


def build():
    tags, loops = plant_tags(), plant_loops()
    actual = {tag.name for tag in tags}
    _, commands, _, _ = design_point()
    d = PID(3000, 2800)
    symbols, signal_paths, process_paths = [], [], []

    def pipe(path, color=METAL, arrow=True, meaning=''):
        d.pipe(path, color, arrow=arrow)
        process_paths.append(dict(path=path, color=color, arrow=arrow, meaning=meaning))

    def signal(path, meaning):
        d.sig(path)
        signal_paths.append(dict(path=path, meaning=meaning))

    def sensor(x, y, name, radius=27):
        assert name in actual, name
        prefix, number = name.split('-', 1)
        d.bubble(x, y, prefix, number, r=radius)
        # Native PID splits two-line labels, so preserve exact searchable tag as metadata.
        d.add(f'<g data-native-tag="{esc(name)}"/>')
        symbols.append(dict(tag=name, x=x, y=y, radius=radius))

    d.title('P-27 / STAMPING CELL', 'Conceptual process flow and native control pathways | public process relationships only')
    txt(d, 60, 125, 'METAL, MOTION, UTILITIES AND INSPECTION', 16, True)
    txt(d, 60, 151, 'One permitted completed stroke consumes one feed token and produces one part; geometry is conceptual.', 12)

    # Equipment bodies precede all pipes and instrument balloons.
    d.add(f'<circle cx="160" cy="430" r="52" fill="#f3f6fa" stroke="{d.EQ}" stroke-width="2"/>')
    d.add(f'<circle cx="160" cy="430" r="22" fill="none" stroke="{d.EQ}" stroke-width="1.4"/>')
    txt(d, 160, 520, 'DC-27 / coil', 15, True, anchor='middle')
    box(d, 410, 350, 160, 180, 'BUFFER', 'Mean inventory / cycle drawdown')
    box(d, 720, 350, 220, 180, 'FD-27', 'Servo feed / completed pitch')
    box(d, 1110, 310, 300, 260, 'P-27 / DIE-27', 'Flywheel, clutch, forming die')
    # Interior ram is not another process line.
    d.add(f'<rect x="1205" y="420" width="110" height="25" fill="#dbe4eb" stroke="{d.EQ}"/>')
    d.add(f'<path d="M 1260,390 L 1260,420 M 1190,490 L 1330,490" fill="none" stroke="{d.EQ}" stroke-width="3"/>')
    box(d, 1480, 350, 220, 180, 'INSPECTION', 'Same part / 10 s transport delay')
    box(d, 100, 1050, 200, 160, 'LUBE-27', 'Lumped oil circuit / cooler to ambient')
    d.add(f'<circle cx="500" cy="1100" r="40" fill="#fffaf1" stroke="{d.EQ}" stroke-width="2"/>')
    txt(d, 500, 1170, 'PUMP-272', 13, True, anchor='middle')
    box(d, 760, 1060, 160, 80, 'FILTER', 'Hydraulic resistance')
    box(d, 1200, 1040, 210, 145, 'P-27 BEARINGS', 'Circulating header / dissipation')
    box(d, 1480, 1060, 240, 125, 'DIE-GUIDE FILM', 'Lumped branch / return')

    # Metal paths use separated output bands; no invented batch or event labels.
    pipe('M 60,430 L 108,430', meaning='coil input')
    pipe('M 212,430 L 410,430', meaning='decoiler to buffer')
    pipe('M 570,430 L 720,430', meaning='buffer to feeder')
    pipe('M 940,430 L 1110,430', meaning='completed feed to die')
    pipe('M 1410,430 L 1480,430', meaning='formed parts to delayed inspection')
    pipe('M 1700,430 L 1800,430', meaning='good product outlet')
    pipe('M 1700,470 L 1760,470 L 1760,610 L 1800,610', meaning='rejected product outlet')
    pipe('M 1410,520 L 1450,520 L 1450,700 L 1800,700', meaning='geometric trim outlet')
    txt(d, 1808, 434, 'GOOD PARTS', 11.5, True)
    txt(d, 1808, 614, 'REJECTED', 11.5, True)
    txt(d, 1808, 704, 'TRIM', 11.5, True)
    txt(d, 60, 270, 'COLD-ROLLED STRIP', 13, True)
    txt(d, 60, 292, '100 mm width / 1.2 mm thickness', 12)

    # Utility nozzles are dedicated corridors below the die; trim stays to their right.
    pipe('M 60,850 L 1260,850 L 1260,570', d.CYAN, meaning='cooling water supply to die')
    pipe('M 1320,570 L 1320,930 L 60,930', d.CYAN, meaning='heated cooling water return')
    txt(d, 60, 790, 'CW-27 / COOLING SUPPLY', 13, True)
    txt(d, 60, 812, '29 degC nominal; coolant demand removes die heat', 12)
    txt(d, 60, 970, 'CW RETURN / heat removed from die', 12)
    # Electrical shaft path explicitly separates input, storage and work.
    pipe('M 1060,190 L 1180,190 L 1180,310', ENERGY, meaning='electrical drive energy')
    txt(d, 750, 188, 'ELECTRICAL DRIVE INPUT', 13, True)
    txt(d, 1210, 250, 'Flywheel -> clutch -> die', 12)

    # Circulating oil arrangement: main return and measured bypass use separate bands.
    pipe('M 300,1100 L 460,1100', OIL, meaning='oil supply to pump')
    pipe('M 540,1100 L 760,1100', OIL, meaning='pump to filter')
    pipe('M 920,1100 L 1200,1100', OIL, meaning='filtered oil header to bearings')
    pipe('M 1300,1185 L 1300,1300 L 200,1300 L 200,1210', OIL, meaning='bearing return to reservoir')
    pipe('M 1050,1100 L 1050,1230 L 200,1230', OIL, meaning='measured return bypass branch')
    pipe('M 1080,1100 L 1080,1000 L 1600,1000 L 1600,1060', OIL, meaning='die guide film branch')
    pipe('M 1720,1130 L 1800,1130 L 1800,1340 L 200,1340 L 200,1300', OIL, meaning='film branch return manifold')
    txt(d, 330, 1275, 'Pump input + bearing dissipation heat the oil; lumped cooler rejects heat to ambient.', 11.5)
    txt(d, 65, 1400, 'Oil branches are lumped model relationships, not hydraulic pipe sizing or a resolved reservoir inventory.', 12)

    pipe('M 300,990 L 500,990 L 500,1060', ENERGY, meaning='electrical pump input')
    txt(d,60,1010,'PUMP ELECTRICAL INPUT',12,True)

    # Sensors and source references are added last, on their actual equipment/streams.
    for x, y, name in [(270,430,'FI-275'),(355,430,'PI-271'),(490,610,'LI-272'),
        (695,610,'ZI-276'),(780,610,'ZI-272'),(865,610,'ZI-273'),(950,610,'ZI-274'),(1035,610,'ZI-275'),
        (740,250,'AI-271'),(880,250,'AI-272'),(1530,270,'QI-271'),(1640,270,'QI-272'),
        (1050,190,'EI-271'),(1140,190,'JI-271'),(1170,650,'SI-272'),(1350,650,'WI-271'),
        (1170,740,'WI-273'),(1410,740,'WI-272'),(1510,850,'PHASE-271'),(1630,850,'DI-271'),
        (1035,740,'DI-272'),(700,850,'FI-272'),(400,850,'TI-273'),
        (650,1100,'FI-271'),(840,990,'DPI-271'),(980,1100,'PI-273'),(150,1180,'TI-272'),
        (1450,1000,'FI-273'),(800,1230,'FI-274'),(500,990,'JI-272')]:
        sensor(x,y,name)
    # Thin sensor connections have no flow arrow and do not imply extra material streams.
    for coords in [(490,583,490,530),(695,583,740,530),(780,583,780,530),(865,583,865,530),
                   (950,583,925,530),(1035,583,940,500),(1530,297,1530,350),
                   (1640,297,1640,350),(1170,623,1170,570),(1350,623,1350,570),
                   (1110,500,1100,500),(1100,500,1100,740),(1100,740,1143,740),(1410,713,1410,570),
                   (740,277,740,350),(880,277,880,350),(840,1017,840,1060),(500,1017,500,1060)]:
        d.lead(*coords)
    box(d,60,655,450,100,'P-27 INTERLOCK / CLUTCH','SIC-271.SP = 0: operator stop')
    signal('M 1008,740 L 510,740','DI-272 feed-complete latch to interlock')
    signal('M 510,690 L 1080,690 L 1080,550 L 1110,550','interlock enable to P-27 clutch/drive')
    txt(d, 650, 680, 'Completed / within-cycle feed travel', 11.5)
    txt(d, 1510, 905, 'Physical phase / run permissive', 11.5)
    txt(d, 900, 795, 'Feed-complete latch; no stroke without its material token', 11.5)
    txt(d, 720, 210, 'Incoming strip properties', 11.5)
    txt(d, 1500, 220, 'Delayed part / independent check', 11.5)
    txt(d, 700, 900, 'Coolant flow', 11, anchor='middle')
    txt(d, 330, 900, 'Supply temperature', 11)
    # Production ledgers are process records, not hidden scheduling/cause counters.
    for index,name in enumerate(['COUNT-271','COUNT-272','COUNT-273','COUNT-274']):
        x=1480+index*112
        sensor(x,750,name)
        txt(d,x,800,['Completed strokes','Accepted','Rejected','Pending'][index],11,anchor='middle')

    txt(d, 60, 1460, 'NATIVE FEEDBACK / OPERATOR CONTROL PATHWAYS', 16, True)
    txt(d, 60, 1485, 'Dashed arrows: measured PV -> controller -> final element. PV source is an internal physical signal, not another recorded tag.', 12)
    pathways=[]
    for index,loop in enumerate(loops):
        y=1550+index*145
        label, service, mv = LOOP_NAMES[loop.name]
        d.add(f'<rect x="60" y="{y-40}" width="1780" height="125" rx="4" fill="#fbfcfe" stroke="#dce3e8"/>')
        sensor(250,y,loop.name+'.PV',radius=34)
        txt(d, 80, y+61, f'Source {loop.pv_source} / {label}', 11.5)
        box(d, 500, y-27, 650, 78, loop.name+' / DCS', '', fill='#eef4f7')
        txt(d, 520, y+18, f'{loop.name}.SP   |   {loop.name}.OP   |   {loop.name}.MODE', 12)
        box(d, 1440, y-27, 360, 78, loop.mv_tag, '', fill='#fffaf2')
        txt(d, 1460, y+18, service, 11.5)
        signal(f'M 284,{y} L 500,{y}', f'{loop.name}: measured PV to controller')
        signal(f'M 1150,{y} L 1440,{y}', f'{loop.name}: controller to {loop.mv_tag}')
        txt(d, 1165, y-13, '0-100% demand', 11)
        txt(d, 505, y+75, f'{loop.action} action | SP {loop.sp:g} | design demand {100*commands[loop.mv_tag]:.2f}% | mode {loop.mode}', 11.5)
        pathways.append(dict(loop=loop.name,pv_tag=loop.name+'.PV',pv_source=loop.pv_source,mv=loop.mv_tag,
                             measurement_path=signal_paths[-2]['path'],output_path=signal_paths[-1]['path']))

    txt(d, 60, 2270, 'PERMISSIVES / STOP / RESTART / MATERIAL AND ENERGY NOTES', 16, True)
    notes=[
      'Run gate: lube pressure >=2 bar; buffer >=0.15 m; die <=80 degC; cycle work <=2500 J; pitch inside 50..150 mm.',
      'Restart hysteresis: pressure >2.5 bar; buffer >0.25 m; die <75 degC; work <2200 J; pitch inside 55..145 mm.',
      'DI-271 = gate enabled AND clutch engaged AND no operator stop. DI-272 is the feed-complete latch, not an inspection status.',
      'SIC-271.SP = 0 requests an operator stop; restoring the speed setpoint permits physical spinup and clutch reengagement.',
      'An open clutch preserves partial crank work and any feed token. The flywheel coasts; no production tag is forced to zero.',
      'Active feed holds its admitted shaft/strip plan through completion; travel coordinates reset at completed stroke, not a position jump.',
      'COUN T reconciliation: completed strokes = accepted + rejected + pending inspections; geometric trim is a separate material outlet.',
      'Drive electrical power -> efficiency -> motor torque -> flywheel storage / forming work / bearing, guide and other losses.',
      'Forming energy partitions to part energy and die heat. Oil rejects pump/bearing heat to ambient; water removes die heat.',
      'CALC-WORK, CALC-SUPPLY and CALC-CONSUMPTION use measured instruments and retain their measurement uncertainty.',
      'Design: 60 SPM, 100 mm pitch, 100 mm strip width, 1.2 mm thickness, density7850 kg/m3, 1000 J forming work/cycle.',
      'Exact 10 s delivery: classify each part from primary MEASURED QI-271 including gain/error/ADC; QI-272 is an independent check.',
      'Journal code 3 records delivery / cumulative inspected count. Pulse position/speed: 16-bit acquisition, no level/flow dynamics.',
      'Optical gauges: 10 um output increments, independent 50 um / 600 s thermal error; synthetic acquisition assumptions.',
      'Operator .SP/.OP/.MODE are separate records; 0 MAN / 1 AUTO / 2 CAS. No separate manual reset tag is modeled.',
      'Conceptual only: no safety certification, relief/isolating/drain devices, line numbers, wiring, equipment or pipe sizing.',
    ]
    for index,line in enumerate(notes):
        txt(d,60,2300+index*22,line.replace('COUN T','Counter'),12)
    d.legend([('Metal / parts',METAL,False),('Cooling water',d.CYAN,False),('Lumped circulating oil',OIL,False),
              ('Electrical / shaft energy',ENERGY,False),('Instrument / control signal',d.SIG,True)],x=60,y=2660,gap=330,size=11.5)
    txt(d,60,2700,'Circles: field/recorded observations. Rectangles: equipment and shared DCS controls. Internal MV names are actuator keys, not extra tags.',11.5)
    txt(d,60,2720,'Thin solid gray leads attach observations to physical sources; equipment geometry and line routes are conceptual.',11.5)
    d.revision(REV+' | conceptual native press | verify against current source contracts',y=2760)

    # Exact recorded-tag register, including the PV/SP/OP/MODE records.
    d.add('<path d="M 1910,120 L 1910,2730" fill="none" stroke="#cbd5df"/>')
    txt(d,1950,145,'EXACT NATIVE RECORDED-TAG REGISTER',16,True)
    txt(d,1950,172,'Units / range / signal meaning; no neighbouring-equipment tags',12)
    for index,tag in enumerate(tags):
        y=210+index*41
        txt(d,1950,y,tag.name,13,True)
        if tag.loop:
            label=LOOP_NAMES[tag.loop][0]
            description={'PV':label,'SP':'Operator/controller setpoint','OP':'Controller demand (not measured actuator position)',
                         'MODE':'Controller mode: 0 MAN / 1 AUTO / 2 CAS'}[tag.role]
        else: description=SEMANTICS[tag.name]
        txt(d,2170,y,f'{tag.units} | {tag.lo:g}..{tag.hi:g} | {description}',11.5)
        txt(d,2170,y+16,f'source={tag.source} | {tag.role} | node={tag.node} | {tag.instrument}'+(f' | loop={tag.loop}' if tag.loop else ''),10.5,color=d.SUB)
    txt(d,1950,2660,'Tag metadata comes directly from tags.py; calibration, lag, scan and quality follow the native measurement/export configuration.',11)
    txt(d,1950,2690,'Historian quality: 0 good / 1 uncertain / 2 bad. Process relationships do not identify a scheduled event or a diagnostic answer.',11)

    svg=OUT/'PFD.svg'
    d.save(svg)
    contract=dict(plant='stamping_press',revision=REV,tags=[asdict(tag) for tag in tags],
                  loops=[loop.model_dump(mode='json') for loop in loops],control_pathways=pathways,
                  sensor_symbols=symbols,signal_paths=signal_paths,process_paths=process_paths,
                  source_sha256={name:hashlib.sha256((OUT.parent/name).read_bytes()).hexdigest()
                                 for name in ['tags.py','loops.py','model.py','cycles.py','compiled_backend.py','cycle_kernel.cpp','description.py','instruments.py',
                                              '../../patches/0007-native-event-instrument-acquisition.patch',
                                              '../../patches/0008-native-digital-feedback-quantization.patch']},
                  assumptions=['Conceptual equipment and pipe geometry; no sizing or safety certification.',
                               'Oil branches show lumped model relationships; no resolved reservoir or piping inventory.',
                               'Native actuator keys are equipment labels, not additional historian tags.'],
                  excluded_public_signals=['CALC-MATERIAL-RESIDUAL','CALC-ENERGY-RESIDUAL'])
    (OUT/'pfd_contract.json').write_text(json.dumps(contract,indent=2)+'\n')
    check_contract(svg,contract)
    render(str(svg),str(OUT/'PFD.png'),width=3200)
    print(f'P-27 PFD {REV}: native tag/loop contract checked; rendered SVG and PNG')


def check_contract(svg,contract):
    root=ET.parse(svg).getroot()
    rendered=' '.join(root.itertext())
    assert all(tag['name'] in rendered for tag in contract['tags'])
    assert {s['tag'] for s in contract['sensor_symbols']} <= {t['name'] for t in contract['tags']}
    assert len(contract['control_pathways'])==len(contract['loops'])
    assert all(p['pv_tag']==p['loop']+'.PV' for p in contract['control_pathways'])
    assert not root.findall('.//{*}marker') and not root.findall('.//{*}use')
    assert all(float(e.attrib.get('font-size',10))>=8.5 for e in root.findall('.//{*}text'))
    expected=len(contract['signal_paths'])+sum(p['arrow'] for p in contract['process_paths'])
    assert len([e for e in root.findall('.//{*}polygon') if e.attrib.get('class')=='arrowhead'])==expected
    assert not re.search(r'RC-[A-Z][0-9]|ground_truth|answer.key|root.cause|[0-9]+ (causes|faults|episodes)',rendered,re.I)
    assert 'NOT FOR CONSTRUCTION' in rendered
    return True

if __name__=='__main__':
    build()
