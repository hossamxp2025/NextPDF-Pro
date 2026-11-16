"""Private subprocess for creating a PDF from user documents.

The parent never reads the sources beyond passing their paths; the child writes
only inside its temporary job directory.
"""
import json
import sys
from pathlib import Path

from src.engine.pdf_creation import create_pdf
from src.job_result import guarded_run, progress


def _run(request_path):
    request = Path(request_path).resolve()
    options = json.loads(request.read_text(encoding="utf-8"))


    create_pdf(options["sources"], str(request.parent / "output.pdf"), progress=progress)
    return 0


def run(request_path):
    return guarded_run(request_path, _run)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
