"""Utilities for extracting and executing translated Z3 programs."""

import re
import json
import subprocess
import tempfile
import os


def extract_python_code(markdown_text) -> str:
    """Return the longest fenced Python code block from a markdown response."""
    pattern = r"```python\s+(.*?)\s+```"
    matches = re.findall(pattern, markdown_text, re.DOTALL)
    if not matches:
        return "NO CODE FOUND"
    # Prefer the most complete program when multiple code blocks are returned.
    return max(matches, key=len)


def run_python_code(code):
    """Execute a translated Python program in a temporary file and capture output."""
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as tmpfile:
        tmpfile.write(code)
        tmpfile_path = tmpfile.name
    timeout = 120
    try:
        result = subprocess.run(
            ["python", tmpfile_path],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return result.stdout, ""
    except subprocess.TimeoutExpired:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return "", "Error: Execution timed out after {} seconds.".format(timeout)
    except subprocess.CalledProcessError as e:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return "", e.stderr
    except Exception as e:
        if tmpfile_path and os.path.exists(tmpfile_path):
            os.remove(tmpfile_path)
        return "", "Error: {}".format(str(e))


def z3_exec(markdown_text):
    """Execute the translated program and validate its single-option output."""
    code = extract_python_code(markdown_text)
    stdout, stderr = run_python_code(code)
    # MAC-Reasoner expects exactly one option label as the executable program output.
    if len(stdout.strip()) > 1 and not stderr:
        stderr = "Output multiple answer options"
    if len(stdout.strip()) == 0 and not stderr:
        stderr = "No output answer options"
    return stdout, stderr
