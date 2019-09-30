============
Introduction
============

Installation
============

To install hunter run::

    pip install hunter


The ``trace`` function
======================

The :obj:`hunter.trace` function can take 2 types of arguments:

* Keyword arguments like ``module``, ``function`` or ``action`` (see :obj:`hunter.Event` for all the possible
  filters).
* Callbacks that take an ``event`` argument:

  * Builtin predicates like: :class:`hunter.predicates.Query`, :class:`hunter.When`, :class:`hunter.And` or :class:`hunter.Or`.
  * Actions like: :class:`hunter.actions.CodePrinter`, :class:`hunter.actions.Debugger` or :class:`hunter.actions.VarsPrinter`
  * Any function. Or a disgusting lambda.

Note that :obj:`hunter.trace` will use :obj:`hunter.Q` when you pass multiple positional arguments or keyword arguments.

The ``Q`` function
==================

The :func:`hunter.Q` function provides a convenience API for you:

* ``Q(module='foobar')`` is converted to ``Query(module='foobar')``.
* ``Q(module='foobar', action=Debugger)`` is converted to ``When(Query(module='foobar'), Debugger)``.
* ``Q(module='foobar', actions=[CodePrinter, VarsPrinter('name')])`` is converted to
  ``When(Query(module='foobar'), CodePrinter, VarsPrinter('name'))``.
* ``Q(Q(module='foo'), Q(module='bar'))`` is converted to ``And(Q(module='foo'), Q(module='bar'))``.
* ``Q(your_own_callback, module='foo')`` is converted to ``And(your_own_callback, Q(module='foo'))``.

Note that the default junction :func:`hunter.Q` uses is :class:`hunter.predicates.And`.

Composing
=========

All the builtin predicates (:class:`hunter.predicates.Query`, :class:`hunter.predicates.When`,
:class:`hunter.predicates.And`, :class:`hunter.predicates.Not` and :class:`hunter.predicates.Or`) support
the ``|``, ``&`` and ``~`` operators:

* ``Query(module='foo') | Query(module='bar')`` is converted to ``Or(Query(module='foo'), Query(module='bar'))``
* ``Query(module='foo') & Query(module='bar')`` is converted to ``And(Query(module='foo'), Query(module='bar'))``
* ``~Query(module='foo')`` is converted to ``Not(Query(module='foo'))``

Operators
=========

.. versionadded:: 1.0.0

    You can add ``startswith``, ``endswith``, ``in``, ``contains``, ``regex``, ``lt``, ``lte``, ``gt``, ``gte`` to your
    keyword arguments, just like in Django. Double underscores are not necessary, but in case you got twitchy fingers
    it'll just work - ``filename__startswith`` is the same as ``filename_startswith``.

.. versionadded:: 2.0.0

    You can also use these convenience aliases: ``sw`` (``startswith``), ``ew`` (``endswith``), ``rx`` (``regex``) and
    ``has`` (``contains``).

Examples:

* ``Query(module_in=['re', 'sre', 'sre_parse'])`` will match events from any of those modules.
* ``~Query(module_in=['re', 'sre', 'sre_parse'])`` will match events from any modules except those.
* ``Query(module_startswith=['re', 'sre', 'sre_parse'])`` will match any events from modules that starts with either of
  those. That means ``repr`` will match!
* ``Query(module_regex='(re|sre.*)$')`` will match any events from ``re`` or anything that starts with ``sre``.

.. note:: If you want to filter out stdlib stuff you're better off with using ``Query(stdlib=False)``.

Activation
==========

You can activate Hunter in three ways.

from code
---------

.. sourcecode:: python

    import hunter
    hunter.trace(
        ...
    )

with an environment variable
----------------------------

Set the ``PYTHONHUNTER`` environment variable. Eg:

.. sourcecode:: bash

    PYTHONHUNTER="module='os.path'" python yourapp.py

On Windows you'd do something like:

.. sourcecode:: bat

    set PYTHONHUNTER=module='os.path'
    python yourapp.py

The activation works with a clever ``.pth`` file that checks for that env var presence and before your app runs does something like this:

.. sourcecode:: python

    from hunter import *
    trace(
        <whatever-you-had-in-the-PYTHONHUNTER-env-var>
    )

That also means that it will do activation even if the env var is empty, eg: ``PYTHONHUNTER=""``.

with a CLI tool
---------------

If you got an already running process you can attach to it with ``hunter-trace``. See :doc:`remote` for details.
