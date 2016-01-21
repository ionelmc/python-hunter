========
Overview
========

.. start-badges

.. list-table::
    :stub-columns: 1

    * - docs
      - |docs|
    * - tests
      - | |travis| |appveyor| |requires|
        | |coveralls| |codecov|
        | |landscape| |scrutinizer| |codacy| |codeclimate|
    * - package
      - |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/python-hunter/badge/?style=flat
    :target: https://readthedocs.org/projects/python-hunter
    :alt: Documentation Status

.. |travis| image:: https://travis-ci.org/ionelmc/python-hunter.svg?branch=master
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/ionelmc/python-hunter

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/ionelmc/python-hunter?branch=master&svg=true
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/ionelmc/python-hunter

.. |requires| image:: https://requires.io/github/ionelmc/python-hunter/requirements.svg?branch=master
    :alt: Requirements Status
    :target: https://requires.io/github/ionelmc/python-hunter/requirements/?branch=master

.. |coveralls| image:: https://coveralls.io/repos/ionelmc/python-hunter/badge.svg?branch=master&service=github
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-hunter

.. |codecov| image:: https://codecov.io/github/ionelmc/python-hunter/coverage.svg?branch=master
    :alt: Coverage Status
    :target: https://codecov.io/github/ionelmc/python-hunter

.. |landscape| image:: https://landscape.io/github/ionelmc/python-hunter/master/landscape.svg?style=flat
    :target: https://landscape.io/github/ionelmc/python-hunter/master
    :alt: Code Quality Status

.. |codacy| image:: https://api.codacy.com/project/badge/grade/2342e517f3dc4e66910087953afb3a0e
    :target: https://www.codacy.com/app/ionelmc/python-hunter
    :alt: Codacy Code Quality Status

.. |codeclimate| image:: https://codeclimate.com/github/ionelmc/python-hunter/badges/gpa.svg
   :target: https://codeclimate.com/github/ionelmc/python-hunter
   :alt: CodeClimate Quality Status

.. |version| image:: https://img.shields.io/pypi/v/hunter.svg?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/hunter

.. |downloads| image:: https://img.shields.io/pypi/dm/hunter.svg?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/hunter

.. |wheel| image:: https://img.shields.io/pypi/wheel/hunter.svg?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/hunter

.. |supported-versions| image:: https://img.shields.io/pypi/pyversions/hunter.svg?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/hunter

.. |supported-implementations| image:: https://img.shields.io/pypi/implementation/hunter.svg?style=flat
    :alt: Supported implementations
    :target: https://pypi.python.org/pypi/hunter

.. |scrutinizer| image:: https://img.shields.io/scrutinizer/g/ionelmc/python-hunter/master.svg?style=flat
    :alt: Scrutinizer Status
    :target: https://scrutinizer-ci.com/g/ionelmc/python-hunter/


.. end-badges

Hunter is a flexible code tracing toolkit, not for measuring coverage, but for debugging, logging, inspection and other
nefarious purposes. It has a simple Python API and a convenient terminal API (see `Environment variable activation
<env-var-activation_>`_).

* Free software: BSD license

Installation
============

::

    pip install hunter

Documentation
=============

https://python-hunter.readthedocs.org/


Overview
========

The default action is to just print the code being executed. Example:

.. sourcecode:: python

    import hunter
    hunter.trace(module='posixpath')

    import os
    os.path.join('a', 'b')

Would result in::

    python2.7/posixpath.py:60    call      def join(a, *p):
    python2.7/posixpath.py:64    line          path = a
    python2.7/posixpath.py:65    line          for b in p:
    python2.7/posixpath.py:66    line              if b.startswith('/'):
    python2.7/posixpath.py:68    line              elif path == '' or path.endswith('/'):
    python2.7/posixpath.py:71    line                  path += '/' + b
    python2.7/posixpath.py:65    line          for b in p:
    python2.7/posixpath.py:72    line          return path
    python2.7/posixpath.py:72    return        return path
                                 ...       return value: 'a/b'

- or in a terminal:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/simple-trace.png

You can have custom actions, like a variable printer - example:

.. sourcecode:: python

    import hunter
    hunter.trace(hunter.Q(module='posixpath', action=hunter.VarsPrinter('path')))

    import os
    os.path.join('a', 'b')

Would result in::

    python2.7/posixpath.py:60    call      def join(a, *p):
    python2.7/posixpath.py:64    line          path = a
                                 vars      path => 'a'
    python2.7/posixpath.py:65    line          for b in p:
                                 vars      path => 'a'
    python2.7/posixpath.py:66    line              if b.startswith('/'):
                                 vars      path => 'a'
    python2.7/posixpath.py:68    line              elif path == '' or path.endswith('/'):
                                 vars      path => 'a'
    python2.7/posixpath.py:71    line                  path += '/' + b
                                 vars      path => 'a/b'
    python2.7/posixpath.py:65    line          for b in p:
                                 vars      path => 'a/b'
    python2.7/posixpath.py:72    line          return path
                                 vars      path => 'a/b'
    python2.7/posixpath.py:72    return        return path
                                 ...       return value: 'a/b'

- or in a terminal:

.. image:: https://raw.githubusercontent.com/ionelmc/python-hunter/master/docs/vars-trace.png

You can give it a tree-like configuration where you can optionally configure specific actions for parts of the
tree (like dumping variables or a pdb set_trace):

    TODO: More examples.

.. _env-var-activation:

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

Filtering DSL
-------------

Hunter supports a flexible query DSL, see the `introduction
<https://python-hunter.readthedocs.org/en/latest/introduction.html>`_.

Development
===========

To run the all tests run::

    tox


FAQ
===

Why not Smiley?
---------------

There's some obvious overlap with `smiley <https://pypi.python.org/pypi/smiley>`_ but there are few fundamental differences:

* Complexity. Smiley is simply over-engineered:

  * It's uses IPC and a SQL database.
  * It has a webserver. Lots of dependencies.
  * It uses threads. Side-effects and subtle bugs are introduced in your code.
  * It records everything. Tries to dump any variable. Often fails and stops working.

  Why do you need all that just to debug some stuff in a terminal? Simply put, it's a nice idea but the design choices work
  against you when you're already neck-deep into debugging your own code. In my experience Smiley has been very buggy and
  unreliable. Your mileage might way of course.

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

Why (not) coverage?
-------------------

For purposes of debugging `coverage <https://pypi.python.org/pypi/coverage>`_ is a great tool but only as far as "debugging
by looking at what code is (not) run". Checking branch coverage is good but it will only get you as far.

From the other perspective, you'd be wondering if you could use Hunter to measure coverage-like things. You could do it but
for that purpose Hunter is very "rough": it has no builtin storage. You'd have to implement your own storage. You can do it
but it wouldn't give you any advantage over making your own tracer if you don't need to "pre-filter" whatever you're
recording.

In other words, filtering events is the main selling point of Hunter - it's fast (cython implementation) and the query API is
flexible enough.
