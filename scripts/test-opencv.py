#!/usr/bin/env python
"""Regression test for issue #240: conflict between opencv-python and oct2py.

Validates that importing cv2 before or after oct2py no longer causes Octave
to crash with pexpect.exceptions.EOF due to a Qt platform plugin conflict.
"""

import subprocess
import sys
import textwrap

CASES = [
    (
        "cv2 imported before Oct2Py()",
        textwrap.dedent("""\
            import cv2
            from oct2py import Oct2Py
            oc = Oct2Py()
            result = oc.eval("1 + 1", verbose=False)
            oc.exit()
            assert result == 2
        """),
    ),
    (
        "cv2 imported after oct2py module, before Oct2Py()",
        textwrap.dedent("""\
            from oct2py import Oct2Py
            import cv2
            oc = Oct2Py()
            result = oc.eval("1 + 1", verbose=False)
            oc.exit()
            assert result == 2
        """),
    ),
]

failures = []
for name, code in CASES:
    print(f"Case: {name} ... ", end="", flush=True)
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        print("PASS")
    else:
        print("FAIL")
        print(f"  stdout: {result.stdout.strip()}")
        print(f"  stderr: {result.stderr.strip()}")
        failures.append(name)

if failures:
    print(f"\n{len(failures)} case(s) failed.")
    sys.exit(1)
else:
    print("\nAll cases passed.")
