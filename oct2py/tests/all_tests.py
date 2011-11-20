"""Run all tests for oct2py
"""
import glob
import os
import unittest


def run():
    """Run all tests for oct2py
    """
    test_file_strings = glob.glob('test_*.py')
    test_file_strings = [os.path.basename(fname) for fname
                            in test_file_strings]
    module_strings = [str_[0: len(str_) - 3] for str_ in test_file_strings]
    suites = [unittest.defaultTestLoader.loadTestsFromName(str_) for str_
                  in module_strings]
    test_suite = unittest.TestSuite(suites)
    unittest.TextTestRunner().run(test_suite)


if __name__ == '__main__':
    run()
