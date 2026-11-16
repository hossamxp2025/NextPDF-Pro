"""Private conversion subprocess: writes only into its temporary job directory."""
import json
import logging
import sys
import traceback
from pathlib import Path
from src.engine.conversion import export_pdf, SUPPORTED
from src.job_result import guarded_run, progress


def _convert(request_path):
    request = Path(request_path).resolve()
    options = json.loads(request.read_text(encoding="utf-8"))
    if options["format"] not in SUPPORTED:
        raise ValueError("Unsupported conversion")
    export_pdf((request.parent / "input.pdf").read_bytes(),
               str(request.parent / ("output." + options["format"])),
               options["pages"], options["format"], progress=progress)
    return 0


def run(request_path):
    """Guard the imported entry point too (the frozen EXE calls this directly)."""
    return guarded_run(request_path, _convert)


if __name__ == "__main__":
    sys.exit(run(sys.argv[1]))
