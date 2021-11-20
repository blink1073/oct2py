""" Get a sample of all datatypes from Octave and print the result
"""
from oct2py import octave

if __name__ == '__main__':
    out = octave.test_datatypes()
    import pprint
    pprint.pprint(out)
