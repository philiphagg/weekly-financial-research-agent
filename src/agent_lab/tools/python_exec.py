from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from langchain.tools import tool


SAFE_WRAPPER = """
import json
import math
import statistics

INPUT = json.loads(r'''{input_json}''')

# user code starts here
{user_code}

if "RESULT" not in globals():
    raise ValueError("Your code must assign a variable named RESULT")

print(json.dumps({{"result": RESULT}}, ensure_ascii=False))
"""


def _validate_code(code: str) -> None:
    blocked = [
        "import os",
        "import sys",
        "import subprocess",
        "import socket",
        "import requests",
        "import httpx",
        "open(",
        "__import__",
        "eval(",
        "exec(",
    ]
    lowered = code.lower()
    for token in blocked:
        if token in lowered:
            raise ValueError(f"Blocked pattern in code: {token}")


@tool("run_python")
def run_python(code: str, input_json: str) -> dict:
    """
    Execute a small sandboxed Python analysis snippet.

    Use this for scoring, filtering, ranking, weighting, or lightweight calculations
    on already-fetched signal data.

    Arguments:
    - code: Python code that must assign its final value to RESULT
    - input_json: JSON string with input data for the analysis
    """
    _validate_code(code)

    # validera att input_json faktiskt är JSON innan vi kör subprocess
    try:
        json.loads(input_json)
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "stderr": f"Invalid input_json: {exc}",
        }

    wrapped = SAFE_WRAPPER.format(
        input_json=input_json.replace("'''", "\\'\\'\\'"),
        user_code=code,
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "sandbox.py"
        script_path.write_text(wrapped, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=5,
            cwd=tmpdir,
        )

        if proc.returncode != 0:
            return {
                "ok": False,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }

        try:
            parsed = json.loads(proc.stdout.strip())
        except json.JSONDecodeError:
            return {
                "ok": False,
                "stdout": proc.stdout,
                "stderr": "Could not parse JSON result",
            }

        return {
            "ok": True,
            "result": parsed.get("result"),
        }