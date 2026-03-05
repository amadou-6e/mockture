from pathlib import Path

import nbformat
from nbclient import NotebookClient


def test_usage_notebook_runs_end_to_end() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    usage_dir = Path(repo_root, "usage")
    notebook_path = Path(usage_dir, "mockture_server_usage.ipynb")

    notebook = nbformat.read(str(notebook_path), as_version=4)

    runnable_cells = []
    for cell in notebook.cells:
        if cell.cell_type != "code":
            runnable_cells.append(cell)
            continue

        source = str(cell.source)
        if any(line.strip().startswith("%pip ") for line in source.splitlines()):
            # Avoid mutating test env during notebook execution.
            continue
        runnable_cells.append(cell)

    notebook.cells = runnable_cells

    client = NotebookClient(
        notebook,
        timeout=180,
        kernel_name="python3",
        resources={"metadata": {"path": str(usage_dir)}},
    )
    client.execute()

    swagger_path = Path(usage_dir, "basic_api.swagger.yml")
    assert swagger_path.exists()
    assert "openapi:" in swagger_path.read_text(encoding="utf-8")
