# 2. Installation and first use

[Wiki home](Home.md) · [Next: guided press setup](03-Guided-press-setup.md)

## If someone has already installed it

1. Ask the installer for the workspace address. On this workstation it is `http://127.0.0.1:18728/`.
2. Open it in your browser. `127.0.0.1` means this computer; on another computer you need the address supplied by the installer.
3. Wait for the connection indicator to finish connecting.
4. If the installer supplied a service token, select **Access**, enter it and choose **Apply credential**. A token is your service access credential; do not paste it into a wiki, screenshot or URL.
5. Select **Dataset explorer**.
6. In **Active dataset**, choose the original HistorianRCA benchmark or an existing generated record. The original record is a tank example, not your press.
7. In **Signals**, select one measurement. Start with a single signal rather than mixing unrelated units.
8. Keep **Primary / raw measurements** selected and choose **Query measurements**.
9. Read the response metadata and quality information. A bounded query may return only the beginning of the matching history. Narrow the dates to see a later interval.
10. Open **Process context and downloads** to understand the equipment before drawing conclusions.

You have completed the first-use check when a real dataset and its measurements load without an error. This checks connectivity and browsing, not the accuracy of a press model.

## Installer steps: a new local reference installation

These steps are for the person maintaining the computer. Ordinary users can skip this section. Use a new checkout; do not overwrite another user's running installation. Linux prerequisites are Git, Python 3.12 with venv support, g++, OpenSSL and working Bubblewrap namespaces. The isolated analyst also needs separately configured provider access.

The full-stack candidate is on `full-stack-foundation`; the default branch may contain the earlier prototype. Run each line in a terminal and stop if it reports an error.

```bash
git clone --recurse-submodules --branch full-stack-foundation https://github.com/AdaptiveFactoryAISolutions/EKAS_Press_Intelligence.git
cd EKAS_Press_Intelligence
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install --no-deps -e 'vendor/HistorianSim[dev]' -e '.[dev]'
bash scripts/verify_upstreams.sh
.venv/bin/python scripts/prepare_reference_runtime.py
export EKAS_NATIVE_RUNTIME="$PWD/work/reference-runtime"
export EKAS_NATIVE_STATE_DIR="$PWD/work/native-service"
export EKAS_NATIVE_BLAS_THREADS=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
.venv/bin/python -m uvicorn ekas_press_intelligence.native.api:create_native_app --factory --host 127.0.0.1 --port 18728
```

Keep that terminal running and open `http://127.0.0.1:18728/`. Expected result: the workspace loads. If the port is already in use, use the existing service or ask its owner; do not stop an unidentified process.

This starts the **reference** runtime. It does not install the requested full press line. Do not switch a running reference service to the experimental press runtime and assume it is your line. Runtime changes require source verification and a controlled restart; see [technical operations](../NATIVE_OPERATIONS.md).

Local token-free mode grants trusted administrator access. To serve other computers, the installer must configure separate roles, HTTPS, the private listener and proxy correctly. Changing the host to `0.0.0.0` is not a complete network deployment. See [Connecting EKAS](05-Connecting-EKAS.md).
