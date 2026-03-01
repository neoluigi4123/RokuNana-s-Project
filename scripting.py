"""
scripting.py
Execute Python scripts in a restricted environment.
"""
import io
import contextlib

def safe_open(file, mode='r', *args, **kwargs):
    """
    A wrapper around open() that forbids writing or creating files.
    """
    # Normalize mode to lowercase
    mode = mode.lower()
    
    # Check for forbidden flags:
    # 'w' = write (truncates/overwrites)
    # 'a' = append (writes)
    # 'x' = exclusive creation
    # '+' = updating (read + write)
    if 'w' in mode or 'a' in mode or 'x' in mode or '+' in mode:
        raise PermissionError(f"Security: Writing/Modifying files is forbidden. Mode '{mode}' not allowed.")
    
    # If safe, proceed with the standard open
    return open(file, mode, *args, **kwargs)

def run_script(script: str) -> str:
    # Redirect stdout and stderr to capture output
    output = io.StringIO()
    
    # We define the globals. 
    # CRITICAL: We map 'open' to our 'safe_open' function.
    restricted_globals = {
        "__builtins__": {
            "print": print,
            "range": range,
            "len": len,
            "str": str,
            "int": int,
            "list": list,
            "dict": dict,
            "open": safe_open,
             "__import__": __import__ # <--- WARNING
        }
    }
    restricted_locals = {}

    try:
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
            exec(script, restricted_globals, restricted_locals)
    except Exception as e:
        return f"Error during execution: {e}"
    
    return output.getvalue()