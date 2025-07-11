
Changelog
=========

3.8.0 (2025-07-11)
------------------

* Drop support for Python 3.8.
* Added support for Python 3.13, including freethreading variant (but not really tested, as most of the test suite is singlethreaded).
* Fixed issues with latest Cython release (3.1.2).
* Simplified the `Event.__init__` so doesn't require or accept a Tracer instance anymore to fill in some options.
* Fixed hardcoded python executable in tests.
  Contributed by Steve Kowalik in `#126 <https://github.com/ionelmc/python-hunter/pull/126>`.

3.7.0 (2024-05-02)
------------------

* Drop support for Python 3.7.
* Upgrade linters and refactor various string formatting and other cleanups.
* Upgrade Cython to latest release (3.0.10).
* Linux wheels should be back now.
* Switched docs theme to furo.

3.6.1 (2023-04-26)
------------------

* Added safe repr support for Decimal objects.

3.6.0 (2023-04-25)
------------------

* Added C extension support for Python 3.11. This may come with up to 10% performance hit (depending on use-case) for all Pythons.
  Unfortunately some `compat shims <https://raw.githubusercontent.com/python/pythoncapi_compat/master/pythoncapi_compat.h>`_ are
  now used for getting frame details. This is necessary to be able to work with Python 3.11 and be more future-proof.
* Added safe repr support for ZoneInfo objects.
* C extension files are now prebuilt with Cython 3.0b2.
* Replaced the flake8/isort pre-commit hooks with ruff.
* Disabled editable wheels (`PEP-0662 <https://peps.python.org/pep-0662/>`_) as they don't include the `hunter.pth` file.
  There may be a way to do it but I haven't figured out a way to customize the `editable_wheel` command without a
  very brittle solution glued to setuptools' internals.

3.5.1 (2022-09-27)
------------------

* Fixed breakage in ``hunter-trace`` when Ctrl-C.

3.5.0 (2022-09-11)
------------------

* Add support for generators and coroutines in the :obj:`hunter.wrap` decorator.
* Dropped support for Python 3.6.

3.4.3 (2021-12-15)
------------------

* Removed most of the Python 2 support code.
* Fix some refactoring regression in ``setup.py`` and make the 3.4.x series installable only on Python 3.6 and later.
* Yank 3.4.0, 3.4.1, 3.4.2 releases to avoid install problems on Python 2.7.

3.4.2 (2021-12-15)
------------------

* Fixed CI to properly make win32 wheels.

3.4.1 (2021-12-14)
------------------

* Add support for building a ``pp37.pp38`` tagged wheel
  (basically an universal wheel installable just for those two PyPy versions).

3.4.0 (2021-12-14)
------------------

* Switched CI to GitHub Actions, this has a couple consequences:

  * Support for Python 2.7 is dropped. You can still install it there but it's not tested anymore and
    Python 2 specific handling will be removed at some point.
  * Linux wheels are now provided in `musllinux` and `manylinux2014` variants.
* Extension building is now completely skipped on PyPy.
* A pure but tagged as platform specific wheel is now provided for PyPy (to have fast installs there as well).

3.3.8 (2021-06-23)
------------------

* Fixed CI problem that publishes same type of wheels two times.

3.3.7 (2021-06-23)
------------------

* Fixed a bug with how ``stdlib`` is detected on Windows (at least).

3.3.6 (2021-06-23)
------------------

* Fixed regression from *3.3.4*: ``stdlib`` filter was broken.
* Improved the pth file (``PYTHONHUNTER`` environment variable activation) to use a clean eval environment.
  No bogus variables like ``line`` (from the ``site.py`` machinery) will be available anymore.
* Fixed a bug in ``VarsSnooper`` that would make it fail in rare situation where a double `return` event is emitted.

3.3.5 (2021-06-11)
------------------

* Added support for Python 3.10.
* Added support for ``time`` objects and the ``fold`` option in ``safe_repr``.
* *3.3.4 was skipped cause I messed up the CI.*

3.3.3 (2021-05-04)
------------------

* Fixed tracer still being active for other threads after it was stopped.

  Python unfortunately only allows removing the trace function for the current thread -
  now :obj:`~hunter.tracer.Tracer` will uninstall itself if it's marked as stopped.

  This fixes bogus errors that appear when using ``ipdb`` with
  the :class:`hunter.actions.Debugger` action while thread support is enabled (the default).

3.3.2 (2021-03-25)
------------------

* Changed CI to build Python 3.9 wheels. Python 3.5 no longer tested and wheels no longer built to keep things simple.
* Documentation improvements.

3.3.1 (2020-10-24)
------------------

* Fixed CI/test issues that prevented all of 21 wheels being published.

3.3.0 (2020-10-23)
------------------

* Fixed handling so that :any:`hunter.event.Event.module` is always the ``"?"`` string instead of ``None``.
  Previously it was ``None`` when tracing particularly broken code and broke various predicates.
* Similarly :any:`hunter.event.Event.filename` is now ``"?"`` if there's no filename available.
* Building on the previous changes the actions have simpler code for displaying missing module/filenames.
* Changed :class:`hunter.actions.CallPrinter` so that trace events for builtin functions are displayed differently.
  These events appear when using profile mode (eg: ``trace(profile=True)``).
* Fixed failure that could occur if :any:`hunter.event.Event.module` is an unicode string. Now it's always a regular string.
  *Only applies to Python 2.*
* Fixed argument display when tracing functions with tuple arguments.
  Closes `#88 <https://github.com/ionelmc/python-hunter/issues/88>`_. *Only applies to Python 2.*
* Improved error reporting when internal failures occur. Now some details about the triggering event are logged.

3.2.2 (2020-09-04)
------------------

* Fixed oversight over what value is in :any:`hunter.event.Event.builtin`. Now it's always a boolean, and can be used consistently
  in filters (eg: ``builtin=True,function='getattr'``).

3.2.1 (2020-08-18)
------------------

* Added support for regex, date and datetime in ``safe_repr``.
* Fixed call argument display when positional and keyword arguments are used in :class:`hunter.actions.CallPrinter`.

3.2.0 (2020-08-16)
------------------

* Implemented the :class:`~hunter.actions.StackPrinter` action.
* Implemented the :class:`~hunter.predicates.Backlog` predicate.
  Contributed by Dan Ailenei in `#81 <https://github.com/ionelmc/python-hunter/pull/81>`_.
* Improved contributing section in docs a bit.
  Contributed by Tom Schraitle in `#85 <https://github.com/ionelmc/python-hunter/pull/85>`_.
* Improved filtering performance by avoiding a lot of unnecessary
  ``PyObject_GetAttr`` calls in the Cython implementation of :class:`~hunter.predicates.Backlog`.
* Implemented the :class:`~hunter.actions.ErrorSnooper` action.
* Added support for profiling mode (eg: ``trace(profile=True)``).
  This mode will use ``setprofile`` instead of ``settrace``.
* Added ARM64 wheels and CI.
* Added :any:`hunter.event.Event.instruction` and :any:`hunter.event.Event.builtin` (usable in profile mode).
* Added more cookbook entries.

3.1.3 (2020-02-02)
------------------

* Improved again the stdlib check to handle certain paths better.

3.1.2 (2019-01-19)
------------------

* Really fixed the ``<frozen importlib.something`` stdlib check.

3.1.1 (2019-01-19)
------------------

* Marked all the ``<frozen importlib.something`` files as part of stdlib.

3.1.0 (2019-01-19)
------------------

* Added :class:`~hunter.actions.ErrorSnooper` - an action that detects silenced exceptions.
* Added :func:`~hunter.load_config` and fixed issues with configuration being loaded too late from the ``PYTHONHUNTERCONFIG`` environment
  variable.
* Changed :func:`~hunter.From` helper to automatically move ``depth`` and ``calls`` filters to the predicate (so they filter after
  :class:`~hunter.predicates.From` activates).
* Changed :class:`~hunter.predicates.From` to pass a copy of event to the predicate.
  The copy will have the ``depth`` and ``calls`` attributes adjusted to the point where :class:`~hunter.predicates.From` activated.
* Fixed a bunch of inconsistencies and bugs when using ``&`` and ``|`` operators with predicates.
* Fixed a bunch of broken fields on :meth:`detached events <hunter.event.Event.detach>`
  (:attr:`~hunter.event.Event.function_object` and :attr:`~hunter.event.Event.arg`).
* Improved docstrings in various and added a configuration doc section.
* Improved testing (more coverage).

3.0.5 (2019-12-06)
------------------

* Really fixed ``safe_repr`` so it doesn't cause side-effects (now isinstance/issubclass are avoided - they
  can cause side-effects in code that abuses descriptors in special attributes/methods).

3.0.4 (2019-10-26)
------------------

* Really fixed ``stream`` setup in actions (using ``force_colors`` without any ``stream`` was broken).
  See: :obj:`~hunter.actions.ColorStreamAction`.
* Fixed ``__repr__`` for the :obj:`~hunter.predicates.From` predicate to include ``watermark``.
* Added binary wheels for Python 3.8.

3.0.3 (2019-10-13)
------------------

* Fixed ``safe_repr`` on pypy so it's safer on method objects.
  See: :class:`~hunter.actions.ColorStreamAction`.

3.0.2 (2019-10-10)
------------------

* Fixed setting ``stream`` from ``PYTHONHUNTERCONFIG`` environment variable.
  See: :class:`~hunter.actions.ColorStreamAction`.
* Fixed a couple minor documentation issues.

3.0.1 (2019-06-17)
------------------

* Fixed issue with coloring missing source message (coloring leaked into next line).

3.0.0 (2019-06-17)
------------------

* The package now uses setuptools-scm for development builds (available at https://test.pypi.org/project/hunter/). As a
  consequence installing the sdist will download setuptools-scm.
* Recompiled cython modules with latest Cython. Hunter can be installed without any Cython, as before.
* Refactored some of the cython modules to have more typing information and not use deprecated property syntax.
* Replaced ``unsafe_repr`` option with ``repr_func``. Now you can use your custom repr function in the builtin actions.
  **BACKWARDS INCOMPATIBLE**
* Fixed buggy filename handling when using Hunter in ipython/jupyter. Source code should be properly displayed now.
* Removed ``globals`` option from ``VarsPrinter`` action. Globals are now always looked up. **BACKWARDS INCOMPATIBLE**
* Added support for locals in ``VarsPrinter`` action. Now you can do ``VarsPrinter('len(foobar)')``.
* Always pass module_globals dict to linecache methods. Source code from PEP-302 loaders is now printed properly.
  Contributed by Mikhail Borisov in `#65 <https://github.com/ionelmc/python-hunter/pull/65>`_.
* Various code cleanup, style and docstring fixing.
* Added :func:`hunter.From` helper to allow passing in filters directly as keyword arguments.
* Added :meth:`hunter.event.Event.detach` for storing events without leaks or side-effects (due to prolonged references
  to Frame objects, local or global variables).
* Refactored the internals of actions for easier subclassing.

  Added the
  :meth:`~hunter.actions.ColorStreamAction.filename_prefix`,
  :meth:`~hunter.actions.ColorStreamAction.output`,
  :meth:`~hunter.actions.ColorStreamAction.pid_prefix`,
  :meth:`~hunter.actions.ColorStreamAction.thread_prefix`,
  :meth:`~hunter.actions.ColorStreamAction.try_repr` and
  :meth:`~hunter.actions.ColorStreamAction.try_source` methods
  to the :class:`hunter.actions.ColorStreamAction` baseclass.
* Added :class:`hunter.actions.VarsSnooper` - a PySnooper-inspired variant of :class:`~hunter.actions.VarsPrinter`. It
  will record and show variable changes, with the risk of leaking or using too much memory of course :)
* Fixed tracers to log error and automatically stop if there's an internal failure. Previously error may have been
  silently dropped in some situations.

2.2.1 (2019-01-19)
------------------

* Fixed a link in changelog.
* Fixed some issues in the Travis configuration.

2.2.0 (2019-01-19)
------------------

* Added :class:`hunter.predicates.From` predicate for tracing from a specific point. It stop after returning back to the
  same call depth with a configurable offset.
* Fixed ``PYTHONHUNTERCONFIG`` not working in some situations (config values were resolved at the wrong time).
* Made tests in CI test the wheel that will eventually be published to PyPI
  (`tox-wheel <https://pypi.org/project/tox-wheel/>`_).
* Made ``event.stdlib`` more reliable: ``pkg_resources`` is considered part of stdlib and few more paths will be
  considered as stdlib.
* Dumbed down the ``get_peercred`` check that is done when attaching with ``hunter-trace`` CLI (via
  ``hunter.remote.install()``). It will be slightly insecure but will work on OSX.
* Added OSX in the Travis test grid.

2.1.0 (2018-11-17)
------------------

* Made ``threading_support`` on by default but output automatic (also, now ``1`` or ``0`` allowed).
* Added ``pid_alignment`` and ``force_pid`` action options to show a pid prefix.
* Fixed some bugs around ``__eq__`` in various classes.
* Dropped Python 3.3 support.
* Dropped dependency on `fields <https://python-fields.readthedocs.io/en/stable/>`_.
* Actions now repr using a simplified implementation that tries to avoid calling ``__repr__`` on user classes in order
  to avoid creating side-effects while tracing.
* Added support for the ``PYTHONHUNTERCONFIG`` environment variable (stores defaults and doesn't activate hunter).

2.0.2 (2017-11-24)
------------------

* Fixed indentation in :class:`hunter.actions.CallPrinter` action (shouldn't deindent on exception).
* Fixed option filtering in Cython Query implementation (filtering on ``tracer`` was allowed by mistake).
* Various fixes to docstrings and docs.

2.0.1 (2017-09-09)
------------------

* Now ``Py_AddPendingCall`` is used instead of acquiring the GIL (when using GDB).

2.0.0 (2017-09-02)
------------------

* Added the :attr:`hunter.event.Event.count` and :attr:`hunter.event.Event.calls` attributes.
* Added the ``lt``/``lte``/``gt``/``gte`` lookups.
* Added convenience aliases for ``startswith`` (``sw``), ``endswith`` (``ew``), ``contains`` (``has``)
  and ``regex`` (``rx``).
* Added a convenience :func:`hunter.wrap` decorator to start tracing around a function.
* Added support for remote tracing (with two backends: `manhole <https://pypi.org/project/manhole/>`__ and GDB) via
  the ``hunter-trace`` bin. Note: **Windows is NOT SUPPORTED**.
* Changed the default action to :class:`hunter.actions.CallPrinter`.
  You'll need to use ``action=CodePrinter`` if you want the old output.

1.4.1 (2016-09-24)
------------------

* Fix support for getting sources for Cython module (it was broken on Windows and Python3.5+).

1.4.0 (2016-09-24)
------------------

* Added support for tracing Cython modules (`#30 <https://github.com/ionelmc/python-hunter/issues/30>`_). A
  `# cython: linetrace=True` stanza or equivalent is required in Cython modules for this to work.

1.3.0 (2016-04-14)
------------------

* Added :attr:`hunter.event.Event.thread`.
* Added :attr:`hunter.event.Event.threadid` and :attr:`hunter.event.Event.threadname`
  (available for filtering with :func:`hunter.Q`).
* Added :attr:`hunter.event.Event.threading_support` argument to :func:`hunter.trace`.
  It makes new threads be traced and changes action output to include thread name.
* Added support for using `pdb++ <https://pypi.org/project/pdbpp/>`_ in the :class:`hunter.actions.Debugger` action.
* Added support for using `manhole <https://pypi.org/project/manhole/>`_ via a new :class:`hunter.actions.Manhole`
  action.
* Made the :attr:`hunter.event.Event.handler` a public but readonly property.


1.2.2 (2016-01-28)
------------------

* Fix broken import. Require ``fields>=4.0``.
* Simplify a string check in Cython code.

1.2.1 (2016-01-27)
------------------

* Fix "KeyError: 'normal'" bug in :class:`hunter.actions.CallPrinter`. Create the NO_COLORS dict from the COLOR dicts.
  Some keys were missing.

1.2.0 (2016-01-24)
------------------

* Fixed printouts of objects that return very large string in ``__repr__()``. Trimmed to 512. Configurable in actions
  with the ``repr_limit`` option.
* Improved validation of :class:`hunter.actions.VarsPrinter`'s initializer.
* Added a :class:`hunter.actions.CallPrinter` action.

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
* Remove the ``previous_tracer`` handling. Now when you call ``hunter.trace(...)`` the previous tracer (whatever was in
  ``sys.gettrace()``) is disabled and restored when ``hunter.stop()`` is called. **BACKWARDS INCOMPATIBLE**
* Fixed ``CodePrinter`` to show module name if it fails to get any sources.

0.6.0 (2015-10-10)
------------------

* Added a ``clear_env_var`` option on the tracer (disables tracing in subprocess).
* Added ``force_colors`` option on :class:`hunter.actions.VarsPrinter` and :class:`hunter.actions.CodePrinter`.
* Allowed setting the `stream` to a file name (option on :class:`hunter.actions.VarsPrinter` and
  :class:`hunter.actions.CodePrinter`).
* Bumped up the filename alignment to 40 cols.
* If not merging then ``self`` is not kept as a previous tracer anymore.
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

* Fixed :attr:`hunter.event.Event.globals` to actually be the dict of global vars (it was just the locals).

0.5.0 (2015-04-06)
------------------

* Fixed :func:`hunter.And` and :func:`hunter.Or` "single argument unwrapping".
* Implemented predicate compression. Example: ``Or(Or(a, b), c)`` is converted to ``Or(a, b, c)``.
* Renamed :attr:`hunter.event.Event.source` to :attr:`hunter.event.Event.fullsource`.
* Added :attr:`hunter.event.Event.source` that doesn't do any fancy sourcecode tokenization.
* Fixed :attr:`hunter.event.Event.fullsource` return value for situations where the tokenizer would fail.
* Made the print function available in the ``PYTHONHUNTER`` env var payload.
* Added a __repr__ for :class:`hunter.event.Event`.

0.4.0 (2015-03-29)
------------------

* Disabled colors for Jython.
  Contributed by Claudiu Popa in `#12 <https://github.com/ionelmc/python-hunter/pull/12>`_.
* Test suite fixes for Windows.
  Contributed by Claudiu Popa in `#11 <https://github.com/ionelmc/python-hunter/pull/11>`_.
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
* Added :attr:`hunter.event.Event.line` property. It returns the source code for the line being run.

0.2.0 (2015-03-27)
------------------

* Added color support (and ``colorama`` as dependency).
* Added support for expressions in :class:`hunter.actions.VarsPrinter`.
* Breaking changes:

  * Renamed ``F`` to :func:`hunter.Q`. And :func:`hunter.Q` is now just a convenience wrapper for
    :class:`hunter.predicates.Query`.
  * Renamed the ``PYTHON_HUNTER`` env variable to ``PYTHONHUNTER``.
  * Changed :class:`hunter.predicates.When` to take positional arguments.
  * Changed output to show 2 path components (still not configurable).
  * Changed :class:`hunter.actions.VarsPrinter` to take positional arguments for the names.
* Improved error reporting for env variable activation (``PYTHONHUNTER``).
* Fixed env var activator (the ``.pth`` file) installation with ``setup.py install`` (the "egg installs") and
  ``setup.py develop``/``pip install -e`` (the "egg links").

0.1.0 (2015-03-22)
------------------

* First release on PyPI.
