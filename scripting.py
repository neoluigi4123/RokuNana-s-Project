import sys
import io
from RestrictedPython import compile_restricted, safe_builtins
from RestrictedPython.Eval import default_guarded_getiter, default_guarded_getitem
from RestrictedPython.Guards import guarded_iter_unpack_sequence

def run_script(script: str) -> str:
    """
    Executes script in a restricted namespace within the SAME process.
    Prevents file access and imports.
    """
    output = io.StringIO()
    
    # Define the strict whitelist of allowed functions
    # safe_builtins includes: True, False, None, abs, len, str, int, etc.
    # It expressly EXCLUDES: open, __import__, file, exec, eval
    restricted_globals = {
        '__builtins__': safe_builtins,
        '_getattr_': getattr,
        '_getitem_': default_guarded_getitem,
        '_getiter_': default_guarded_getiter,
        '_iter_unpack_sequence_': guarded_iter_unpack_sequence,
        'print': lambda *args, **kwargs: print(*args, file=output, **kwargs),
        'range': range,
        'list': list,
        'dict': dict,
    }

    try:
        # Pre-compile catches syntax errors before execution
        byte_code = compile_restricted(script, '<inline>', 'exec')
        exec(byte_code, restricted_globals)
    except Exception as e:
        return f"Error: {e}"

    return output.getvalue()