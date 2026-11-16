"""File-based child protocol also works with windowed executables (no stdout)."""
import json
import logging
import sys
import traceback
from pathlib import Path

logger = logging.getLogger("NextPDF")


def progress(current, total):
    if sys.stdout is not None:
        print(json.dumps({"current": current, "total": total}), flush=True)


def guarded_run(request_path, action):
    directory = Path(request_path).resolve().parent
    try:
        action(request_path)
        (directory / "result.json").write_text(json.dumps({"ok": True}), encoding="utf-8")
        return 0
    except Exception as exc:
        logger.exception("Child job failed")
        detail = traceback.format_exc()
        try:
            for output in directory.glob("output.*"):
                output.unlink()
            (directory / "traceback.txt").write_text(detail, encoding="utf-8")
            code = "no_tables" if str(exc) == "No supported tables were found" else "job_failed"
            (directory / "result.json").write_text(json.dumps(
                {"ok": False, "error_code": code}), encoding="utf-8")
        except OSError:
            logger.exception("Cannot persist child failure evidence")
        return 1


def read_result(directory):
    result = json.loads((directory / "result.json").read_text(encoding="utf-8"))
    if not isinstance(result, dict) or type(result.get("ok")) is not bool:
        raise ValueError("Invalid child result schema")
    if not result["ok"] and result.get("error_code") not in {"no_tables", "job_failed"}:
        raise ValueError("Invalid child error code")
    return result
