========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |github-actions| |requires|
        | |codecov|
    * - package
      - | |version| |wheel| |supported-versions| |supported-implementations|
        | |commits-since|
.. |docs| image:: https://readthedocs.org/projects/python-hunter/badge/?style=flat
    :target: https://python-hunter.readthedocs.io/
    :alt: Documentation Status

.. |github-actions| image:: https://github.com/ionelmc/python-hunter/actions/workflows/github-actions.yml/badge.svg
    :alt: GitHub Actions Build Status
    :target: https://github.com/ionelmc/python-hunter/actions

.. |requires| image:: https://requires.io/github/ionelmc/python-hunter/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/ionelmc/python-hunter/requirements/?branch=master

.. |codecov| image:: https://codecov.io/gh/ionelmc/python-hunter/branch/master/graphs/badge.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/ionelmc/python-hunter

.. |version| image:: https://img.shields.io/pypi/v/hunter.svg
    :alt: PyPI Package latest release
    :target: https://pypi.org/project/hunter

.. |wheel| image:: https://img.shields.io/pypi/wheel/hunter.svg
    :alt: PyPI Wheel
    :target: https://pypi.org/project/hunter

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hunter.svg
    :alt: Supported versions
    :target: https://pypi.org/project/hunter

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hunter.svg
    :alt: Supported implementations
    :target: https://pypi.org/project/hunter

.. |commits-since| image:: https://img.shields.io/github/commits-since/ionelmc/python-hunter/v3.5.1.svg
    :alt: Commits since latest release
    :target: https://github.com/ionelmc/python-hunter/compare/v3.5.1...master



.. end-badges

Hunter is a flexible code tracing toolkit, not for measuring coverage, but for debugging, logging, inspection and other
nefarious purposes. It has a `simple Python API <https://python-hunter.readthedocs.io/en/latest/introduction.html>`_,
a `convenient terminal API <environment-variable-activation_>`_ and
a `CLI tool to attach to processes <tracing-processes_>`_.

* Free software: BSD 2-Clause License

Installation
============

::

    pip install hunter

Documentation
=============


https://python-hunter.readthedocs.io/

Getting started
===============

Basic use involves passing various filters to the ``trace`` option. An example:

.. sourcecode:: python

    import hunter
    hunter.trace(module='posixpath', action=hunter.CallPrinter)

    import os
    os.path.join('a', 'b')

That would result in:

.. sourcecode:: pycon

    >>> os.path.join('a', 'b')
             /usr/lib/python3.6/posixpath.py:75    call      => join(a='a')
             /usr/lib/python3.6/posixpath.py:80    line         a = os.fspath(a)
             /usr/lib/python3.6/posixpath.py:81    line         sep = _get_sep(a)
             /usr/lib/python3.6/posixpath.py:41    call         => _get_sep(path='a')
             /usr/lib/python3.6/posixpath.py:42    line            if isinstance(path, bytes):
             /usr/lib/python3.6/posixpath.py:45    line            return '/'
             /usr/lib/python3.6/posixpath.py:45    return       <= _get_sep: '/'
             /usr/lib/python3.6/posixpath.py:82    line         path = a
             /usr/lib/python3.6/posixpath.py:83    line         try:
             /usr/lib/python3.6/posixpath.py:84    line         if not p:
             /usr/lib/python3.6/posixpath.py:86    line         for b in map(os.fspath, p):
             /usr/lib/python3.6/posixpath.py:87    line         if b.startswith(sep):
             /usr/lib/python3.6/posixpath.py:89    line         elif not path or path.endswith(sep):
             /usr/lib/python3.6/posixpath.py:92    line         path += sep + b
             /usr/lib/python3.6/posixpath.py:86    line         for b in map(os.fspath, p):
             /usr/lib/python3.6/posixpath.py:96    line         return path
             /usr/lib/python3.6/posixpath.py:96    return    <= join: 'a/b'
    'a/b'

In a terminal it would look like:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/code-trace.png


Another useful scenario is to ignore all standard modules and force colors to make them stay even if the output is
redirected to a file.

.. sourcecode:: python

    import hunter
    hunter.trace(stdlib=False, action=hunter.CallPrinter(force_colors=True))

Actions
-------

Output format can be controlled with "actions". There's an alternative ``CodePrinter`` action that doesn't handle
nesting (it was the default action until Hunter 2.0).

If filters match then action will be run. Example:

.. sourcecode:: python

    import hunter
    hunter.trace(module='posixpath', action=hunter.CodePrinter)

    import os
    os.path.join('a', 'b')

That would result in:

.. sourcecode:: pycon

    >>> os.path.join('a', 'b')
             /usr/lib/python3.6/posixpath.py:75    call      def join(a, *p):
             /usr/lib/python3.6/posixpath.py:80    line          a = os.fspath(a)
             /usr/lib/python3.6/posixpath.py:81    line          sep = _get_sep(a)
             /usr/lib/python3.6/posixpath.py:41    call      def _get_sep(path):
             /usr/lib/python3.6/posixpath.py:42    line          if isinstance(path, bytes):
             /usr/lib/python3.6/posixpath.py:45    line              return '/'
             /usr/lib/python3.6/posixpath.py:45    return            return '/'
                                                   ...       return value: '/'
             /usr/lib/python3.6/posixpath.py:82    line          path = a
             /usr/lib/python3.6/posixpath.py:83    line          try:
             /usr/lib/python3.6/posixpath.py:84    line              if not p:
             /usr/lib/python3.6/posixpath.py:86    line              for b in map(os.fspath, p):
             /usr/lib/python3.6/posixpath.py:87    line                  if b.startswith(sep):
             /usr/lib/python3.6/posixpath.py:89    line                  elif not path or path.endswith(sep):
             /usr/lib/python3.6/posixpath.py:92    line                      path += sep + b
             /usr/lib/python3.6/posixpath.py:86    line              for b in map(os.fspath, p):
             /usr/lib/python3.6/posixpath.py:96    line          return path
             /usr/lib/python3.6/posixpath.py:96    return        return path
                                                   ...       return value: 'a/b'
    'a/b'

- or in a terminal:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/simple-trace.png

------

Another useful action is the ``VarsPrinter``:

.. sourcecode:: python

    import hunter
    # note that this kind of invocation will also use the default `CallPrinter` action
    hunter.trace(hunter.Q(module='posixpath', action=hunter.VarsPrinter('path')))

    import os
    os.path.join('a', 'b')

That would result in:

.. sourcecode:: pycon

    >>> os.path.join('a', 'b')
         /usr/lib/python3.6/posixpath.py:75    call      => join(a='a')
         /usr/lib/python3.6/posixpath.py:80    line         a = os.fspath(a)
         /usr/lib/python3.6/posixpath.py:81    line         sep = _get_sep(a)
         /usr/lib/python3.6/posixpath.py:41    call      [path => 'a']
         /usr/lib/python3.6/posixpath.py:41    call         => _get_sep(path='a')
         /usr/lib/python3.6/posixpath.py:42    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:42    line            if isinstance(path, bytes):
         /usr/lib/python3.6/posixpath.py:45    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:45    line            return '/'
         /usr/lib/python3.6/posixpath.py:45    return    [path => 'a']
         /usr/lib/python3.6/posixpath.py:45    return       <= _get_sep: '/'
         /usr/lib/python3.6/posixpath.py:82    line         path = a
         /usr/lib/python3.6/posixpath.py:83    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:83    line         try:
         /usr/lib/python3.6/posixpath.py:84    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:84    line         if not p:
         /usr/lib/python3.6/posixpath.py:86    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:86    line         for b in map(os.fspath, p):
         /usr/lib/python3.6/posixpath.py:87    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:87    line         if b.startswith(sep):
         /usr/lib/python3.6/posixpath.py:89    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:89    line         elif not path or path.endswith(sep):
         /usr/lib/python3.6/posixpath.py:92    line      [path => 'a']
         /usr/lib/python3.6/posixpath.py:92    line         path += sep + b
         /usr/lib/python3.6/posixpath.py:86    line      [path => 'a/b']
         /usr/lib/python3.6/posixpath.py:86    line         for b in map(os.fspath, p):
         /usr/lib/python3.6/posixpath.py:96    line      [path => 'a/b']
         /usr/lib/python3.6/posixpath.py:96    line         return path
         /usr/lib/python3.6/posixpath.py:96    return    [path => 'a/b']
         /usr/lib/python3.6/posixpath.py:96    return    <= join: 'a/b'
    'a/b'

In a terminal it would look like:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/vars-trace.png

-----

You can give it a tree-like configuration where you can optionally configure specific actions for parts of the
tree (like dumping variables or a pdb set_trace):

.. sourcecode:: python

    from hunter import trace, Q, Debugger
    from pdb import Pdb

    trace(
        # drop into a Pdb session if ``foo.bar()`` is called
        Q(module="foo", function="bar", kind="call", action=Debugger(klass=Pdb))
        |  # or
        Q(
            # show code that contains "mumbo.jumbo" on the current line
            lambda event: event.locals.get("mumbo") == "jumbo",
            # and it's not in Python's stdlib
            stdlib=False,
            # and it contains "mumbo" on the current line
            source__contains="mumbo"
        )
    )

    import foo
    foo.func()

With a ``foo.py`` like this:

.. sourcecode:: python

    def bar():
        execution_will_get_stopped  # cause we get a Pdb session here

    def func():
        mumbo = 1
        mumbo = "jumbo"
        print("not shown in trace")
        print(mumbo)
        mumbo = 2
        print(mumbo) # not shown in trace
        bar()


We get:

.. sourcecode:: pycon

    >>> foo.func()
    not shown in trace
        /home/ionel/osp/python-hunter/foo.py:8     line          print(mumbo)
    jumbo
        /home/ionel/osp/python-hunter/foo.py:9     line          mumbo = 2
    2
        /home/ionel/osp/python-hunter/foo.py:1     call      def bar():
    > /home/ionel/osp/python-hunter/foo.py(2)bar()
    -> execution_will_get_stopped  # cause we get a Pdb session here
    (Pdb)

In a terminal it would look like:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/tree-trace.png

.. _tracing-processes:

Tracing processes
-----------------

In similar fashion to ``strace`` Hunter can trace other processes, eg::

    hunter-trace --gdb -p 123

If you wanna play it safe (no messy GDB) then add this in your code::

    from hunter import remote
    remote.install()

Then you can do::

    hunter-trace -p 123

See `docs on the remote feature <https://python-hunter.readthedocs.org/en/latest/remote.html>`_.

**Note:** Windows ain't supported.

.. _environment-variable-activation:

Environment variable activation
-------------------------------

For your convenience environment variable activation is available. Just run your app like this::


    PYTHONHUNTER="module='os.path'" python yourapp.py

On Windows you'd do something like::

    set PYTHONHUNTER=module='os.path'
    python yourapp.py

The activation works with a clever ``.pth`` file that checks for that env var presence and before your app runs does something
like this::

    from hunter import *
    trace(<whatever-you-had-in-the-PYTHONHUNTER-env-var>)

Note that Hunter is activated even if the env var is empty, eg: ``PYTHONHUNTER=""``.

Environment variable configuration
``````````````````````````````````

Sometimes you always use the same options (like ``stdlib=False`` or ``force_colors=True``). To save typing you can
set something like this in your environment::

    PYTHONHUNTERCONFIG="stdlib=False,force_colors=True"

This is the same as ``PYTHONHUNTER="stdlib=False,action=CallPrinter(force_colors=True)"``.

Notes:

* Setting ``PYTHONHUNTERCONFIG`` alone doesn't activate hunter.
* All the options for the builtin actions are supported.
* Although using predicates is supported it can be problematic. Example of setup that won't trace anything::

    PYTHONHUNTERCONFIG="Q(module_startswith='django')"
    PYTHONHUNTER="Q(module_startswith='celery')"

  which is the equivalent of::

    PYTHONHUNTER="Q(module_startswith='django'),Q(module_startswith='celery')"

  which is the equivalent of::

    PYTHONHUNTER="Q(module_startswith='django')&Q(module_startswith='celery')"



Filtering DSL
-------------

Hunter supports a flexible query DSL, see the `introduction
<https://python-hunter.readthedocs.org/en/latest/introduction.html>`_.

Development
===========

To run the all tests run::

    tox

Design notes
============

Hunter doesn't do everything. As a design goal of this library some things are made intentionally austere and verbose (to avoid complexity,
confusion and inconsistency). This has few consequences:

* There are `Operators <https://python-hunter.readthedocs.io/en/stable/introduction.html#operators>`_ but there's no negation operator.
  Instead you're expected to negate a Query object, eg: ``~Q(module='re')``.
* There are no specialized operators or filters - all filters behave exactly the same. For example:

  * No filter for packages. You're expected to filter by module with an operator.
  * No filter for arguments, return values or variables. You're expected to write your own filter function and deal with the problems
    of poking into objects.
* Layering is minimal. There's are some `helpers <https://python-hunter.readthedocs.io/en/stable/reference.html#helpers>`_ that do
  some argument processing and conversions to save you some typing but that's about it.
* The library doesn't try to hide the mechanics of tracing in Python - it's 1:1 regarding what Python sends to a trace function if you'd be
  using `sys.settrace <https://docs.python.org/3/library/sys.html#sys.settrace>`_.
* Doesn't have any storage. You are expected to redirect output to a file.

You should look at it like it's a tool to help you understand and debug big applications, or a framework ridding you of the boring parts of
settrace, not something that helps you learn Python.

FAQ
===

Why not Smiley?
---------------

There's some obvious overlap with `smiley <https://pypi.org/project/smiley/>`_ but there are few fundamental differences:

* Complexity. Smiley is simply over-engineered:

  * It uses IPC and a SQL database.
  * It has a webserver. Lots of dependencies.
  * It uses threads. Side-effects and subtle bugs are introduced in your code.
  * It records everything. Tries to dump any variable. Often fails and stops working.

  Why do you need all that just to debug some stuff in a terminal? Simply put, it's a nice idea but the design choices work
  against you when you're already neck-deep into debugging your own code. In my experience Smiley has been very buggy and
  unreliable. Your mileage may vary of course.

* Tracing long running code. This will make Smiley record lots of data, making it unusable.

  Now because Smiley records everything, you'd think it's better suited for short programs. But alas, if your program runs
  quickly then it's pointless to record the execution. You can just run it again.

  It seems there's only one situation where it's reasonable to use Smiley: tracing io-bound apps remotely. Those apps don't
  execute lots of code, they just wait on network so Smiley's storage won't blow out of proportion and tracing overhead might
  be acceptable.
* Use-cases. It seems to me Smiley's purpose is not really debugging code, but more of a "non interactive monitoring" tool.

In contrast, Hunter is very simple:

* Few dependencies.
* Low overhead (tracing/filtering code has an optional Cython extension).
* No storage. This simplifies lots of things.

  The only cost is that you might need to run the code multiple times to get the filtering/actions right. This means Hunter is
  not really suited for "post-mortem" debugging. If you can't reproduce the problem anymore then Hunter won't be of much help.

Why not pytrace?
----------------

`Pytrace <https://pypi.org/project/pytrace/>`_ is another tracer tool. It seems quite similar to Smiley - it uses a sqlite
database for the events, threads and IPC, thus it's reasonable to expect the same kind of problems.

Why not PySnooper or snoop?
---------------------------

`snoop <https://pypi.org/project/snoop/>`_ is a refined version of `PySnooper <https://pypi.org/project/PySnooper/>`_. Both are
more suited to tracing small programs or functions as the output is more verbose and less suited to the needs of tracing a big application
where Hunter provides more flexible setup, filtering capabilities, speed and brevity.

Why not coverage?
-----------------

For purposes of debugging `coverage <https://pypi.org/project/coverage/>`_ is a great tool but only as far as "debugging
by looking at what code is (not) run". Checking branch coverage is good but it will only get you as far.

From the other perspective, you'd be wondering if you could use Hunter to measure coverage-like things. You could do it but
for that purpose Hunter is very "rough": it has no builtin storage. You'd have to implement your own storage. You can do it
but it wouldn't give you any advantage over making your own tracer if you don't need to "pre-filter" whatever you're
recording.

In other words, filtering events is the main selling point of Hunter - it's fast (cython implementation) and the query API is
flexible enough.

Projects using Hunter
=====================

Noteworthy usages or Hunter (submit a PR with your project if you built a tool that relies on hunter):

* `Crunch-io/diagnose <https://github.com/Crunch-io/diagnose>`_ - a runtime instrumentation library.
* `talwrii/huntrace <https://github.com/talwrii/huntrace>`_ - an alternative cli (similar to ltrace).
* `anki-code/xunter <https://github.com/anki-code/xunter>`_ - a profiling tool made specifically for `the xonsh shell <https://xon.sh>`_.

More projects using it at https://github.com/ionelmc/python-hunter/network/dependents
