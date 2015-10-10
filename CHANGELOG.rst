
Changelog
=========

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
