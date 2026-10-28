"""EKAS ORIGINAL: fail-closed Linux mount/user/PID/network isolation.

The evaluator owns truth. Only public rule code is mounted into the worker.
No site packages, repository tree, hidden config, environment or home mount is
needed by the standard-library diagnosis engine.
"""
import json
import shutil
import subprocess
from pathlib import Path


class IsolationUnavailable(RuntimeError):
    pass


def sandbox_command(code):
    bwrap = shutil.which('bwrap')
    if not bwrap:
        raise IsolationUnavailable('Linux Bubblewrap is required; diagnosis is disabled')
    root = Path(__file__).resolve().parent
    cmd = [bwrap, '--unshare-all', '--die-with-parent', '--new-session',
           '--clearenv', '--ro-bind', '/usr', '/usr']
    for directory in ('/lib', '/lib64'):
        if Path(directory).exists():
            cmd += ['--ro-bind', directory, directory]
    cmd += ['--proc', '/proc', '--dev', '/dev', '--tmpfs', '/tmp',
            '--dir', '/app', '--dir', '/app/ekas_press_intelligence',
            '--dir', '/app/ekas_press_intelligence/rca',
            '--dir', '/app/ekas_press_intelligence/observability']
    # Individual public files only; never mount simulator, vault, API or storage.
    for relative in ('domain.py', 'rca/engine.py', 'observability/model.py'):
        source = root / relative
        if source.exists():
            cmd += ['--ro-bind', str(source), '/app/ekas_press_intelligence/' + relative]
    cmd += ['--chdir', '/tmp', '/usr/bin/python3', '-I', '-c',
            "import sys;sys.path.insert(0,'/app');" + code]
    return cmd


def investigate_isolated(evidence, question=''):
    code = ("import json,sys;from ekas_press_intelligence.rca.engine import investigate;"
            "p=json.load(sys.stdin);print(json.dumps(investigate(p['evidence'],p['question']),allow_nan=False))")
    try:
        process = subprocess.run(sandbox_command(code),
                                 input=json.dumps({'evidence': evidence, 'question': question}, allow_nan=False),
                                 text=True, capture_output=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise IsolationUnavailable('Diagnostic worker failed closed') from exc
    if process.returncode:
        raise IsolationUnavailable('Diagnostic worker failed closed: ' + process.stderr[-1000:])
    return json.loads(process.stdout)
