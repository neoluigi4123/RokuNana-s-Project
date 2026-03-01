import os
import sys
import urllib.request
import tempfile

# Configuration
WASM_RUNTIME_URL = "https://github.com/vmware-labs/webassembly-language-runtimes/releases/download/python-3.11.3/python-3.11.3.wasm"
WASM_FILE = "python-3.11.3.wasm"

def _ensure_dependencies():
    """
    Auto-setup:
    1. Checks if 'wasmtime' lib is installed.
    2. Checks if 'python.wasm' file exists.
    """
    # 1. Check Library
    try:
        import wasmtime
    except ImportError:
        import subprocess
        print("Installing sandbox engine (wasmtime)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "wasmtime"])
        import wasmtime # Retry import

    # 2. Check Wasm Image
    if not os.path.exists(WASM_FILE):
        print(f"Downloading Python Wasm image to {os.getcwd()}...")
        try:
            urllib.request.urlretrieve(WASM_RUNTIME_URL, WASM_FILE)
            print("Download complete.")
        except Exception as e:
            raise RuntimeError(f"Failed to download Wasm image: {e}")

def run_script(script: str) -> str:
    # 1. Auto-install dependencies if needed
    _ensure_dependencies()
    
    from wasmtime import Engine, Store, Module, Linker, WasiConfig, Config

    # 2. Write the user script to a temp file (because we must pass it to the Wasm VM)
    # Note: We are creating a file on the Host, but the Wasm VM can ONLY read this one file.
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as tf:
        tf.write(script)
        script_path = tf.name

    try:
        # 3. Configure the Sandbox
        engine = Engine()
        linker = Linker(engine)
        linker.define_wasi()

        # Config WASI (The OS interface for Wasm)
        wasi = WasiConfig()
        wasi.inherit_argv()
        wasi.inherit_env()
        
        # Capture Stdout/Stderr to a pipe
        r_pipe, w_pipe = os.pipe()
        wasi.stdout_file = w_pipe
        wasi.stderr_file = w_pipe
        
        # MOUNTING: We only mount the script file. 
        # The VM sees the host's 'script_path' as '/app.py'
        # It has NO access to the rest of your drive.
        wasi.preopen_dir(script_path, "/app.py")

        store = Store(engine)
        store.set_wasi(wasi)
        
        # 4. Load Python Wasm Module
        module = Module.from_file(engine, WASM_FILE)
        instance = linker.instantiate(store, module)
        
        # 5. Execute: "python /app.py"
        # The export name '_start' is standard for WASI binaries
        start = instance.exports(store)["_start"]
        
        try:
            start(store)
        except Exception:
            # Wasm usually throws an exit trap when the script finishes (sys.exit(0))
            pass

        # 6. Read Output
        os.close(w_pipe)
        with os.fdopen(r_pipe, 'r') as f:
            return f.read()

    except Exception as e:
        return f"Sandbox Error: {e}"
    finally:
        if os.path.exists(script_path):
            os.remove(script_path)