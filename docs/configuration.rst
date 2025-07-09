=============
Configuration
=============

Default predicates and action kwargs defaults can be configured via a ``PYTHONHUNTERCONFIG`` environment variable.

All the :ref:`actions` kwargs:

* ``klass``
* ``stream``
* ``force_colors``
* ``force_pid``
* ``filename_alignment``
* ``thread_alignment``
* ``pid_alignment``
* ``repr_limit``
* ``repr_func``

Example::

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
