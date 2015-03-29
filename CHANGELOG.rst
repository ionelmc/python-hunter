
Changelog
=========

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
