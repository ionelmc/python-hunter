Reference
=========

.. autosummary::

.. highlights:: :ref:`reference:Helpers`

.. autosummary::

    hunter.trace
    hunter.stop
    hunter.wrap
    hunter.And
    hunter.From
    hunter.Not
    hunter.Or
    hunter.Q

.. highlights:: :ref:`reference:Actions`

.. autosummary::

    hunter.actions.CallPrinter
    hunter.actions.CodePrinter
    hunter.actions.ColorStreamAction
    hunter.actions.Debugger
    hunter.actions.Manhole
    hunter.actions.VarsPrinter
    hunter.actions.VarsSnooper

.. warning::

    The following (Predicates and Internals) have Cython implementations in modules prefixed with "_".
    Should be imported from the ``hunter`` module, not ``hunter.something`` to be sure you get the right implementation.

.. highlights:: :ref:`reference:Predicates`

.. autosummary::

    hunter.predicates.Query
    hunter.predicates.From
    hunter.predicates.When
    hunter.predicates.And
    hunter.predicates.Not
    hunter.predicates.Or
    hunter.predicates.Query

.. highlights:: :ref:`reference:Internals`

.. autosummary::

    hunter.event.Event
    hunter.tracer.Tracer

|
|
|

----

Helpers
-------

.. autofunction:: hunter.trace(*predicates, clear_env_var=False, action=CodePrinter, actions=[], **kwargs)

.. autofunction:: hunter.stop()

.. autofunction:: hunter.wrap

.. autofunction:: hunter.And

.. autofunction:: hunter.From

.. autofunction:: hunter.Not

.. autofunction:: hunter.Or

.. autofunction:: hunter.Q

----

Actions
-------

.. autoclass:: hunter.actions.ColorStreamAction(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.CallPrinter(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.CodePrinter(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.Debugger(klass=pdb.Pdb, **kwargs)
    :members:
    :special-members:

.. autoclass:: hunter.actions.Manhole(**options)
    :members:
    :special-members:

.. autoclass:: hunter.actions.VarsPrinter(name, [name, [name, [...]]], stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.VarsSnooper(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

----

Predicates
----------

.. warning::

    These have Cython implementations in modules prefixed with "_".
    Should be imported from the ``hunter`` module, not ``hunter.something`` to be sure you get the right implementation.

.. autoclass:: hunter.predicates.Query
    :members:
    :special-members: __call__

.. autoclass:: hunter.predicates.When
    :members:
    :special-members: __call__

.. autoclass:: hunter.predicates.From
    :members:
    :special-members: __call__

.. autoclass:: hunter.predicates.And
    :members:
    :special-members: __call__

.. autoclass:: hunter.predicates.Or
    :members:
    :special-members: __call__

.. autoclass:: hunter.predicates.Not
    :members:
    :special-members: __call__

----

Internals
---------

.. warning::

    These have Cython implementations in modules prefixed with "_".
    Should be imported from the ``hunter`` module, not ``hunter.something`` to be sure you get the right implementation.

Normally these are not used directly. Perhaps just the :class:`~hunter.tracer.Tracer` may be used directly for
performance reasons.

.. autoclass:: hunter.event.Event
    :members:
    :special-members:

.. autoclass:: hunter.tracer.Tracer
    :members:
    :special-members: __call__, __enter__, __exit__
