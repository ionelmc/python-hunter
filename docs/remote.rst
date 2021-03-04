==============
Remote tracing
==============

Hunter supports tracing local processes, with two backends: `manhole <https://pypi.org/project/manhole/>`_ and GDB.
For now Windows isn't supported.

Using GDB is risky (if anything goes wrong your process will probably be hosed up badly) so the Manhole backend is
recommended. To use it:

.. sourcecode:: python

    from hunter import remote
    remote.install()

You should put this somewhere where it's run early in your project (settings or package's ``__init__.py`` file).

The ``remote.install()`` takes same arguments as ``manhole.install()``. You'll probably only want to use ``verbose=False`` ...


The CLI
=======

::

    usage: hunter-trace [-h] -p PID [-t TIMEOUT] [--gdb] [-s SIGNAL]
                    [OPTIONS [OPTIONS ...]]



positional arguments:
  OPTIONS

optional arguments:
  -h, --help            show this help message and exit
  -p PID, --pid PID     A numerical process id.
  -t TIMEOUT, --timeout TIMEOUT
                        Timeout to use. Default: 1 seconds.
  --gdb                 Use GDB to activate tracing. WARNING: it may deadlock
                        the process!
  -s SIGNAL, --signal SIGNAL
                        Send the given SIGNAL to the process before
                        connecting.

The ``OPTIONS`` are ``hunter.trace()`` arguments.
