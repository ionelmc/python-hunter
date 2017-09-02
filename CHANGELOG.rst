
Changelog
=========

2.0.0 (2017-09-02)
------------------

* Added the ``Event.count`` and ``Event.calls`` attributes.
* Added the ``lt``/``lte``/``gt``/``gte`` lookups.
* Added convenience aliases for ``startswith`` (``sw``), ``endswith`` (``ew``) and ``regex`` (``rx``).
* Added a convenience ``hunter.wrap`` decorator to start tracing around a function.
* Added support for remote tracing (with two backends: `manhole <https://pypi.python.org/pypi/manhole>`__ and GDB) via
  the ``hunter-trace`` bin. Note: **Windows is NOT SUPPORTED**.
* Changed the default action to ``CallPrinter``. You'll need to use ``action=CodePrinter`` if you want the old output.

1.4.1 (2016-09-24)
------------------

* Fix support for getting sources for Cython module (it was broken on Windows and Python3.5+).

1.4.0 (2016-09-24)
------------------

* Added support for tracing Cython modules (`#30 <https://github.com/ionelmc/python-hunter/issues/30>`_). A
  `# cython: linetrace=True` stanza or equivalent is required in Cython modules for this to work.

1.3.0 (2016-04-14)
------------------

* Added ``Event.thread``.
* Added ``Event.threadid`` and ``Event.threadname`` (available for filtering with ``Q`` objects).
* Added ``threading_support`` argument to ``hunter.trace``: makes new threads be traced and changes action output to include
  threadname.
* Added support for using `pdb++ <https://pypi.python.org/pypi/pdbpp>`_ in the ``Debugger`` action.
* Added support for using `manhole <https://pypi.python.org/pypi/manhole>`_ via a new ``Manhole`` action.
* Made the ``handler`` a public but readonly property of ``Tracer`` objects.


1.2.2 (2016-01-28)
------------------

* Fix broken import. Require `fields>=4.0`.
* Simplify a string check in Cython code.

1.2.1 (2016-01-27)
------------------

* Fix "KeyError: 'normal'" bug in ``CallPrinter``. Create the NO_COLORS dict from the COLOR dicts. Some keys were missing.

1.2.0 (2016-01-24)
------------------

* Fixed printouts of objects that return very large string in ``__repr__()``. Trimmed to 512. Configurable in actions with the
  ``repr_limit`` option.
* Improved validation of ``VarsPrinter``'s initializer.
* Added a ``CallPrinter`` action.

1.1.0 (2016-01-21)
------------------

* Implemented a destructor (``__dealloc__``) for the Cython tracer.
* Improved the restoring of the previous tracer in the Cython tracer (use ``PyEval_SetTrace``) directly.
* Removed ``tracer`` as an allowed filtering argument in ``hunter.Query``.
* Add basic validation (must be callable) for positional arguments and actions passed into ``hunter.Q``. Closes
  `#23 <https://github.com/ionelmc/python-hunter/issues/23>`_.
* Fixed ``stdlib`` checks (wasn't very reliable). Closes `#24 <https://github.com/ionelmc/python-hunter/issues/24>`_.

1.0.2 (2016-01-05)
------------------

* Fixed missing import in ``setup.py``.

1.0.1 (2015-12-24)
------------------

* Fix a compile issue with the MSVC compiler (seems it don't like the inline option on the ``fast_When_call``).

1.0.0 (2015-12-24)
------------------

* Implemented fast tracer and query objects in Cython. **MAY BE BACKWARDS INCOMPATIBLE**

  To force using the old pure-python implementation set the ``PUREPYTHONHUNTER`` environment variable to non-empty value.
* Added filtering operators: ``contains``, ``startswith``, ``endswith`` and ``in``. Examples:

  * ``Q(module_startswith='foo'`` will match events from ``foo``, ``foo.bar`` and ``foobar``.
  * ``Q(module_startswith=['foo', 'bar']`` will match events from ``foo``, ``foo.bar``, ``foobar``, ``bar``, ``bar.foo`` and ``baroo`` .
  * ``Q(module_endswith='bar'`` will match events from ``foo.bar`` and ``foobar``.
  * ``Q(module_contains='ip'`` will match events from ``lipsum``.
  * ``Q(module_in=['foo', 'bar']`` will match events from ``foo`` and ``bar``.
  * ``Q(module_regex=r"(re|sre.*)\b") will match events from ``re``, ``re.foobar``, ``srefoobar`` but not from ``repr``.

* Removed the ``merge`` option. Now when you call ``hunter.trace(...)`` multiple times only the last one is active.
  **BACKWARDS INCOMPATIBLE**
* Remove the `previous_tracer handling`. Now when you call ``hunter.trace(...)`` the previous tracer (whatever was in
  ``sys.gettrace()``) is disabled and restored when ``hunter.stop()`` is called. **BACKWARDS INCOMPATIBLE**
* Fixed ``CodePrinter`` to show module name if it fails to get any sources.

0.6.0 (2015-10-10)
------------------

* Added a ``clear_env_var`` option on the tracer (disables tracing in subprocess).
* Added ``force_colors`` option on :class:`VarsPrinter` and :class:`CodePrinter`.
* Allowed setting the `stream` to a file name (option on :class:`VarsPrinter` and :class:`CodePrinter`).
* Bumped up the filename alignment to 40 cols.
* If not merging then `self` is not kept as a previous tracer anymore.
  Closes `#16 <https://github.com/ionelmc/python-hunter/issues/16>`_.
* Fixed handling in VarsPrinter: properly print eval errors and don't try to show anything if there's an AttributeError.
  Closes `#18 <https://github.com/ionelmc/python-hunter/issues/18>`_.
* Added a ``stdlib`` boolean flag (for filtering purposes).
  Closes `#15 <https://github.com/ionelmc/python-hunter/issues/15>`_.
* Fixed broken frames that have "None" for filename or module (so they can still be treated as strings).
* Corrected output files in the ``install_lib`` command so that pip can uninstall the pth file.
  This only works when it's installed with pip (sadly, ``setup.py install/develop`` and ``pip install -e`` will still
  leave pth garbage on ``pip uninstall hunter``).

0.5.1 (2015-04-15)
------------------

* Fixed :obj:`Event.globals` to actually be the dict of global vars (it was just the locals).

0.5.0 (2015-04-06)
------------------

* Fixed :class:`And` and :class:`Or` "single argument unwrapping".
* Implemented predicate compression. Example: ``Or(Or(a, b), c)`` is converted to ``Or(a, b, c)``.
* Renamed the :obj:`Event.source` to :obj:`Event.fullsource`.
* Added :obj:`Event.source` that doesn't do any fancy sourcecode tokenization.
* Fixed :obj:`Event.fullsource` return value for situations where the tokenizer would fail.
* Made the print function available in the ``PYTHONHUNTER`` env var payload.
* Added a __repr__ for :class:`Event`.

0.4.0 (2015-03-29)
------------------

* Disabled colors for Jython (contributed by Claudiu Popa in `#12 <https://github.com/ionelmc/python-hunter/pull/12>`_).
* Test suite fixes for Windows (contributed by Claudiu Popa in `#11 <https://github.com/ionelmc/python-hunter/pull/11>`_).
* Added an introduction section in the docs.
* Implemented a prettier fallback for when no sources are available for that frame.
* Implemented fixups in cases where you use action classes as a predicates.

0.3.1 (2015-03-29)
------------------

* Forgot to merge some commits ...

0.3.0 (2015-03-29)
------------------

* Added handling for internal repr failures.
* Fixed issues with displaying code that has non-ascii characters.
* Implemented better display for ``call`` frames so that when a function has decorators the
  function definition is shown (instead of just the first decorator).
  See: `#8 <https://github.com/ionelmc/python-hunter/issues/8>`_.

0.2.1 (2015-03-28)
------------------

* Added missing color entry for exception events.
* Added :obj:`Event.line` property. It returns the source code for the line being run.

0.2.0 (2015-03-27)
------------------

* Added color support (and ``colorama`` as dependency).
* Added support for expressions in :class:`VarsPrinter`.
* Breaking changes:

  * Renamed ``F`` to :obj:`Q`. And :obj:`Q` is now just a convenience wrapper for :class:`Query`.
  * Renamed the ``PYTHON_HUNTER`` env variable to ``PYTHONHUNTER``.
  * Changed :class:`When` to take positional arguments.
  * Changed output to show 2 path components (still not configurable).
  * Changed :class:`VarsPrinter` to take positional arguments for the names.
* Improved error reporting for env variable activation (``PYTHONHUNTER``).
* Fixed env var activator (the ``.pth`` file) installation with ``setup.py install`` (the "egg installs") and
  ``setup.py develop``/``pip install -e`` (the "egg links").

0.1.0 (2015-03-22)
------------------

* First release on PyPI.
