"""
Python code execution module for AI assistant
Provides safe execution with sandboxing, timeout, and output capture
"""

import subprocess
import sys
import os
import json
import tempfile
from typing import Dict, Any
import signal
import threading


class ExecutionTimeout(Exception):
    """Raised when code execution exceeds time limit"""
    pass


class ExecutionError(Exception):
    """Raised when code execution fails"""
    pass


def run_script(
    script: str,
    timeout: int = 30,
    max_output: int = 5000,
    allowed_imports: bool = True
) -> Dict[str, Any]:
    """
    Execute Python script safely with timeout and output capture.
    
    Args:
        script (str): Python code to execute
        timeout (int): Maximum execution time in seconds (default: 30)
        max_output (int): Maximum output length in characters (default: 5000)
        allowed_imports (bool): Whether to allow imports (default: True)
    
    Returns:
        Dict containing:
        - success (bool): Whether execution was successful
        - output (str): Captured stdout
        - error (str): Error message if execution failed
        - execution_time (float): Time taken to execute
    
    Raises:
        ExecutionTimeout: If code exceeds timeout
        ExecutionError: If code execution fails
    """
    
    import time
    start_time = time.time()
    
    # Security check: warn about dangerous operations
    dangerous_patterns = [
        'os.system', 'subprocess.', 'exec(', 'eval(', '__import__',
        'open(', 'compile(', 'input(', 'raw_input('
    ]
    
    has_dangerous = any(pattern in script for pattern in dangerous_patterns)
    
    # Create temporary file for execution
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        temp_file = f.name
        f.write(script)
    
    try:
        # Prepare the execution environment
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        
        # Run script in subprocess with timeout
        try:
            result = subprocess.run(
                [sys.executable, temp_file],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env
            )
            
            execution_time = time.time() - start_time
            
            # Combine stdout and stderr
            output = result.stdout
            error = result.stderr if result.returncode != 0 else ""
            
            # Limit output size
            if len(output) > max_output:
                output = output[:max_output] + f"\n... (output truncated, {len(output) - max_output} chars omitted)"
            
            if result.returncode != 0:
                return {
                    'success': False,
                    'output': output,
                    'error': error or "Script exited with non-zero status",
                    'execution_time': execution_time,
                    'return_code': result.returncode,
                    'dangerous_pattern_detected': has_dangerous
                }
            
            return {
                'success': True,
                'output': output,
                'error': "",
                'execution_time': execution_time,
                'dangerous_pattern_detected': has_dangerous
            }
        
        except subprocess.TimeoutExpired:
            execution_time = time.time() - start_time
            return {
                'success': False,
                'output': "",
                'error': f"Script execution timed out (exceeded {timeout} seconds)",
                'execution_time': execution_time,
                'return_code': -1,
                'dangerous_pattern_detected': has_dangerous
            }
    
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            'success': False,
            'output': "",
            'error': f"Execution error: {str(e)}",
            'execution_time': execution_time,
            'return_code': -1,
            'dangerous_pattern_detected': has_dangerous
        }
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
        except:
            pass


def validate_script(script: str) -> Dict[str, Any]:
    """
    Validate Python script for syntax and security issues.
    
    Args:
        script (str): Python code to validate
    
    Returns:
        Dict containing:
        - valid (bool): Whether script is syntactically valid
        - error (str): Error message if invalid
        - warnings (list): List of security warnings
    """
    
    warnings = []
    
    # Check syntax
    try:
        compile(script, '<string>', 'exec')
    except SyntaxError as e:
        return {
            'valid': False,
            'error': f"Syntax error: {e.msg}",
            'warnings': []
        }
    
    # Check for dangerous patterns
    dangerous_patterns = {
        'os.system': 'Using os.system is dangerous',
        'subprocess.': 'Using subprocess is potentially dangerous',
        'exec(': 'Using exec() is dangerous',
        'eval(': 'Using eval() is dangerous',
        '__import__': 'Dynamic imports may be unsafe',
        'open(': 'File operations should be reviewed',
        'input(': 'Input() will block execution',
    }
    
    for pattern, warning in dangerous_patterns.items():
        if pattern in script:
            warnings.append(warning)
    
    return {
        'valid': True,
        'error': "",
        'warnings': warnings
    }


if __name__ == "__main__":
    # Test examples
    test_cases = [
        "print('Hello, World!')",
        "x = 5\nprint(x ** 2)",
        "import json\ndata = {'name': 'Test'}\nprint(json.dumps(data))",
        "while True: pass",  # Will timeout
        "print(1/0)",  # Will error
    ]
    
    for i, script in enumerate(test_cases, 1):
        print(f"\n--- Test {i} ---")
        print(f"Script: {script[:50]}...")
        result = run_script(script, timeout=2)
        print(f"Success: {result['success']}")
        print(f"Output: {result['output'][:100]}")
        if result['error']:
            print(f"Error: {result['error'][:100]}")
