"""Reference PFD, derived from pinned native tags/loops; no scenario or cause catalog.

Coordinate plan (viewBox units): 2500x2250; physical flows x60..1540;
register x1630..2430. Tank: x740..1080/y500..1000, level650;
feed430 above level; steam800/coil800..900 below level; condensate900;
product1060 from bottom head. Master/slave y260 with separate measurement
and output corridors; level controller right600. CSTR uses feed bands420/560,
reactor650..1120, cooling return800/supply1060, product1240, controls200/680/900/1380.
Every exact native tag appears in a source-derived register; physical sensor
balloons use ISA transmitter names with explicit original PV-source mappings.
"""
from pathlib import Path
import sys
import textwrap
import json

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'vendor/HistorianSim/src'))
sys.path.insert(0,str(ROOT/'vendor/HistorianSim/.claude/skills/simulate/pfd-generator/scripts'))
from pid_lib import PID, esc, render
from historiansim.plants import get_plant
PLANT='exothermic_cstr'
REV='R6'


def note(d,x,y,text,size=11): d.txt(x,y,esc(text),size=size)
def sensor(d,x,y,tag):
    top,bot=tag.split('-'); d.bubble(x,y,top,bot)
def controller(d,x,y,tag):
    top,bot=tag.split('-'); d.bubble(x,y,top,bot,shared=True)


def tank(d):
    d.vessel(740,500,1080,1000,level=650)
    d.pipe('M 60,430 L 800,430 L 800,500',arrow=True)
    d.pipe('M 60,800 L 740,800',d.RUST,arrow=True)
    d.pipe('M 1010,900 L 1540,900',d.RUST,arrow=True)
    d.pipe('M 920,1000 L 920,1060 L 1540,1060',arrow=True)
    d.pipe('M 740,800 L 790,800 L 790,835 L 1010,835 L 1010,865 L 790,865 L 790,900 L 1010,900',d.RUST)
    d.agitator(920,500,760,tag='Agitator')
    d.equip_tag(910,970,'TK-101','Heated stirred hold tank')
    note(d,795,935,'E-101 submerged steam coil')
    note(d,60,382,'FROM UPSTREAM STORAGE / P-100')
    note(d,60,402,'15 m3/h | 25 degC | top entry')
    note(d,60,750,'FROM SHARED STEAM HEADER')
    note(d,60,770,'6 barg | saturated steam')
    note(d,1315,960,'TO CONDENSATE RETURN')
    note(d,1270,1130,'TO DOWNSTREAM RECOVERY')
    d.steam_trap(1210,900,tag='Condensate trap')
    for x,tag in [(140,'PI-201'),(220,'TI-201'),(500,'FT-201')]: sensor(d,x,800,tag)
    for x,tag in [(330,'FI-101'),(480,'TI-100')]: sensor(d,x,430,tag)
    sensor(d,1370,900,'TI-202')
    for x,tag in [(1300,'FI-102'),(1400,'TI-102'),(1500,'AI-101')]: sensor(d,x,1060,tag)
    d.lead(740,700,722,700); sensor(d,700,700,'TT-101')
    d.lead(1080,700,1098,700); sensor(d,1120,700,'LT-101')
    d.lead(1080,740,1158,740); sensor(d,1180,740,'LI-102')
    sensor(d,1440,160,'TI-901'); note(d,1370,207,'Ambient air')
    d.sig('M 700,678 L 700,282')
    d.sig('M 678,260 L 472,260')
    note(d,490,218,'CASCADE SP: FIC-201.SP = 30 x TIC-101.OP')
    d.sig('M 500,778 L 500,740 L 450,740 L 450,282')
    d.sig('M 428,260 L 300,260 L 300,768')
    d.sig('M 1142,700 L 1238,700')
    d.sig('M 1260,722 L 1260,980 L 1180,980 L 1180,1028')
    controller(d,700,260,'TIC-101'); controller(d,450,260,'FIC-201'); controller(d,1260,700,'LIC-101')
    d.cvalve(300,800,'TV-101',fail='FC*',actuator='above',tag_dy=62)
    d.cvalve(1180,1060,'LV-101',fail='FL*',actuator='above',tag_dy=62)
    note(d,780,330,'Master: AUTO / reverse action / 75 degC')
    note(d,60,320,'Slave: CAS / reverse action')
    note(d,60,340,'Steam mass flow')
    note(d,1320,740,'AUTO / direct / 2 m')
    notes=[
      'TT-101 = native TI-101 source of TIC-101.PV; FT-201 = native FI-201 source of FIC-201.PV.',
      'LT-101 = native LI-101 source of LIC-101.PV. LI-102 is independent indication, never a voting input.',
      'Valve .POS tags are measured stem feedback; controller .OP tags are demand, not the same observation.',
      'Steam trap, piping elevations and valve failure positions (*) are conceptual engineering assumptions.',
      'FC steam stops heat input; FL product avoids asserting an unmodelled automatic release on loss of air.',
    ]
    return notes


def cstr(d):
    d.vessel(760,650,1080,1120,level=780)
    d.add('<rect x="740" y="780" width="360" height="280" rx="16" fill="none" stroke="#2a7f8f" stroke-width="2.4"/>')
    d.pipe('M 60,420 L 1000,420 L 1000,650',arrow=True)
    d.pipe('M 60,560 L 820,560 L 820,650',arrow=True)
    d.pipe('M 1540,1060 L 1100,1060',d.CYAN,arrow=True)
    d.pipe('M 1100,800 L 1540,800',d.CYAN,arrow=True)
    d.pipe('M 920,1120 L 920,1240 L 1540,1240',arrow=True)
    d.agitator(920,650,980,tag='M-201')
    d.equip_tag(920,1090,'R-201','Jacketed exothermic reactor')
    note(d,60,340,'PROCESS WATER / P-202')
    note(d,60,360,'Acid dosed upstream')
    note(d,60,380,'7 m3/h | 30 degC')
    note(d,60,508,'PO FROM STORAGE / P-201')
    note(d,60,530,'2 m3/h | 20 degC')
    note(d,1335,745,'TO CW RETURN')
    note(d,1310,1010,'FROM COOLING TOWER')
    note(d,1355,1029,'29 degC | 2.5 bar dP')
    note(d,1270,1305,'TO PG PURIFICATION')
    for x,tag in [(550,'FT-202'),(680,'TI-102')]: sensor(d,x,420,tag)
    for x,tag in [(500,'FT-201'),(650,'TI-101')]: sensor(d,x,560,tag)
    sensor(d,1460,800,'TT-202')
    for x,tag in [(1380,'FI-301'),(1500,'TI-301')]: sensor(d,x,1060,tag)
    d.lead(1540,1060,1540,1150); d.lead(1540,1150,1522,1150); sensor(d,1500,1150,'PI-301')
    for x,tag in [(1300,'FI-203'),(1400,'TI-203'),(1500,'AI-201')]: sensor(d,x,1240,tag)
    d.lead(1080,860,1098,860); sensor(d,1120,860,'TT-201')
    d.lead(760,860,702,860); sensor(d,680,860,'TI-204')
    d.lead(1080,1020,1098,1020); sensor(d,1120,1020,'LT-201')
    d.lead(920,606,920,582); sensor(d,920,560,'JI-201')
    sensor(d,1440,160,'TI-901'); note(d,1370,207,'Ambient air')
    d.sig('M 500,538 L 500,222')
    d.sig('M 500,178 L 350,178 L 350,528')
    d.sig('M 550,398 L 650,398 L 650,300 L 1000,300 L 1000,222')
    d.sig('M 522,200 L 718,200')
    d.add('<rect x="718" y="178" width="94" height="44" fill="white" stroke="#343a46" stroke-width="1.4"/>')
    note(d,732,195,'FY ratio')
    note(d,735,212,'x 3.5')
    d.sig('M 812,200 L 978,200')
    note(d,680,255,'Remote SP = 3.5 x FIC-201.PV')
    d.sig('M 1000,178 L 1000,130 L 250,130 L 250,388')
    d.sig('M 1142,860 L 1180,860 L 1180,680 L 1238,680')
    d.sig('M 1260,702 L 1260,878')
    note(d,1285,770,'Cascade remote SP')
    d.sig('M 1460,822 L 1460,900 L 1282,900')
    d.sig('M 1238,900 L 1200,900 L 1200,1028')
    d.sig('M 1120,1042 L 1120,1380 L 1238,1380')
    d.sig('M 1260,1358 L 1260,1272 L 1180,1272')
    for x,y,tag in [(500,200,'FIC-201'),(1000,200,'FFC-202'),(1260,680,'TIC-201'),(1260,900,'TIC-202'),(1260,1380,'LIC-201')]: controller(d,x,y,tag)
    for x,y,tag,fail,act in [(250,420,'FV-202','FC*','above'),(350,560,'FV-201','FC*','above'),(1200,1060,'TV-202','FO*','above'),(1180,1240,'LV-201','FL*','below')]: d.cvalve(x,y,tag,fail=fail,actuator=act,tag_dy=62)
    note(d,60,470,'PO: AUTO / reverse action')
    note(d,815,350,'Water: CAS ratio / reverse action')
    note(d,1260,625,'Master: AUTO / reverse / 60 degC')
    note(d,1260,958,'Slave: CAS / direct / jacket temperature')
    note(d,1285,1400,'AUTO / direct / 1.8 m')
    return [
      'TT-201 = TI-201 source of TIC-201.PV; TT-202 = TI-202 source of TIC-202.PV, at jacket outlet.',
      'FT-201 = FI-201 source of FIC-201.PV; FT-202 = FI-202 source of FFC-202.PV.',
      'LT-201 = LI-201 source of LIC-201.PV; TI-204 is a separate thermowell, indication only.',
      'FY is a conceptual ratio computation, not an additional historian tag; exact ratio_to source is FI-201.',
      'Valve failures (*) are assumptions: feeds FC, cooling FO, product FL; no loss-of-air dynamics modelled.',
      'Upstream feed pumps are outside the unit; both feeds enter above liquid; product drains under head.',
    ]


def build():
    plant=get_plant(PLANT); tags=plant.tags(); loops=plant.loops()
    d=PID(2500,2250)
    d.title(plant.equipment+' / NATIVE REFERENCE PROCESS','Conceptual PFD | native tags and control topology | no event or cause information')
    notes=tank(d) if PLANT=='heated_stirred_tank' else cstr(d)
    # Complete source-derived instrument register, including every PV/SP/OP/MODE and calculation.
    note(d,1630,135,'COMPLETE NATIVE HISTORIAN TAG REGISTER',14)
    note(d,1630,160,f'{len(tags)} actual native tags; controller modes 0 MAN / 1 AUTO / 2 CAS',11)
    for i,t in enumerate(tags):
        y=205+i*45
        d.txt(1630,y,esc(t.name),size=11,weight='bold')
        desc=f'{t.description} [{t.units}]'
        for j,line in enumerate(textwrap.wrap(desc,width=64)):
            d.txt(1825,y+j*14,esc(line),size=10.5,fill=d.SUB)
    y=1540
    note(d,60,y,'NATIVE CONTROL CONTRACT / EXACT PARAMETER REGISTER',14)
    for loop in loops:
        y+=30
        line=f'{loop.name}: PV source {loop.pv_source}; MV {loop.mv_tag}; mode {loop.mode}; SP {loop.sp:.5g}; {loop.action}'
        note(d,60,y,line)
        if loop.cascade_to:
            y+=23; note(d,85,y,f'Output cascades to {loop.cascade_to}; remote-SP range is declared by the slave sp_limits.')
        if loop.ratio_to:
            y+=23; note(d,85,y,f'Ratio feedforward: {loop.ratio_to} x {loop.ratio:g}; mode CAS recomputes SP every scan.')
    y+=48; note(d,60,y,'DESIGN BASIS / MAPPING / ASSUMPTIONS',13)
    basis='TK-101: feed15 m3/h; bulk75 degC; level2 m; steam6 barg; native equilibrium computes required steam flow.' if PLANT=='heated_stirred_tank' else 'R-201: PO2 + water7 m3/h; bulk60 degC; level1.8 m; jacket design SP computed from native equilibrium.'
    y+=25; note(d,60,y,basis)
    for text in notes:
        y+=25; note(d,60,y,text,10.5)
    y+=30; note(d,60,y,'Conceptual only: relief, isolation, vents, drains, line numbers, insulation and equipment sizing omitted.',10.5)
    d.legend([('Process liquid',d.BLUE,False),('Steam / condensate' if PLANT=='heated_stirred_tank' else 'Cooling water',d.RUST if PLANT=='heated_stirred_tank' else d.CYAN,False),('DCS / instrument signal',d.SIG,True)],y=2170,gap=300)
    d.revision(REV+' | pinned upstream reference | generated from native contracts',y=2210)
    out=Path(__file__).resolve().parent
    svg=out/'PFD.svg'; d.save(svg)
    text=svg.read_text()
    assert all(t.name in text for t in tags)
    assert all(lp.name in text and lp.pv_source in text and lp.mv_tag in text for lp in loops)
    assert '<marker' not in text and '<use' not in text
    render(str(svg),str(out/'PFD.png'),width=3200)
    (out/'pfd_contract.json').write_text(json.dumps({'plant':PLANT,'tag_count':len(tags),'tags':[t.name for t in tags],'loops':[lp.model_dump(mode='json') for lp in loops],'revision':REV},indent=2))
    print(f'{PLANT}: {len(tags)} tags; {len(loops)} loops; rendered {svg.name} + PFD.png')

if __name__=='__main__': build()
