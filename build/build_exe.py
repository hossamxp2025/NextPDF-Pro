#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Build script for NextPDF Pro.

Creates a standalone Windows EXE with PyInstaller and (optionally) the Inno
Setup installer.  Releases are written to a versioned folder so an existing
release is never overwritten.
"""

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.version import APP_VERSION as VERSION


def _paths():
    base_dir = Path(__file__).resolve().parent.parent
    spec_file = base_dir / "build" / "NextPDF-Pro.spec"
    dist_dir = base_dir / "dist" / f"release-{VERSION}"
    work_dir = base_dir / "build" / "pyinstaller_build"
    return base_dir, spec_file, dist_dir, work_dir


def build_exe():
    """Build the standalone EXE."""
    base_dir, spec_file, dist_dir, work_dir = _paths()
    if (dist_dir / "NextPDF-Pro.exe").exists():
        raise FileExistsError(f"Refusing to overwrite an existing release: {dist_dir}")
    subprocess.run([sys.executable, str(base_dir / "build/generate_metadata.py")], check=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        str(spec_file),
    ]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(base_dir))
    if result.returncode != 0:
        print("Build failed!")
        return False

    exe = dist_dir / "NextPDF-Pro.exe"
    if not exe.exists():
        print(f"Build reported success but {exe} is missing.")
        return False
    print(f"Build successful: {exe} ({exe.stat().st_size / (1024 * 1024):.1f} MB)")
    return stage_release(dist_dir)


def stage_release(dist_dir=None):
    """Copy the documents the installer expects and write SHA256SUMS.txt."""
    base_dir, _, default_dist, _ = _paths()
    dist_dir = dist_dir or default_dist
    result = subprocess.run(
        [sys.executable, str(base_dir / "scripts/prepare_patch_package.py"), str(dist_dir)],
        cwd=str(base_dir))
    if result.returncode != 0:
        print("Staging the release documents failed.")
        return False
    return True


def _find_iscc():
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Inno Setup 6", "ISCC.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def build_installer():
    """Build the Inno Setup installer from the current release folder."""
    base_dir = Path(__file__).resolve().parent.parent
    iss_file = base_dir / "build" / "installer.iss"

    iscc = _find_iscc()
    if not iscc:
        print("Inno Setup compiler (ISCC.exe) not found. Install Inno Setup 6.")
        print("Download from: https://jrsoftware.org/isinfo.php")
        return False

    release_dir = _paths()[2]
    if not (release_dir / "README.txt").exists():
        stage_release(release_dir)

    cmd = [iscc, f"/DReleaseDir={release_dir}", str(iss_file)]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(base_dir))
    if result.returncode != 0:
        print("Installer build failed!")
        return False

    print("Installer build successful!")
    # Re-stage so SHA256SUMS.txt also covers the installer that was just built.
    return stage_release(release_dir)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--installer":
        success = build_installer()
    else:
        success = build_exe()
    sys.exit(0 if success else 1)
