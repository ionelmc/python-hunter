===============================
Hunter
===============================

| |docs| |travis| |appveyor| |coveralls| |landscape| |scrutinizer|
| |version| |downloads| |wheel| |supported-versions| |supported-implementations|

.. |docs| image:: https://readthedocs.org/projects/python-hunter/badge/?style=flat
    :target: https://readthedocs.org/projects/python-hunter
    :alt: Documentation Status

.. |travis| image:: http://img.shields.io/travis/ionelmc/python-hunter/master.png?style=flat
    :alt: Travis-CI Build Status
    :target: https://travis-ci.org/ionelmc/python-hunter

.. |appveyor| image:: https://ci.appveyor.com/api/projects/status/github/ionelmc/python-hunter?branch=master
    :alt: AppVeyor Build Status
    :target: https://ci.appveyor.com/project/ionelmc/python-hunter

.. |coveralls| image:: http://img.shields.io/coveralls/ionelmc/python-hunter/master.png?style=flat
    :alt: Coverage Status
    :target: https://coveralls.io/r/ionelmc/python-hunter

.. |landscape| image:: https://landscape.io/github/ionelmc/python-hunter/master/landscape.svg?style=flat
    :target: https://landscape.io/github/ionelmc/python-hunter/master
    :alt: Code Quality Status

.. |version| image:: http://img.shields.io/pypi/v/hunter.png?style=flat
    :alt: PyPI Package latest release
    :target: https://pypi.python.org/pypi/hunter

.. |downloads| image:: http://img.shields.io/pypi/dm/hunter.png?style=flat
    :alt: PyPI Package monthly downloads
    :target: https://pypi.python.org/pypi/hunter

.. |wheel| image:: https://pypip.in/wheel/hunter/badge.png?style=flat
    :alt: PyPI Wheel
    :target: https://pypi.python.org/pypi/hunter

.. |supported-versions| image:: https://pypip.in/py_versions/hunter/badge.png?style=flat
    :alt: Supported versions
    :target: https://pypi.python.org/pypi/hunter

.. |supported-implementations| image:: https://pypip.in/implementation/hunter/badge.png?style=flat
    :alt: Supported imlementations
    :target: https://pypi.python.org/pypi/hunter

.. |scrutinizer| image:: https://img.shields.io/scrutinizer/g/ionelmc/python-hunter/master.png?style=flat
    :alt: Scrtinizer Status
    :target: https://scrutinizer-ci.com/g/ionelmc/python-hunter/

Hunter is a flexible code tracing toolkit, not for measuring coverage, but for debugging, logging, inspection and other
nefarious purposes.

API is considered unstable until 1.0 is released.

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

Environment variable activation
-------------------------------

For your convenience environment variable activation is available. Just run your app like this::


    PYTHONHUNTER="module='os.path'" python yourapp.py

On Windows you'd do something like::

    set PYTHONHUNTER="module='os.path'"
    python yourapp.py

The activation works with a clever ``.pth`` file that checks for that env var presence and before your app runs does something like this::

    from hunter import *
    trace(<whatever-you-had-in-the-PYTHONHUNTER-env-var>)

That also means that it will do activation even if the env var is empty, eg: ``PYTHONHUNTER=""``.

Development
===========

To run the all tests run::

    tox
