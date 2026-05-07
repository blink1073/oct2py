"""Simple oct2py app to be bundled with PyInstaller."""

import sys

from oct2py import Oct2Py


def main() -> int:
    """Run a small set of Octave commands and print results."""
    print("Starting oct2py PyInstaller test app...")
    with Oct2Py() as oc:
        result = oc.eval("1 + 1")
        print(f"1 + 1 = {result}")
        assert result == 2, f"Expected 2, got {result}"

        result = oc.eval("sum([1, 2, 3, 4, 5])")
        print(f"sum([1,2,3,4,5]) = {result}")
        assert result == 15, f"Expected 15, got {result}"

        result = oc.sqrt(float(16))
        print(f"sqrt(16) = {result}")
        assert result == 4.0, f"Expected 4.0, got {result}"

        oc.push("x", [1.0, 2.0, 3.0])
        result = oc.pull("x")
        print(f"push/pull [1,2,3]: {result}")
        assert list(result[0]) == [1.0, 2.0, 3.0], f"Unexpected value: {result}"

    print("All Octave commands completed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
