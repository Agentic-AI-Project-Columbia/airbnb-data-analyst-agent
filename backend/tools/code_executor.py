import os
import sys
import json
import uuid
import subprocess
import tempfile

ARTIFACTS_DIR = os.environ.get(
    "ARTIFACTS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "artifacts"),
)

ALLOWED_IMPORTS = {
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "json", "csv", "math", "statistics", "collections",
    "datetime", "re", "os", "io", "textwrap",
    "duckdb",
}

TIMEOUT_SECONDS = 120


def execute_python(code: str) -> str:
    """Run Python code in a subprocess and return stdout + list of saved artifacts."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    run_id = uuid.uuid4().hex[:8]
    run_artifacts_dir = os.path.join(ARTIFACTS_DIR, run_id).replace("\\", "/")
    os.makedirs(run_artifacts_dir, exist_ok=True)

    data_dir = os.environ.get(
        "DATA_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "Sample Data"),
    ).replace("\\", "/")

    preamble = (
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        f"ARTIFACTS_DIR = r'{run_artifacts_dir}'\n"
        f"DATA_DIR = r'{data_dir}'\n"
    )
    full_code = preamble + code

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(full_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            cwd=os.path.dirname(tmp_path),
        )
        stdout = result.stdout[-8000:] if len(result.stdout) > 8000 else result.stdout
        stderr = result.stderr[-4000:] if len(result.stderr) > 4000 else result.stderr

        artifacts = []
        for f in os.listdir(run_artifacts_dir):
            artifacts.append(
                {"filename": f, "path": f"/artifacts/{run_id}/{f}"}
            )

        return json.dumps({
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "artifacts": artifacts,
        })
    except subprocess.TimeoutExpired:
        return json.dumps({"error": f"Code execution timed out after {TIMEOUT_SECONDS}s"})
    finally:
        os.unlink(tmp_path)
