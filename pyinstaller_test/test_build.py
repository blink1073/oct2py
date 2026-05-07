"""Build and run the oct2py PyInstaller app, verifying its output.

Run from the repo root:

    python pyinstaller_test/test_build.py

Exit code 0 on success, non-zero on failure.
"""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
SPEC = HERE / "oct2py_app.spec"
DIST = HERE / "dist"


def build() -> None:
    """Build the one-file executable from the spec."""
    print("Building with PyInstaller...")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--distpath",
            str(DIST),
            "--workpath",
            str(HERE / "build"),
            str(SPEC),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("--- PyInstaller stdout ---")
        print(result.stdout[-4000:])
        print("--- PyInstaller stderr ---")
        print(result.stderr[-4000:])
        sys.exit(f"PyInstaller build failed (exit {result.returncode})")
    print("Build succeeded.")


def run() -> None:
    """Run the bundled executable and verify its output."""
    exe_name = "oct2py_app.exe" if sys.platform == "win32" else "oct2py_app"
    exe = DIST / exe_name
    if not exe.exists():
        sys.exit(f"Executable not found: {exe}")

    print(f"Running {exe}...")
    result = subprocess.run(
        [str(exe)],
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )

    print("--- stdout ---")
    print(result.stdout)
    if result.stderr:
        print("--- stderr ---")
        print(result.stderr)

    if result.returncode != 0:
        sys.exit(f"App exited with code {result.returncode}")

    expected = "All Octave commands completed successfully."
    if expected not in result.stdout:
        sys.exit(f"Expected output not found: {expected!r}")

    print("All checks passed.")


if __name__ == "__main__":
    build()
    run()
