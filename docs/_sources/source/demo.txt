
***********
Demo
***********

Output of Oct2Py demo script, showing most of the features of the library.  Note that the two
plot commands will generate an interactive plot in the actual demo.
To run interactively:


.. code-block:: python

   >>> import oct2py
   >>> oct2py.demo()

    >>> import numpy as np
    >>> from oct2py import Oct2Py
    >>> oc = Oct2Py()
    >>> # basic commands
    >>> print(oc.abs(-1))
    1
    >>> print(oc.upper('xyz'))
    XYZ
    >>> # plotting
    >>> oc.plot([1,2,3],'-o')
    Press Enter to continue...

.. image:: static/plot.png

.. code-block:: python

   >>> xx = np.arange(-2*np.pi, 2*np.pi, 0.2)
   >>> oc.surf(np.subtract.outer(np.sin(xx), np.cos(xx)))
   Press Enter to continue...

.. image:: static/surf.png

.. code-block:: python

    >>> # getting help
    >>> help(oc.svd)
    Help on function svd in module oct2py.session:
    
    svd(*args, **kwargs)
        `svd' is a function from the file c:\Program Files\Octave-3.6.2\lib\octave\3.6.2\oct\i686-pc-mingw32\svd.oct
        
         -- Loadable Function: S = svd (A)
         -- Loadable Function: [U, S, V] = svd (A)
         -- Loadable Function: [U, S, V] = svd (A, ECON)
             Compute the singular value decomposition of A
        
                  A = U*S*V'
        
             The function `svd' normally returns only the vector of singular
             values.  When called with three return values, it computes U, S,
             and V.  For example,
        
                  svd (hilb (3))
        
             returns
        
                  ans =
        
                   1.4083189
                   0.1223271
                   0.0026873
        
             and
        
                  [u, s, v] = svd (hilb (3))
        
             returns
        
                  u =
        
                   -0.82704   0.54745   0.12766
                   -0.45986  -0.52829  -0.71375
                   -0.32330  -0.64901   0.68867
        
                  s =
        
                   1.40832  0.00000  0.00000
                   0.00000  0.12233  0.00000
                   0.00000  0.00000  0.00269
        
                  v =
        
                   -0.82704   0.54745   0.12766
                   -0.45986  -0.52829  -0.71375
                   -0.32330  -0.64901   0.68867
        
             If given a second argument, `svd' returns an economy-sized
             decomposition, eliminating the unnecessary rows or columns of U or
             V.
        
             See also: svd_driver, svds, eig
        
        
        
        Additional help for built-in functions and operators is
        available in the on-line version of the manual.  Use the command
        `doc <topic>' to search the manual index.
        
        Help and information about Octave is also available on the WWW
        at http://www.octave.org and via the help@octave.org
        mailing list.
    
    >>> # single vs. multiple return values
    >>> print(oc.svd(np.array([[1,2], [1,3]])))
    [[ 3.86432845]
     [ 0.25877718]]
    >>> U, S, V = oc.svd([[1,2], [1,3]])
    >>> print(U, S, V)
    (array([[-0.57604844, -0.81741556],
           [-0.81741556,  0.57604844]]), array([[ 3.86432845,  0.        ],
           [ 0.        ,  0.25877718]]), array([[-0.36059668, -0.93272184],
           [-0.93272184,  0.36059668]]))
    >>> # low level constructs
    >>> oc.run("y=ones(3,3)")
    >>> print(oc.get("y"))
    [[ 1.  1.  1.]
     [ 1.  1.  1.]
     [ 1.  1.  1.]]
    >>> oc.run("x=zeros(3,3)", verbose=True)
    
    x=zeros(3,3)
    
    x =
    
            0        0        0
            0        0        0
            0        0        0
    
    >>> x = oc.call('rand', 1, 4)
    >>> print(x)
    [[ 0.10852044  0.72508862  0.63270314  0.54310462]]
    >>> t = oc.call('rand', 1, 2, verbose=True)
    load c:\users\silves~1\appdata\local\temp\tmpvyaxwv.mat "A__" "B__"
    [a__] = rand(A__, B__)
    save "-v6" c:\users\silves~1\appdata\local\temp\tmplhftfv.mat "a__"
    a__ =
    
      0.42867  0.92885
    
    >>> y = np.zeros((3,3))
    >>> oc.put('y', y)
    >>> print(oc.get('y'))
    [[ 0.  0.  0.]
     [ 0.  0.  0.]
     [ 0.  0.  0.]]
    >>> from oct2py import Struct
    >>> y = Struct()
    >>> y.b = 'spam'
    >>> y.c.d = 'eggs'
    >>> print(y.c['d'])
    eggs
    >>> print(y)
    {'c': {'d': 'eggs'}, 'b': 'spam'}
    ********************
    DEMO COMPLETE!
