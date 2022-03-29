***********************
Conversions
***********************

Python to Octave Types
----------------------

Shows the round-trip data types, originating in Python.
Lists and sets will be converted to a numeric array if possible, falling back 
on cells.  If an Octave cell consisting of numbers is desired, use a tuple.
Cell, Struct, StructArray are Oct2Py convenience classes.

=============   ===============   ===============
Python          Octave            Python
=============   ===============   ===============
int             int32             np.int32
long            int64             np.int64
float           double            np.float64
complex         double            np.complex128
str             char              unicode
unicode         cell              unicode
bool            logical           np.bool
None            nan               np.nan
dict            struct            Struct
tuple           cell              Cell
list            array or cell     ndarray or Cell
set             array or cell     ndarray or Cell
Struct          struct            Struct
StructArray     struct array      StructArray
=============   ===============   ===============


Numpy to Octave Types
---------------------

Note that when `convert_to_float` is set (default is True), 
integer types are converted to floating point before sending them
to Octave.

=============   ============   =============
Numpy           Octave         Numpy
=============   ============   =============
np.int8         int8           np.int8
np.int16        int16          np.int16
np.int32        int32          np.int32
np.int64        int64          np.int64
np.uint8        uint8          np.uint8
np.uint16       uint16         np.uint16
np.uint32       uint32         np.uint32
np.uint64       uint64         np.uint64
np.float16      double         np.float64
np.float32      single         np.float32
np.float64      double         np.float64
np.float128     double         np.float64
np.double       double         np.float64
np.complex64    double         np.complex64
np.complex128   double         np.complex128
np.complex256   double         np.complex128
np.bool         logical        bool
np.str          cell           list
np.object       cell           list
sparse          sparse         sparse
recarray        struct array   StructArray
=============   ============   =============


Octave to Python Types
----------------------

These are handled unambiguously.  The only known data type that
is not transferable is a function pointer, since Octave cannot
save them to the v6 MAT file format.

===================  ======================
Octave               Python
===================  ======================
array                ndarray
cell                 Cell
struct               Struct
struct array         StructArray
logical              ndarray (of uint8)
sparse               sparse
user defined object  Oct2Py object pointer
===================  ======================
