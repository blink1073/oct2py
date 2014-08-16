***********************
Examples
***********************

OctaveMagic
==========================
Oct2Py provides a plugin for IPython to bring Octave to the IPython prompt or the
IPython Notebook_.

.. _Notebook: http://nbviewer.ipython.org/github/blink1073/oct2py/blob/master/example/octavemagic_extension.ipynb?create=1


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
   [array([[ 1.,  2.],
          [ 3.,  4.]]),
    dtype('float64'),
    array([[ 1.,  2.],
          [ 3.,  4.]]),
    'double',
    dtype('float64')]



Test Datatypes
---------------

test_datatypes.m
+++++++++++++++++

::

  function test = test_datatypes()
    % Test of returning a structure with multiple
    % nesting and multiple return types

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
    test.num.complex_matrix = (1 + 1j) * rand([2 2])

    % misc
    test.num.inf = inf
    test.num.NaN = NaN
    test.num.matrix = [1 2; 3 4]
    test.num.vector = [1 2 3 4]
    test.num.column_vector = [1;2;3;4]
    test.num.matrix3d = rand([2 3 4])
    test.num.matrix5d = rand(1,2,3,4,5)

    %%%%%%%%%%%%%%%
    % logical type
    test.logical = [10 20 30 40 50] > 30

    %%%%%%%%%%%%%%%
    % string types
    test.string.basic = 'spam'
    test.string.char_array = {'spam', 'eggs'; 'foo ', 'bar '}
    test.string.cell_array = {'spam', 'eggs'}

    %%%%%%%%%%%%%%%
    % struct types
    test.struct.array(1).name = 'Sharon'
    test.struct.array(1).age = 31
    test.struct.array(2).name = 'Bill'
    test.struct.array(2).age = 42

    %%%%%%%%%%%%%%%
    % cell array types
    test.cell.vector = {'spam', 4.0, [1 2 3]}
    test.cell.matrix = {'Bob', 40; 'Pam', 41}

Python Session
+++++++++++++++

::

   >>> from oct2py import octave
   >>> out = octave.test_dataypes()
   >>> import pprint
   >>> pprint.pprint(out)
   {u'cell': {u'matrix': [['Bob', 'Pam'], [40.0, 41.0]],
              u'vector': ['spam', 4.0, array([[ 1.,  2.,  3.]])]},
    u'logical': array([[0, 0, 0, 1, 1]]),
    u'num': {u'NaN': nan,
             u'column_vector': array([[ 1.],
          [ 2.],
          [ 3.],
          [ 4.]]),
             u'complex': (3+1j),
             u'complex_matrix': array([[ 0.29801132+0.29801132j,  0.25385592+0.25385592j],
          [ 0.36628765+0.36628765j,  0.17222843+0.17222843j]]),
             u'float32': 3.1415927,
             u'float64': 3.1415926535897931,
             u'inf': inf,
             u'int': {u'int16': -32768,
                      u'int32': -2147483648,
                      u'int64': -9223372036854775808,
                      u'int8': -128,
                      u'uint16': 65535,
                      u'uint32': 4294967295,
                      u'uint64': 18446744073709551615,
                      u'uint8': 255},
             u'matrix': array([[ 1.,  2.],
          [ 3.,  4.]]),
          u'matrix3d': array([[[ 0.37748504,  0.42576504,  0.33770276,  0.28353423],
           [ 0.07772849,  0.79317342,  0.35633704,  0.84392906],
           [ 0.27743843,  0.58173155,  0.60478932,  0.15784762]],

          [[ 0.61831316,  0.52826816,  0.2561059 ,  0.69882897],
           [ 0.78915391,  0.55164477,  0.34382527,  0.23743691],
           [ 0.7984285 ,  0.13977171,  0.77679021,  0.22355376]]]),
             u'matrix5d': array([[[[[ 0.87245616,  0.3935346 ,  0.00509518,  0.18260647,  0.2328523 ],
             [ 0.57790841,  0.26083328,  0.82910847,  0.79100768,  0.111686  ],
             [ 0.01399121,  0.80096565,  0.50399158,  0.51631872,  0.07292035],
             [ 0.59993558,  0.62226338,  0.26245502,  0.71373283,  0.54863195]],

            [[ 0.47438503,  0.17510892,  0.31801117,  0.09766319,  0.72427364],
             [ 0.02762037,  0.73835099,  0.6464369 ,  0.59452631,  0.26695231],
             [ 0.01843247,  0.10938661,  0.68805356,  0.43229338,  0.84202539],
             [ 0.77406571,  0.21564875,  0.6492912 ,  0.18763039,  0.02976736]],

            [[ 0.32019185,  0.67178221,  0.33481521,  0.39093148,  0.51177757],
             [ 0.59023927,  0.91152032,  0.26690269,  0.46438787,  0.02999184],
             [ 0.08864962,  0.97042015,  0.10310935,  0.12789306,  0.71532619],
             [ 0.19870871,  0.14683877,  0.0367708 ,  0.96534334,  0.04710378]]],


           [[[ 0.97058297,  0.12706106,  0.05109758,  0.16347541,  0.88931781],
             [ 0.43036654,  0.97654587,  0.99862712,  0.33365358,  0.74330177],
             [ 0.41980651,  0.74997277,  0.9978432 ,  0.44787774,  0.60519502],
             [ 0.94386177,  0.12320678,  0.01164074,  0.34409676,  0.34135462]],

            [[ 0.92895971,  0.81883047,  0.27796085,  0.9303487 ,  0.01020294],
             [ 0.30430039,  0.74434446,  0.3828099 ,  0.15817473,  0.74870604],
             [ 0.82601961,  0.28806172,  0.75975623,  0.76901488,  0.06666695],
             [ 0.58065392,  0.96855147,  0.7603041 ,  0.98177511,  0.59357169]],

            [[ 0.86808738,  0.89797971,  0.16175654,  0.93365793,  0.25343561],
             [ 0.25567182,  0.75436271,  0.94137345,  0.04822251,  0.69818659],
             [ 0.18410575,  0.07060479,  0.20660155,  0.06567875,  0.83880553],
             [ 0.61876976,  0.64932156,  0.21524418,  0.99559647,  0.34971336]]]]]),
             u'vector': array([[ 1.,  2.,  3.,  4.]])},
    u'string': {u'basic': 'spam',
                u'cell_array': ['spam', 'eggs'],
                u'char_array': [['spam', 'foo '], ['eggs', 'bar ']]},
    u'struct': {u'array': {u'age': [31.0, 42.0], u'name': ['Sharon', 'Bill']}}}

