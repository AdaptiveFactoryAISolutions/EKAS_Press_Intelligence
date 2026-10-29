# 2. Installation and first use

[Wiki home](Home.md) · [Next: guided press setup](03-Guided-press-setup.md)

## If someone has already installed it

1. Ask the installer for the press-line address. On this workstation it is `http://127.0.0.1:18729/#setup`.
2. Open it in your browser. `127.0.0.1` means this computer; on another computer you need the address supplied by the installer.
3. Wait for the connection indicator to finish connecting.
4. If the installer supplied a service token, select **Access**, enter it and choose **Apply credential**. A token is your service access credential; do not paste it into a wiki, screenshot or URL.
5. The **Guided press setup** screen opens. If it does not, select that navigation button.
6. For your first run, keep the standard line and settings. Follow [the eight setup steps](03-Guided-press-setup.md).
7. At Step 8 select **Check setup**, then **Run practice**.
8. Watch **Durable jobs**. After completion choose **View practice results**.
9. In the explorer choose a signal, keep **Primary / raw measurements**, and select **Query measurements**.
10. Read the visible practice status and quality information. Open **Process context and downloads** for equipment context. A bounded query may show only the beginning of the history; narrow its dates for later events.

You have completed the first-use check when a real generated line dataset and its measurements load. This proves the configuration/execution/browsing path; it does not establish real-machine accuracy or full native qualification.

## Installer steps: a new local press-line installation

These steps are for the person maintaining the computer. Ordinary users can skip this section. Use a new checkout; do not overwrite another user's running installation. Linux prerequisites are Git, Python 3.12 with venv support, g++, OpenSSL and working Bubblewrap namespaces. The isolated analyst also needs separately configured provider access.

The full-stack candidate is on `full-stack-foundation`; the default branch may contain the earlier prototype. Run each line in a terminal and stop if it reports an error.

```bash
git clone --recurse-submodules --branch full-stack-foundation https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence.git
cd EKAS_Press_Intelligence
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e 'vendor/HistorianSim[dev]' -e '.[dev]'
bash scripts/verify_upstreams.sh
.venv/bin/python scripts/prepare_native_runtime.py
export EKAS_NATIVE_RUNTIME="$PWD/work/native-runtime"
export EKAS_NATIVE_STATE_DIR="$PWD/work/press-line-service"
export EKAS_NATIVE_BLAS_THREADS=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -m uvicorn ekas_press_intelligence.native.api:create_native_app --factory --host 127.0.0.1 --port 18729
```

Keep that terminal running and open `http://127.0.0.1:18729/#setup`. Expected result: the guided setup loads with the complete line preset. If the port is already in use, use the existing service or ask its owner; do not stop an unidentified process.

This prepares a verified hybrid runtime containing the new `stamping_line` plant, the earlier experimental press and the reference plants. The wizard selects `stamping_line`; do not choose the old press in expert workflows and mistake it for this preset. Runtime changes require source verification and a controlled restart; see [technical operations](../NATIVE_OPERATIONS.md). Keep prior runtime/state directories as evidence rather than overwriting a running installation. For a separate tank/reactor-only service use the reference commands in the repository README on port 18728.

Local token-free mode grants trusted administrator access. To serve other computers, the installer must configure separate roles, HTTPS, the private listener and proxy correctly. Changing the host to `0.0.0.0` is not a complete network deployment. See [Connecting EKAS](05-Connecting-EKAS.md).
