import ast
import os
import sys
import uuid
import subprocess

from models.schemas import ArtifactRef, CodeExecutionResult

ALLOWED_IMPORTS = {
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "json", "csv", "math", "statistics", "collections",
    "datetime", "re", "os", "io", "textwrap",
    "duckdb",
    "itertools", "pathlib", "typing",
    "time", "warnings",
}

TIMEOUT_SECONDS = 120

ARTIFACTS_DIR = os.environ.get(
    "ARTIFACTS_DIR",
    os.path.join(os.path.dirname(__file__), "..", "artifacts"),
)


def _validate_imports(code: str) -> str | None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return f"Syntax error before execution: {exc}"

    disallowed: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module = alias.name.split(".")[0]
                if module not in ALLOWED_IMPORTS:
                    disallowed.add(module)
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                continue
            module = node.module.split(".")[0]
            if module not in ALLOWED_IMPORTS:
                disallowed.add(module)

    if disallowed:
        blocked = ", ".join(sorted(disallowed))
        allowed = ", ".join(sorted(ALLOWED_IMPORTS))
        return f"Disallowed imports: {blocked}. Allowed imports: {allowed}."

    return None


def execute_python(code: str, require_artifacts: bool = False) -> str:
    """Run Python code in a subprocess and return stdout, stderr, and artifacts."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)

    run_id = uuid.uuid4().hex[:8]
    run_artifacts_dir = os.path.join(ARTIFACTS_DIR, run_id).replace("\\", "/")
    os.makedirs(run_artifacts_dir, exist_ok=True)

    data_dir = os.environ.get(
        "DATA_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "Sample Data"),
    ).replace("\\", "/")

    import_error = _validate_imports(code)
    if import_error is not None:
        return CodeExecutionResult(
            stdout="",
            stderr=import_error,
            exit_code=1,
            artifacts=[],
        ).model_dump_json()

    preamble = (
        "# -*- coding: utf-8 -*-\n"
        "import os\n"
        "import matplotlib\n"
        "matplotlib.use('Agg')\n"
        "import matplotlib.pyplot as plt\n"
        f"ARTIFACTS_DIR = r'{run_artifacts_dir}'\n"
        f"DATA_DIR = r'{data_dir}'\n"
        "os.environ['ARTIFACTS_DIR'] = ARTIFACTS_DIR\n"
        "os.environ['DATA_DIR'] = DATA_DIR\n"
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

    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env["MPLBACKEND"] = "Agg"
    env["DATA_DIR"] = data_dir
    env["ARTIFACTS_DIR"] = run_artifacts_dir

    try:
        result = subprocess.run(
            [sys.executable, "-"],
            input=full_code,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            cwd=os.path.dirname(__file__),
            env=env,
            check=False,
        )
        stdout = result.stdout
        stderr = result.stderr
        exit_code = result.returncode
    except subprocess.TimeoutExpired:
        return CodeExecutionResult(
            stdout="",
            stderr=f"Code execution timed out after {TIMEOUT_SECONDS}s",
            exit_code=1,
            artifacts=[],
        ).model_dump_json()

    stdout = stdout[-8000:] if len(stdout) > 8000 else stdout
    stderr = stderr[-4000:] if len(stderr) > 4000 else stderr

    artifacts: list[ArtifactRef] = []
    if os.path.isdir(run_artifacts_dir):
        for f in os.listdir(run_artifacts_dir):
            artifacts.append(
                ArtifactRef(filename=f, path=f"/artifacts/{run_id}/{f}")
            )

    if require_artifacts and exit_code == 0 and not artifacts:
        artifact_hint = (
            "No artifacts were created. Save generated files to the local filesystem "
            "directory stored in ARTIFACTS_DIR. Do not save directly to /artifacts/..."
            " paths; those are public URLs returned after a file is written successfully."
        )
        stderr = f"{stderr}\n{artifact_hint}".strip() if stderr else artifact_hint
        exit_code = 1

    return CodeExecutionResult(
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        artifacts=artifacts,
    ).model_dump_json()
