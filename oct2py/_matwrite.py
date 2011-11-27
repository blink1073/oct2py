"""
.. module:: _h5write
   :synopsis: Write Python values into an MAT file for Octave.
              Strives to preserve both value and type in transit.

.. moduleauthor:: Steven Silvester <steven.silvester@ieee.org>

"""
from scipy.io import savemat
import numpy as np
from _utils import Oct2PyError, _register_del, _create_file


class MatWrite(object):
    """Write Python values into a MAT file for Octave.

    Strives to preserve both value and type in transit.
    """
    def __init__(self):
        self.in_file = _create_file('load', 'mat')
        _register_del(self.in_file)

    def create_file(self, inputs, names=None):
        """
        Create a MAT file, loading the input variables.

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
        #fid = h5py.File(self.in_file, "w")
        # create a dummy list of var names ("A", "B", "C" ...)
        # use ascii char codes so we can increment
        argin_list = []
        ascii_code = 65
        data = {}
        for var in inputs:
            if names:
                argin_list.append(names.pop(0))
            else:
                argin_list.append("%s__" % chr(ascii_code))
            # for structs - recursively add the elements
            try:
                if isinstance(var, dict):
                    data[argin_list[-1]] = self._putvals(var)
                    #data[argin_list[-1]] = self._putvals(dict(), var)
                    #sub = fid.create_group(argin_list[-1])
                    #self._putvals(sub, var)
                else:
                    data[argin_list[-1]] = self._putval(var)
                    #self._putval(fid, argin_list[-1], var)
            except Oct2PyError:
                #fid.close()
                raise
            ascii_code += 1
        #fid.close()
        #import pdb; pdb.set_trace()
        try:
            savemat(self.in_file, data, do_compression=False, oned_as='row')
        except KeyError:
            import pdb; pdb.set_trace()
            pass
        load_line = 'load "%s" "%s"' % (self.in_file, '" "'.join(argin_list))
        return argin_list, load_line

    def _putvals(self, dict_):
        """
        Put a nested dict into the MAT file as a struct

        Parameters
        ==========
        group : h5py group object
            Location to store the value
        dict_ : dict
            Dictionary of object(s) to store

        """
        data = dict()
        for key in dict_.keys():
            if isinstance(dict_[key], dict):
                data[key] = self._putvals(dict_[key])
                #sub = group.create_group(key)
                #self._putvals(sub, dict_[key])
            else:
                data[key] = self._putval(dict_[key])
                #self._putval(group, key, dict_[key])
        return data
        
    def _putval(self, data): #group, name, data):
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
        
        # rules: bool - int
        #        None - NaN
        #        set - list
        #        list with string - np.array, dtype=np.object
        #        numpy String, Unicode, or Buffer - dtype=np.object
        #        otherwise, pass as is
        if data is None:
            data = np.NaN
        if isinstance(data, set):
            data = list(data)
        '''
        if isinstance(data, np.ndarray):
            if data.dtype.str == '|O4':
                raise Oct2PyError('not implemented before')
        '''
        if isinstance(data, list):
            if self.str_in_list(data):
                '''
                for item in data:
                    if isinstance(item, list):
                        raise Oct2PyError('not implemented before')
                    if not isinstance(item, str):
                        raise Oct2PyError('not implemented before')
                '''
                data = np.array(data, dtype=np.object)
        if isinstance(data, str) or isinstance(data, unicode):
            return data
        try:
            data = np.array(data)
        except ValueError as err:
            raise Oct2PyError(err)
        dstr = data.dtype.str
        if dstr == '|b1':
            data = data.astype(np.int32)
        elif dstr == '<m8[us]' or dstr == '<M8[us]':
            data = data.astype(np.uint64)
        elif '|S' in dstr or '<U' in dstr:
            data = data.astype(np.object)
            '''
            if len(data.shape) > 1:
                raise Oct2PyError('not implemented before')
            '''
        if '<c' in dstr and np.alltrue(data.imag == 0):
            data.imag = 1e-6
        if dstr in ['<f12', 'c16', '<c24', '|V4']:
            # TODO: implement objects
            raise Oct2PyError('Datatype not supported: %s' % data.dtype)
        return data

    def str_in_list(self, list_):
        for item in list_:
            if isinstance(item, str):
                return True
            elif isinstance(item, list):
                if self.str_in_list(item):
                    return True
