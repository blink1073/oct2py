"""
.. module:: _h5write
   :synopsis: Write Python values into an HDF file for Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
try:
    import h5py
except:
    print('Please install h5py from')
    print('"http://code.google.com/p/h5py/downloads/list"')
    raise
import os
import numpy as np
from ._utils import Oct2PyError, _register_del, _create_hdf


class H5Write(object):
    """Write Python values into an HDF file for Octave.

    Strives to preserve both value and type in transit.
    """
    def __init__(self):
        self.in_file = _create_hdf('load')
        _register_del(self.in_file)

    def create_file(self, inputs, names=None):
        """
        Create an HDF file, loading the input variables.

        If names are given, use those, otherwise use dummies.

        Parameters
        ==========
        inputs : array-like
            List of variables to write to a file.
        names : array-like
            Optional list of names to assign to the variables.

        Returns
        =======
        argin_list : str or array
            Name or list of variable names to be sent.
        load_line : str
            Octave "load" command.

        """
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
        """
        Put a nested dict into the HDF file as a struct

        Parameters
        ==========
        group : h5py group object
            Location to store the value
        dict_ : dict
            Dictionary of object(s) to store

        """
        for key in dict_.keys():
            if isinstance(dict_[key], dict):
                sub = group.create_group(key)
                self._putvals(sub, dict_[key])
            else:
                self._putval(group, key, dict_[key])

    @staticmethod
    def _putval(group, name, data):
        """
        Convert data into a state suitable for transfer.

        Parameters
        ==========
        group : h5py group object
            Location to store the object.
        name : str
            Name of the object.
        data : object
            Value to write to file.

        Notes
        =====
        All data is sent as an ndarray.  Several considerations must be made
        for data type to ensure proper read/write of the HDF.
        Currently string arrays of rank > 2 and the following types are not
        supported: float96, complex192, object.

        """
        if data is None:
            data = np.nan
        if isinstance(data, set):
            data = np.array(tuple(data))
        try:
            data = np.array(data)
        except ValueError as err:
            raise Oct2PyError(err)
        if data.dtype.str == '<c8':
            data = data.astype(np.complex128)
        if data.dtype.str == '<m8[us]' or data.dtype.str == '<M8[us]':
            data = data.astype(np.uint64)
        if data.dtype.str == '<c16':
            temp = [(item.real, item.imag) for item in data.ravel()]
            temp = np.array(temp, dtype=np.dtype([('real', '<f8'),
                                       ('imag', '<f8')]))
            data = temp.reshape(data.shape)
        elif data.dtype.str == '|b1':
            data = data.astype(np.int32)
        elif 'f' in data.dtype.str and not '12' in data.dtype.str:
            data = data.astype(np.float64)
        elif '|S' in data.dtype.str or '<U' in data.dtype.str:
            nchars = int(data.dtype.str[2:]) + 1
            data = data.astype(np.dtype('|S%s' % nchars))
            if len(data.shape) > 1:
                # TODO: implement this
                # Note: will probably have to fully mimic what the cell
                #      array looks like coming out of Octave
                raise Oct2PyError('Cannot send string objects of rank > 1')
        elif data.dtype.str in ['<f12', '<c24', '|O4']:
            # TODO: implement objects
            raise Oct2PyError('Datatype not supported: %s' % data.dtype)
        # Octave reads the data in Fortran order, not 'C' order
        data = data.T
        group.create_dataset(name, data=data)
