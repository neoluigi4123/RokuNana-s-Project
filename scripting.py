import os
import sys
import urllib.request
import tempfile
import shutil

# Configuration
# Updated to use the Python 3.12.0 Wasm binary
WASM_VERSION = "3.12.0"
WASM_RUNTIME_URL = "https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python%2F3.12.0%2B20231211-040d5a6/python-3.12.0.wasm"
WASM_FILE = f"python-{WASM_VERSION}.wasm"

def _ensure_dependencies():
    """Checks for wasmtime lib and the python.wasm image."""
    try:
        import wasmtime
    except ImportError:
        import subprocess
        print("Installing sandbox engine (wasmtime)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wasmtime"])
        import wasmtime

    if not os.path.exists(WASM_FILE):
        print(f"Downloading Python {WASM_VERSION} Wasm image...")
        try:
            req = urllib.request.Request(
                WASM_RUNTIME_URL, 
                headers={'User-Agent': 'Mozilla/5.0'}
            )
            with urllib.request.urlopen(req) as response, open(WASM_FILE, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            print("Download complete.")
        except Exception as e:
            raise RuntimeError(f"Failed to download Wasm image: {e}")

def run_script(script: str) -> str:
    _ensure_dependencies()
    
    from wasmtime import Engine, Store, Module, Linker, WasiConfig

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Setup the script and log files
        script_name = "main.py"
        host_script_path = os.path.join(temp_dir, script_name)
        out_log = os.path.join(temp_dir, "out.log")
        
        with open(host_script_path, 'w') as f:
            f.write(script)

        try:
            # 2. Configure the Sandbox
            engine = Engine()
            linker = Linker(engine)
            linker.define_wasi()

            wasi = WasiConfig()
            
            # Mount the directory
            wasi.preopen_dir(temp_dir, "/app")
            
            # Tell Wasm Python to run /app/main.py
            wasi.argv = ["python", f"/app/{script_name}"]
            wasi.inherit_env()

            # Fix: Pass string file paths instead of integer pipes
            wasi.stdout_file = out_log
            wasi.stderr_file = out_log

            store = Store(engine)
            store.set_wasi(wasi)

            # 3. Load & Run
            module = Module.from_file(engine, WASM_FILE)
            instance = linker.instantiate(store, module)
            
            start = instance.exports(store)["_start"]
            
            try:
                start(store)
            except Exception:
                # WASI runtimes often raise a Trap on standard sys.exit(), which is perfectly normal
                pass

            # 4. Read Output
            with open(out_log, 'r') as f:
                return f.read()

        except Exception as e:
            return f"Sandbox Error: {e}"

if __name__ == "__main__":
    user_script = """import sys
print(f"Hello from Wasm! Python version: {sys.version.split()[0]}")
for i in range(3):
    print(f"Sandbox Count: {i}")
"""
    
    print("--- Starting Sandbox ---")
    output = run_script(user_script)
    print("--- Sandbox Output ---")
    print(output)