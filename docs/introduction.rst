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

* Keyword arguments like ``module``, ``function`` or ``action``. This is for convenience.
* Callbacks that take an ``event`` argument:

  * Builtin predicates like: :class:`hunter.Query`, :class:`hunter.When`, :class:`hunter.And` or :class:`hunter.Or`.
  * Actions like: :class:`hunter.CodePrinter`, :class:`hunter.Debugger` or :class:`hunter.VarsPrinter`

Note that :obj:`hunter.trace` will use :obj:`hunter.Q` when you pass multiple positional arguments or keyword arguments.

The ``Q`` function
==================

The :obj:`hunter.Q` function provides a convenience API for you:

* ``Q(module='foobar')`` is converted to ``Query(module='foobar')``.
* ``Q(module='foobar', action=Debugger)`` is converted to ``When(Query(module='foobar'), Debugger)``.
* ``Q(module='foobar', actions=[CodePrinter, VarsPrinter('name')])`` is converted to ``When(Query(module='foobar'), CodePrinter, VarsPrinter('name'))``.
* ``Q(Q(module='foo'), Q(module='bar'))`` is converted to ``Or(Q(module='foo'), Q(module='bar'))``.
* ``Q(your_own_callback, module='foo')`` is converted to ``Or(your_own_callback, Q(module='foo'))``.

Note that the default junction :obj:`hunter.Q` uses is :obj:`hunter.Or`.

The builtin predicates and actions
==================================

All the builtin predicates (:class:`hunter.Query`, :class:`hunter.When`, :class:`hunter.And` and :class:`hunter.Or`) support the ``|`` and ``&`` operators:

* ``Query(module='foo') | Query(module='bar')`` is converted to ``Or(Query(module='foo'), Query(module='bar'))``
* ``Query(module='foo') & Query(module='bar')`` is converted to ``And(Query(module='foo'), Query(module='bar'))``

Activation
==========

You can activate Hunter in two ways.

`via` code
----------

.. sourcecode:: python

    import hunter
    hunter.trace(
        ...
    )

`via` environment variable
--------------------------

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
