***********************
Conversions
***********************

Python to Octave Types
----------------------

Shows the round-trip data types.  Note that when `convert_to_float` is 
set (default), integer types are converted to floating point.

=============   ===========    =============
Python          Octave         Python
=============   ===========    =============
int             int32          np.int32
long            int64          np.int64
float           double         np.float64
complex         double         np.complex128
str             char           unicode
unicode         cell           unicode
bool            int32          np.int32
None            double         np.float64
dict            struct         Struct
=============   ===========    =============

Numpy to Octave Types
---------------------

Note that the errors are types that are not implemented.
Note that when `convert_to_float` is 
set (default), integer types are converted to floating point.

=============   ===========    =============
Numpy           Octave         Numpy
=============   ===========    =============
np.int8         int8           np.int8
np.int16        int16          np.int16
np.int32        int32          np.int32
np.int64        int64          np.int64
np.uint8        uint8          np.uint8
np.uint16       uint16         np.uint16
np.uint32       uint32         np.uint32
np.uint64       uint64         np.uint64
np.float16      ERROR          ERROR
np.float32      double         *np.float64*
np.float64      double         np.float64
np.float96      ERROR          ERROR
np.str          char           np.str
np.double       double         *np.float64*
np.complex64    double         *np.complex128*
np.complex128   double         np.complex128
np.complex192   ERROR          ERROR
np.object       cell           list
=============   ===========    =============

Python to Octave Compound Types
-------------------------------

==================   ===========    ===============
Python               Octave         Python
==================   ===========    ===============
list of strings      cell (1-d)     list of strings
list of mixed type   cell           list of mixed type
nested string list   cell           list of strings
tuple of strings     cell           list of strings
nested dict          struct         Struct
set of int32         int32          np.int32
==================   ===========    ===============

Octave to Python Types
----------------------

These are the unique values apart from the Python to Octave lists.

===============  =================
Octave           Python
===============  =================
matrix           ndarray
cell (2-d)       list of lists
cell (scalar)    scalar
cell array       list of lists
struct           Struct
struct (nested)  Struct (nested)
struct array*    Struct (of lists)*
logical          ndarray
===============  =================

::
  
  * One-way trip (cannot be sent back to Octave intact)

