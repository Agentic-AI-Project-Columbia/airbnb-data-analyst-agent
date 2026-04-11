import os
import sys
import json
import uuid
import io
import threading
import traceback
import contextlib

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


def _reset_matplotlib() -> None:
    """Reset matplotlib state to avoid leaks between exec calls."""
    try:
        import matplotlib
        import matplotlib.pyplot as plt
        plt.close("all")
        matplotlib.rcParams.update(matplotlib.rcParamsDefault)
        matplotlib.use("Agg")
    except Exception:
        pass


def execute_python(code: str) -> str:
    """Run Python code via exec() in an isolated namespace and return stdout + artifacts."""
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
        "import matplotlib.pyplot as plt\n"
        "plt.rcParams['figure.constrained_layout.use'] = True\n"
        f"ARTIFACTS_DIR = r'{run_artifacts_dir}'\n"
        f"DATA_DIR = r'{data_dir}'\n"
    )
    postamble = (
        "\n\n"
        "# Auto-save orphaned matplotlib figures, then close all.\n"
        "try:\n"
        "    import os as _artifact_os\n"
        "    import matplotlib.pyplot as _artifact_plt\n"
        "    _existing_artifacts = set(_artifact_os.listdir(ARTIFACTS_DIR))\n"
        "    _figure_numbers = list(_artifact_plt.get_fignums())\n"
        "    # Only auto-save if the code didn't save any charts itself\n"
        "    if _figure_numbers and not _existing_artifacts:\n"
        "        for _index, _figure_number in enumerate(_figure_numbers, start=1):\n"
        "            _candidate = _artifact_os.path.join(ARTIFACTS_DIR, f'chart_{_index}.png')\n"
        "            _figure = _artifact_plt.figure(_figure_number)\n"
        "            _figure.savefig(_candidate, dpi=150, bbox_inches='tight')\n"
        "    _artifact_plt.close('all')\n"
        "except Exception as _artifact_save_error:\n"
        "    print(f'[artifact-save-warning] {_artifact_save_error}')\n"
    )
    full_code = preamble + code + postamble

    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()
    exec_globals = {"__builtins__": __builtins__}
    result = {"completed": False, "error": None}

    def _run():
        try:
            with contextlib.redirect_stdout(stdout_capture), contextlib.redirect_stderr(stderr_capture):
                exec(compile(full_code, f"<agent_code_{run_id}>", "exec"), exec_globals)
            result["completed"] = True
        except SystemExit as e:
            result["completed"] = (e.code is None or e.code == 0)
            if not result["completed"]:
                stderr_capture.write(f"Script exited with code {e.code}\n")
        except Exception:
            stderr_capture.write(traceback.format_exc())
            result["error"] = traceback.format_exc()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    thread.join(timeout=TIMEOUT_SECONDS)

    if thread.is_alive():
        _reset_matplotlib()
        return json.dumps({"error": f"Code execution timed out after {TIMEOUT_SECONDS}s"})

    _reset_matplotlib()

    stdout = stdout_capture.getvalue()
    stderr = stderr_capture.getvalue()
    stdout = stdout[-8000:] if len(stdout) > 8000 else stdout
    stderr = stderr[-4000:] if len(stderr) > 4000 else stderr

    exit_code = 0 if result["completed"] and not result["error"] else 1

    artifacts = []
    if os.path.isdir(run_artifacts_dir):
        for f in os.listdir(run_artifacts_dir):
            artifacts.append(
                {"filename": f, "path": f"/artifacts/{run_id}/{f}"}
            )

    return json.dumps({
        "stdout": stdout,
        "stderr": stderr,
        "exit_code": exit_code,
        "artifacts": artifacts,
    })
