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
from _utils import Oct2PyError, register_del, create_hdf


class H5Write(object):
    '''Used to write Python values into an HDF file for Octave

    Strives to preserve both value and type in transit
    '''
    def __init__(self):
        self.in_file = create_hdf('load')
        register_del(self.in_file)

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
            try:
                if isinstance(var, dict):
                    sub = fid.create_group(argin_list[-1])
                    self._putvals(sub, var)
                else:
                    self._putval(fid, argin_list[-1], var)
            except Oct2PyError:
                fid.close()
                raise
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
        ''' Convert data into a state suitable for transfer.

        All data is sent as an ndarray.  Several considerations must be made
        for data type to ensure proper read/write of the HDF.

        Currently string arrays of rank > 2 and the following types are not
        supported: float96, complex192, object
        '''
        if isinstance(data, set):
            data = np.array(tuple(data))
        data = np.array(data)
        if data.dtype == np.dtype('complex64'):
            data = data.astype(np.complex128)
        if '<U' in data.dtype.str:
            data = data.astype(np.dtype('|S' + data.dtype.str[2:]))
        if data.dtype in [np.dtype('timedelta64'), np.dtype('datetime64')]:
            data = data.astype(np.uint64)
        if data.dtype == np.dtype('complex128'):
            temp = [(item.real, item.imag) for item in data.ravel()]
            temp = np.array(temp, dtype=np.dtype([('real', '<f8'),
                                       ('imag', '<f8')]))
            data = temp.reshape(data.shape)
        elif data.dtype == np.dtype('bool'):
            data = data.astype(np.int32)
        elif data.dtype == np.dtype('float16'):
            data = data.astype(np.float32)
        elif '|S' in data.dtype.str:
            nchars = int(data.dtype.str[2:]) + 1
            data = data.astype(np.dtype('|S%s' % nchars))
            if len(data.shape) > 1:
                # TODO: implement this
                # Note: will probably have to fully mimic what the cell
                #      array looks like coming out of Octave
                raise Oct2PyError('Cannot send string objects of rank > 1')
        else:
            if data.dtype in [np.dtype('float96'),
                              np.dtype('complex192'),
                              np.dtype('object')]:
                raise Oct2PyError('Datatype not supported: %s' %
                                  data.dtype)
        # Octave reads the data in Fortran order, not 'C' order
        data = data.T
        group.create_dataset(name, data=np.array(data))
