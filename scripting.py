"""
scripting.py
Execute Python scripts in a restricted environment.
"""
import io
import contextlib

def python_execution(script: str) -> str:
    try:
        import io, contextlib
        output = io.StringIO()
        global_vars = {"__builtins__": __builtins__}
        with contextlib.redirect_stdout(output):
            exec(script, global_vars)
        return output.getvalue() or "Script executed successfully (no output)."
    except Exception as e:
        return f"Error during execution: {e}"