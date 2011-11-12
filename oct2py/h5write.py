''' h5write - Used to write Python values into an HDF file for Octave

Strives to preserve both value and type in transit
'''
try:
    import h5py
except:
    print 'Please install h5py from'
    print '"http://code.google.com/p/h5py/downloads/list"'
    raise
import numpy as np
from helpers import OctaveError, _register_del, _create_hdf


class _OctaveH5Write(object):
    '''Used to write Python values into an HDF file for Octave

    Strives to preserve both value and type in transit
    '''
    def __init__(self):
        self.in_file = _create_hdf('load')
        _register_del(self.in_file)

    def create_file(self, inputs, names=None):
        ''' Create an HDF file, loading the input variables

        If names are given, use those, otherwise use dummies
        '''
        fid = h5py.File(self.in_file, "w")
        # create a dummy list of var names ("A", "B", "C" ...)
        # use ascii char codes so we can increment
        argin_list = []
        ascii_code = 65
        for var in inputs:
            if names:
                argin_list.append(names.pop(0))
            else:
                argin_list.append("%s__" % chr(ascii_code))
            # for structs - recursively add the elements
            if isinstance(var, dict):
                sub = fid.create_group(argin_list[-1])
                self._putvals(sub, var)
            else:
                self._putval(fid, argin_list[-1], var)
            ascii_code += 1
        fid.close()
        load_line = 'load "-hdf5" "%s" "%s"' % (self.in_file,
                                                '" "'.join(argin_list))
        return argin_list, load_line

    def _putvals(self, group, dict_):
        ''' Put a nested dict into the HDF file as a struct
        '''
        for key in dict_.keys():
            if isinstance(dict_[key], dict):
                sub = group.create_group(key)
                self._putvals(sub, dict_[key])
            else:
                self._putval(group, key, dict_[key])

    @staticmethod
    def _putval(group, name, data):
        ''' Handle variable types that do not translate directly
        '''
        # the last char is stripped off in transit
        if isinstance(data, str):
            data += '_'
        # lists get mangled unless you make them an ndarrays
        # XXX they will still get mangled for cell arrays
        #      (vectors work though)
        elif isinstance(data, list):
            data = np.array(data)
            # pad the strings here too
            if '|S' in data.dtype.str:
                if len(data.shape) > 1:
                    raise OctaveError('Cannot pass nested lists:\n%s' % data)
                nchars = int(data.dtype.str[2:])
                data = data.astype(np.dtype('|S%s' % (nchars + 1)))
        # matlab expects a specific array type for complex nums
        elif isinstance(data, complex):
            data = np.array((data.real, data.imag),
                           dtype=np.dtype([('real', '<f8'),
                                           ('imag', '<f8')]))
        if isinstance(data, np.ndarray):
            if data.dtype == np.dtype('complex128'):
                temp = [(item.real, item.imag) for item in data.ravel()]
                temp = np.array(temp, dtype=np.dtype([('real', '<f8'),
                                           ('imag', '<f8')]))
                data = temp.reshape(data.shape)
            # Matlab reads the data in Fortran order, not 'C' order
            data = data.T
        group.create_dataset(name, data=data)
