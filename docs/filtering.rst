=========
Filtering
=========

A list of all the keyword filters that :obj:`hunter.trace` or :obj:`hunter.Q` accept:

* ``arg`` - you probably don't care about this - it may have a value for return/exception events
* ``builtin`` (`bool`) - ``True`` if function is a builtin function
* ``calls`` (`int`) - a call counter, you can use it to limit output by using a ``lt`` operator
* ``depth`` (`int`) - call depth, starts from 0, increases for call events and decreases for returns
* ``filename`` (`str`)
* ``fullsource`` (`str`) - sourcecode for the executed lines (may be multiple lines in some situations)
* ``function`` (`str`) -  function name
* ``globals`` (`dict`) - global variables
* ``instruction`` (`int` or `str`, depending on Python version) - current executed bytecode,
  see :ref:`silenced-exception-runtime-analysis` for example usage
* ``kind`` (`str`) - one of 'call', 'exception', 'line' or 'return'
* ``lineno`` (`int`)
* ``locals`` (`dict`) - local variables
* ``module`` (`str`) -  dotted module
* ``source`` (`str`) - sourcecode for the executed line
* ``stdlib`` (`bool`) - ``True`` if module is from stdlib
* ``threadid`` (`int`)
* ``threadname`` (`str`) - whatever `threading.Thread.name <https://docs.python.org/3/library/threading.html#threading.Thread.name>`_
  returns

You can append operators to the above filters. Note that some of of the filters won't work well with the `bool` or `int` types.

* ``contains`` - works best with `str`, for
  example ``module_contains='foobar'`` translates to ``'foobar' in event.module``
* ``has`` - alias for ``contains``
* ``endswith`` - works best with `str`, for
  example ``module_endswith='foobar'`` translates to ``event.module.endswith('foobar')``. You can also pass in a iterable,
  example ``module_endswith=('foo', 'bar')`` is `acceptable <https://docs.python.org/3/library/stdtypes.html#str.startswith>`_
* ``ew`` - alias for ``endswith``
* ``gt`` - works best with `int`, for example ``lineno_gt=100`` translates to ``event.lineno > 100``
* ``gte`` - works best with `int`, for example ``lineno_gte=100`` translates to ``event.lineno >= 100``
* ``in`` - a membership test, for example ``module_in=('foo', 'bar')`` translates to ``event.module in ('foo', 'bar')``. You can use any
  iterable, for example ``module_in='foo bar'`` translates to ``event.module in 'foo bar'``, and that would probably have the same result
  as the first example
* ``lt`` - works best with `int`, for example ``calls_lt=100`` translates to ``event.calls < 100``
* ``lte`` - works best with `int`, for example ``depth_lte=100`` translates to ``event.depth <= 100``
* ``regex`` - works best with `str`, for
  example ``module_regex=r'(test|test.*)\b'`` translates to ``re.match(r'(test|test.*)\b', event.module)``
* ``rx`` - alias for ``regex``
* ``startswith`` - works best with `str`, for
  example ``module_startswith='foobar'`` translates to ``event.module.startswith('foobar')``. You can also pass in a iterable,
  example ``module_startswith=('foo', 'bar')`` is `acceptable <https://docs.python.org/3/library/stdtypes.html#str.startswith>`_
* ``sw`` - alias for ``startswith``

Notes:

* you can also use double underscore (if you're too used to Django query lookups), eg: ``module__has='foobar'`` is acceptable
* there's nothing smart going on for the dots in module names so sometimes you might need to account for said dots:

  * ``module_sw='foo'`` will match ``"foo.bar"`` and ``"foobar"`` - if you want to avoid matchin the later you could do either of:

    * ``Q(module='foo')|Q(module_sw='foo.')``
    * ``Q(module_rx=r'foo($|\.)')`` - but this might cost you in speed
    * ``Q(filename_sw='/path/to/foo/')`` - probably the fastest
    * ``Q(filename_has='/foo/')`` - avoids putting in the full path but might match unwanted paths
