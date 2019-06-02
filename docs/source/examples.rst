***********************
Examples
***********************

OctaveMagic
==========================
Oct2Py provides a plugin for IPython to bring Octave to the IPython prompt or the
IPython Notebook_.

.. _Notebook: http://nbviewer.jupyter.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1


M-File Examples
===============


M-files in the directory where oct2py was initialized, or those in the
Octave path, can be called like any other Octave function.
To explicitly add to the path, use::

   >>> from oct2py import octave
   >>> octave.addpath('/path/to/directory')

to add the directory in which your m-file is located to Octave's path.


Roundtrip
---------

roundtrip.m
+++++++++++

::

  function [x, class] = roundtrip(y)
     % returns the input variable and its class
     x = y
     class = class(x)


Python Session
++++++++++++++

::

   >>> from oct2py import octave
   >>> import numpy as np
   >>> x = np.array([[1, 2], [3, 4]], dtype=float)
   >>> out, oclass = octave.roundtrip(x)
   >>> import pprint
   >>> pprint.pprint([x, x.dtype, out, oclass, out.dtype])
   [array([[1., 2.],
         [3., 4.]]),
   dtype('float64'),
   array([1., 2.]),
   array([3., 4.]),
   dtype('<f8')]



Test Datatypes
---------------

test_datatypes.m
+++++++++++++++++

::

   function test = test_datatypes()
   % Test of returning a structure with multiple
   % nesting and multiple return types
   % Add a UTF char for test: 猫

   %%%%%%%%%%%%%%%
   % numeric types
   % integers
   test.num.int.int8 = int8(-2^7);
   test.num.int.int16 = int16(-2^15);
   test.num.int.int32 = int32(-2^31);
   test.num.int.int64 = int64(-2^63);
   test.num.int.uint8 = uint8(2^8-1);
   test.num.int.uint16 = uint16(2^16-1);
   test.num.int.uint32 = uint32(2^32-1);
   test.num.int.uint64 = uint64(2^64-1);

   %floats
   test.num.float32 = single(pi);
   test.num.float64 = double(pi);
   test.num.complex = 3 + 1j;
   test.num.complex_matrix = (1.2 + 1.1j) * magic(3);

   % misc
   test.num.inf = inf;
   test.num.NaN = NaN;
   test.num.matrix = [1 2; 3 4];
   test.num.vector = [1 2 3 4];
   test.num.column_vector = [1;2;3;4];
   test.num.matrix3d = ones([2 3 4]) * pi;
   test.num.matrix5d = ones(1,2,3,4,5) * pi;

   %%%%%%%%%%%%%%%
   % logical type
   test.logical = [10 20 30 40 50] > 30;


   %%%%%%%%%%%%%%%%
   % sparse type
   test.sparse = speye(10);

   %%%%%%%%%%%%%%%
   % string types
   test.string.basic = 'spam';
   test.string.cell = {'1'};
   test.string.char_array = ['Thomas R. Lee'; ...
                           'Sr. Developer'; ...
                           'SFTware Corp.'];
   test.string.cell_array = {'spam', 'eggs'};

   %%%%%%%%%%%%%%%%
   % User defined object
   test.object = polynomial([1,2,3]);

   %%%%%%%%%%%%%%%
   % struct array of shape 3x1
   test.struct_vector = [struct('key','a'); struct('key','b'); struct('key','c')];

   %%%%%%%%%%%%%%%
   % struct array of shape 1x2
   test.struct_array(1).name = 'Sharon';
   test.struct_array(1).age = 31;
   test.struct_array(2).name = 'Bill';
   test.struct_array(2).age = 42;

   %%%%%%%%%%%%%%%
   % cell array types
   test.cell.vector = {'spam', 4.0, [1 2 3]};
   test.cell.matrix = {'Bob', 40; 'Pam', 41};
   test.cell.scalar = {1.8};
   test.cell.string = {'1'};
   test.cell.string_array = {'1', '2'};
   test.cell.empty = cell(3,4,2);
   test.cell.array = {[0.4194 0.3629 -0.0000;
                     0.0376 0.3306 0.0000;
                     0 0 1.0000],
                     [0.5645 -0.2903 0;
                     0.0699 0.1855 0.0000;
                     0.8500 0.8250 1.0000]};

   %%%%%%%%%%%%%%
   % nest all of the above.
   test.nested = test;

   end


Python Session
+++++++++++++++

::

   >>> from oct2py import octave
   >>> out = octave.test_dataypes()
   >>> import pprint
   >>> pprint.pprint(out)
   {'cell': {'array': Cell([array([[ 0.4194,  0.3629, -0.    ],
         [ 0.0376,  0.3306,  0.    ],
         [ 0.    ,  0.    ,  1.    ]]),
         array([[ 0.5645, -0.2903,  0.    ],
         [ 0.0699,  0.1855,  0.    ],
         [ 0.85  ,  0.825 ,  1.    ]])]),
            'empty': Cell([[[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]],

         [[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]],

         [[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]]]),
            'matrix': Cell([['Bob', 40.0],
         ['Pam', 41.0]]),
            'scalar': Cell([1.8]),
            'string': Cell(['1']),
            'string_array': Cell([['1', '2']]),
            'vector': Cell([['spam', 4.0, array([[1., 2., 3.]])]])},
   'logical': array([[0, 0, 0, 1, 1]], dtype=uint8),
   'nested': {'cell': {'array': Cell([array([[ 0.4194,  0.3629, -0.    ],
         [ 0.0376,  0.3306,  0.    ],
         [ 0.    ,  0.    ,  1.    ]]),
         array([[ 0.5645, -0.2903,  0.    ],
         [ 0.0699,  0.1855,  0.    ],
         [ 0.85  ,  0.825 ,  1.    ]])]),
                        'empty': Cell([[[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]],

         [[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]],

         [[list([]), list([])],
         [list([]), list([])],
         [list([]), list([])],
         [list([]), list([])]]]),
                        'matrix': Cell([['Bob', 40.0],
         ['Pam', 41.0]]),
                        'scalar': Cell([1.8]),
                        'string': Cell(['1']),
                        'string_array': Cell([['1', '2']]),
                        'vector': Cell([['spam', 4.0, array([[1., 2., 3.]])]])},
               'logical': array([[0, 0, 0, 1, 1]], dtype=uint8),
               'num': {'NaN': nan,
                     'column_vector': array([[1.],
         [2.],
         [3.],
         [4.]]),
                     'complex': (3+1j),
                     'complex_matrix': array([[ 9.6+8.8j,  1.2+1.1j,  7.2+6.6j],
         [ 3.6+3.3j,  6. +5.5j,  8.4+7.7j],
         [ 4.8+4.4j, 10.8+9.9j,  2.4+2.2j]]),
                     'float32': 3.1415927410125732,
                     'float64': 3.141592653589793,
                     'inf': inf,
                     'int': {'int16': -32768,
                              'int32': -2147483648,
                              'int64': -9223372036854775808,
                              'int8': -128,
                              'uint16': 65535,
                              'uint32': 4294967295,
                              'uint64': 18446744073709551615,
                              'uint8': 255},
                     'matrix': array([[1., 2.],
         [3., 4.]]),
                     'matrix3d': array([[[3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265]],

         [[3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265]]]),
                     'matrix5d': array([[[[[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]]],


         [[[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]]]]]),
                     'vector': array([[1., 2., 3., 4.]])},
               'object': <oct2py.dynamic.polynomial object at 0x0000027C56C16EB8>,
               'sparse': <10x10 sparse matrix of type '<class 'numpy.float64'>'
         with 10 stored elements in Compressed Sparse Column format>,
               'string': {'basic': 'spam',
                        'cell': Cell(['1']),
                        'cell_array': Cell([['spam', 'eggs']]),
                        'char_array': array(['Thomas R. Lee', 'Sr. Developer', 'SFTware Corp.'], dtype='<U13')},
               'struct_array': 1x2 StructArray containing the fields:
      name
      age,
               'struct_vector': 3x1 StructArray containing the fields:
      key},
   'num': {'NaN': nan,
            'column_vector': array([[1.],
         [2.],
         [3.],
         [4.]]),
            'complex': (3+1j),
            'complex_matrix': array([[ 9.6+8.8j,  1.2+1.1j,  7.2+6.6j],
         [ 3.6+3.3j,  6. +5.5j,  8.4+7.7j],
         [ 4.8+4.4j, 10.8+9.9j,  2.4+2.2j]]),
            'float32': 3.1415927410125732,
            'float64': 3.141592653589793,
            'inf': inf,
            'int': {'int16': -32768,
                  'int32': -2147483648,
                  'int64': -9223372036854775808,
                  'int8': -128,
                  'uint16': 65535,
                  'uint32': 4294967295,
                  'uint64': 18446744073709551615,
                  'uint8': 255},
            'matrix': array([[1., 2.],
         [3., 4.]]),
            'matrix3d': array([[[3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265]],

         [[3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265],
         [3.14159265, 3.14159265, 3.14159265, 3.14159265]]]),
            'matrix5d': array([[[[[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]]],


         [[[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]],

            [[3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265],
            [3.14159265, 3.14159265, 3.14159265, 3.14159265, 3.14159265]]]]]),
            'vector': array([[1., 2., 3., 4.]])},
   'object': <oct2py.dynamic.polynomial object at 0x0000027C56BB3B38>,
   'sparse': <10x10 sparse matrix of type '<class 'numpy.float64'>'
         with 10 stored elements in Compressed Sparse Column format>,
   'string': {'basic': 'spam',
               'cell': Cell(['1']),
               'cell_array': Cell([['spam', 'eggs']]),
               'char_array': array(['Thomas R. Lee', 'Sr. Developer', 'SFTware Corp.'], dtype='<U13')},
   'struct_array': 1x2 StructArray containing the fields:
      name
      age,
   'struct_vector': 3x1 StructArray containing the fields:
      key}
