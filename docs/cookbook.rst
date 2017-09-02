========
Cookbook
========

.. epigraph::

    When in doubt, use Hunter.

Packaging
=========

I frequently use Hunter to figure out how distutils/setuptools work. It's very hard to figure out what's going on by just
looking at the code - lots of stuff happens at runtime. If you ever tried to write a custom command you know what I mean.

To show everything that is being run:

.. sourcecode:: shell

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"]' python setup.py bdist_wheel

If you want too see some interesting variables:

.. sourcecode:: shell

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"], actions=[CodePrinter, VarsPrinter("self.bdist_dir")]' python setup.py bdist_wheel

Typical
=======

Normally you'd only want to look at your code. For that purpose, there's the ``stdlib`` option. Set it to ``False``.

Building a bit on the previous example, if I have a ``build`` Distutils command and I only want to see my code then I'd run
this:

.. sourcecode:: shell

    PYTHONHUNTER='stdlib=False' python setup.py build

But this also means I'd be seeing anything from ``site-packages``. I could filter on only the events from the current
directory (assuming the filename is going to be a relative path):

.. sourcecode:: shell

    PYTHONHUNTER='~Q(filename_startswith="/")' python setup.py build

Needle in the haystack
======================

If the needle might be though the stdlib then you got not choice. But some of the `hay` is very verbose and useless, like
stuff from the ``re`` module.

Note that there are few "hidden" modules like ``sre``, ``sre_parse``, ``sre_compile`` etc. You can filter that out with:

.. sourcecode:: python

    ~Q(module_regex="(re|sre.*)$")

Although filtering out that regex stuff can cut down lots of useless output you usually still get lots of output.

Another way, if you got at least some vague idea of what might be going on is to "grep" for sourcecode. Example, to show all
the code that does something with a ``build_dir`` property:

.. sourcecode:: python

    source_contains=".build_dir"

You could even extend that a bit to dump some variables::

.. sourcecode:: python

    source_contains=".build_dir", actions=[CodePrinter, VarsPrinter("self.build_dir")]


Stop after N calls
==================

Say you want to stop tracing after 1000 events, you'd do this:

.. sourcecode:: python

    ~Q(calls_gt=1000, action=Stop)

..

    Explanation:

        ``Q(calls_gt=1000, action=Stop)`` will translate to ``When(Query(calls_gt=1000), Stop)``

        ``Q(calls_gt=1000)`` will return ``True`` when 1000 call count is hit.

        ``When(something, Stop)`` will call ``Stop`` when ``something`` returns ``True``. However it will also return the result of ``something`` - the net effect being nothing being shown up to 1000 calls. Clearly not what we want ...

        So then we invert the result, ``~When(...)`` is the same as ``Not(When)``.

        This may not seem intuitive but for now it makes internals simpler. If ``When`` would always return ``True`` then
        ``Or(When, When)`` would never run the second ``When`` and we'd need to have all sorts of checks for this. This may
        change in the future however.
