Reference
=========

.. _helpers-summary:

.. highlights:: :ref:`Helpers`

.. autosummary::

    hunter.trace
    hunter.stop
    hunter.wrap
    hunter.And
    hunter.Backlog
    hunter.From
    hunter.Not
    hunter.Or
    hunter.Q

.. highlights:: :ref:`Actions`

.. autosummary::

    hunter.actions.CallPrinter
    hunter.actions.CodePrinter
    hunter.actions.ColorStreamAction
    hunter.actions.Debugger
    hunter.actions.ErrorSnooper
    hunter.actions.Manhole
    hunter.actions.StackPrinter
    hunter.actions.VarsPrinter
    hunter.actions.VarsSnooper

.. warning::

    The following (Predicates and Internals) have Cython implementations in modules prefixed with "_".
    They should be imported from the ``hunter`` module, not ``hunter.something`` to be sure you get the best available implementation.

.. highlights:: :ref:`Predicates`

.. autosummary::

    hunter.predicates.And
    hunter.predicates.Backlog
    hunter.predicates.From
    hunter.predicates.Not
    hunter.predicates.Or
    hunter.predicates.Query
    hunter.predicates.When

.. highlights:: :ref:`Internals`

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

.. autofunction:: hunter.Backlog

.. autofunction:: hunter.From

.. autofunction:: hunter.Not

.. autofunction:: hunter.Or

.. autofunction:: hunter.Q


----

Actions
-------

.. autoclass:: hunter.actions.CallPrinter(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.CodePrinter(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.ColorStreamAction(stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.Debugger(klass=pdb.Pdb, **kwargs)
    :members:
    :special-members:

.. autoclass:: hunter.actions.ErrorSnooper(max_events=50, max_depth=1, stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
    :members:
    :special-members:

.. autoclass:: hunter.actions.Manhole(**options)
    :members:
    :special-members:

.. autoclass:: hunter.actions.StackPrinter(depth=15, limit=2, stream=sys.stderr, force_colors=False, force_pid=False, filename_alignment=40, thread_alignment=12, pid_alignment=9, repr_limit=1024, repr_func='safe_repr')
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

    Note that:

    * Every predicate except :class:`~hunter.predicates.When` has a :ref:`helper <helpers-summary>` importable directly from the
      ``hunter`` package.
    * Ideally you'd use the helpers instead of these to get the best available implementation, extra validation and
      better argument handling.

.. autoclass:: hunter.predicates.And
    :members:
    :special-members:

.. autoclass:: hunter.predicates.Backlog
    :members:
    :special-members:

.. autoclass:: hunter.predicates.From
    :members:
    :special-members:

.. autoclass:: hunter.predicates.Not
    :members:
    :special-members:

.. autoclass:: hunter.predicates.Or
    :members:
    :special-members:

.. autoclass:: hunter.predicates.Query
    :members:
    :special-members:

.. autoclass:: hunter.predicates.When
    :members:
    :special-members:

----

Internals
---------

.. warning::

    These have Cython implementations in modules prefixed with "_".
    They should be imported from the ``hunter`` module, not ``hunter.something`` to be sure you get the best available implementation.

Normally these are not used directly. Perhaps just the :class:`~hunter.tracer.Tracer` may be used directly for
performance reasons.

.. autoclass:: hunter.event.Event
    :members:
    :special-members:

.. autoclass:: hunter.tracer.Tracer
    :members:
    :special-members:
