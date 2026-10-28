from pathlib import Path
import subprocess
HISTORIANSIM_SHA = "14e616c382a9db8026cbb4ab86bdd803d56ca72e"
HISTORIANRCA_SHA = "8d12a821395ce5f72e464dc78cc2c10d05cbb9ed"
class UpstreamNotReady(RuntimeError):
    pass
def verify_upstreams(repo_root: Path) -> None:
    script = repo_root / "scripts" / "verify_upstreams.sh"
    p = subprocess.run([str(script)], capture_output=True, text=True)
    if p.returncode:
        raise UpstreamNotReady((p.stderr or p.stdout).strip())
