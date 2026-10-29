from pathlib import Path
import ast
import numpy as np


def test_native_duration_never_exceeds_real_short_slot(tmp_path):
    import importlib.util
    root=Path(__file__).resolve().parents[1]
    source=root/'vendor/HistorianSim/src/historiansim/faults/scheduler.py'
    target=tmp_path/'runtime';dest=target/'src/historiansim/faults/scheduler.py'
    dest.parent.mkdir(parents=True);dest.write_bytes(source.read_bytes())
    patch=root/'patches/0011-native-short-campaign-duration.patch'
    if patch.exists():
        spec=importlib.util.spec_from_file_location('prepare_line_test',root/'scripts/prepare_native_runtime.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.apply_runtime_patch(target,patch)
    tree=ast.parse(dest.read_text());node=next(x for x in tree.body if isinstance(x,ast.FunctionDef) and x.name=='_episode_duration')
    namespace={'DAY':86400.,'HOUR':3600.};exec(compile(ast.Module(body=[node],type_ignores=[]),str(dest),'exec'),namespace)
    result=namespace['_episode_duration']('cycling','obvious',np.random.default_rng(7),1.,600.,60.)
    assert 0<result<=540.
    long=namespace['_episode_duration']('cycling','obvious',np.random.default_rng(7),1.,10*86400.,86400.)
    assert 1.5*86400<=long<=4*86400
