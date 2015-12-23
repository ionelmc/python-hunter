========
Cookbook
========

.. epigraph::

    When in doubt, use Hunter.

Packaging
=========

I frequently use Hunter to figure out how distutils/setuptools work. It's very hard to figure out what's going on by just
looking at the code - lots of stuff happens at runtime. If you ever tried to write a custom command you know what I mean.

To show everything that is being run::

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"]' python setup.py bdist_wheel

If you want too see some interesting variables::

    PYTHONHUNTER='module_startswith=["setuptools", "distutils", "wheel"], actions=[CodePrinter, VarsPrinter("self.bdist_dir")]' python setup.py bdist_wheel

Typical
=======

Normally you'd only want to look at your code. For that purpose, there's the ``stdlib`` option. Set it to ``False``.

Building a bit on the previous example, if I have a ``build`` Distutils command and I only want to see my code then I'd run
this::

    PYTHONHUNTER='stdlib=False' python setup.py build

But this also means I'd be seeing anything from ``site-packages``. I could filter on only the events from the current
directory (assuming the filename is going to be a relative path)::

    PYTHONHUNTER='~Q(filename_startswith="/")' python setup.py build

Needle in the haystack
======================

If the needle might be though the stdlib then you got not choice. But some of the `hay` is very verbose and useless, like
stuff from the ``re`` module.

Note that there are few "hidden" modules like ``sre``, ``sre_parse``, ``sre_compile`` etc. You can filter that out with::

    PYTHONHUNTER='~Q(module_regex="(re|sre.*)$")'

Although filtering out that regex stuff can cut down lots of useless output you usually still get lots of output.

Another way, if you got at least some vague idea of what might be going on is to "grep" for sourcecode. Example, to show all
the code that does something with a ``build_dir`` property::

    PYTHONHUNTER='source_contains=".build_dir"'

You could even extend that a bit to dump some variables::

    PYTHONHUNTER='source_contains=".build_dir", actions=[CodePrinter, VarsPrinter("self.build_dir")]'


