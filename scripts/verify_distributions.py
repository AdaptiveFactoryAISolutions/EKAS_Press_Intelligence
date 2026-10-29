"""Verify independently built client and server wheel contents, without installs."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile


def verify_shared_client(sdk,server):
    name='ekas_historian_client/__init__.py'
    if sdk.read(name)!=server.read(name):raise ValueError('SDK and server contain different canonical client implementations')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);args=parser.parse_args()
    sdk=list(args.directory.glob('ekas_historian_client-*.whl'))
    server=list(args.directory.glob('ekas_press_intelligence_rca-*.whl'))
    if len(sdk)!=1 or len(server)!=1:raise SystemExit('Exactly one SDK and one server wheel required')
    with zipfile.ZipFile(sdk[0]) as archive:
        names=archive.namelist()
        if any(not (n=='ekas_historian_client/__init__.py' or '.dist-info/' in n) for n in names):raise SystemExit('SDK includes non-client implementation')
        metadata=archive.read(next(n for n in names if n.endswith('/METADATA'))).decode()
        dependencies=[line for line in metadata.splitlines() if line.startswith('Requires-Dist:')]
        if dependencies!=['Requires-Dist: httpx<1,>=0.27']:raise SystemExit('SDK dependency boundary changed')
    code="import sys;sys.path.insert(0,sys.argv[1]);import ekas_historian_client as c;assert '.whl/' in c.__file__;assert not any(n.startswith(('historiansim','ekas_press_intelligence')) for n in sys.modules)"
    subprocess.run([sys.executable,'-I','-c',code,str(sdk[0].resolve())],check=True)
    with zipfile.ZipFile(server[0]) as archive:
        names=set(archive.namelist())
        required={'ekas_press_intelligence/native_ui/'+f for f in ('index.html','app.js','app.css','setup.js','setup.css','report.js','report.css')}
        required.update({'ekas_press_intelligence/native/api.py','ekas_historian_client/__init__.py'})
        if not required.issubset(names):raise SystemExit('Server wheel is missing runtime assets')
        with zipfile.ZipFile(sdk[0]) as client_archive:verify_shared_client(client_archive,archive)
    result={'passed':True,'scope':'Wheel contents, standalone client dependency/import boundary; checkout-based server runtime qualification remains separate.',
            'wheels':[{'name':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in (sdk[0],server[0])]}
    print(json.dumps(result))


if __name__=='__main__':main()
