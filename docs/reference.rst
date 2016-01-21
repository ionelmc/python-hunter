Reference
=========

.. contents::
    :local:
    :backlinks: none

Functions
---------

.. autofunction:: hunter.trace(*predicates, clear_env_var=False, action=CodePrinter, actions=[])

.. autofunction:: hunter.stop()

.. autofunction:: hunter.Q

Predicates
----------

.. autoclass:: hunter.Query
    :members:
    :special-members:

.. autoclass:: hunter.When
    :members:
    :special-members:

.. autofunction:: hunter.And

.. autofunction:: hunter.Or

Actions
-------

.. autoclass:: hunter.CallPrinter(stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

.. autoclass:: hunter.CodePrinter(stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

.. autoclass:: hunter.Debugger(klass=pdb.Pdb, **kwargs)
    :members:
    :special-members:

.. autoclass:: hunter.VarsPrinter(name, [name, [name, [...]]], globals=False, stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

Objects
-------

.. autoclass:: hunter.event.Event
    :members:
