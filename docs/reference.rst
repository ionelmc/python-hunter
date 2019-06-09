Reference
=========

.. autosummary::

.. highlights:: :ref:`reference:Helpers`

.. autosummary::

    hunter.trace
    hunter.stop
    hunter.wrap
    hunter.And
    hunter.Not
    hunter.Or
    hunter.Q

.. warning::

    The following (Predicates, Actions and Internals) have Cython implementations in modules prefixed with "_".
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

.. highlights:: :ref:`reference:Actions`

.. autosummary::

    hunter.actions.CallPrinter
    hunter.actions.CodePrinter
    hunter.actions.Debugger
    hunter.actions.Manhole
    hunter.actions.VarsPrinter

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

.. autofunction:: hunter.Not

.. autofunction:: hunter.Or

.. autofunction:: hunter.Q

----

Predicates
----------

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

Actions
-------

.. autoclass:: hunter.actions.CallPrinter(stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

.. autoclass:: hunter.actions.CodePrinter(stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

.. autoclass:: hunter.actions.Debugger(klass=pdb.Pdb, **kwargs)
    :members:
    :special-members:

.. autoclass:: hunter.actions.Manhole(**options)
    :members:
    :special-members:

.. autoclass:: hunter.actions.VarsPrinter(name, [name, [name, [...]]], stream=sys.stderr, filename_alignment=40, force_colors=False, repr_limit=512)
    :members:
    :special-members:

----

Internals
---------

Normally these are not used directly. Perhaps just the :class:`hunter.tracer.Tracer` may be used directly for
performance reasons.

.. autoclass:: hunter.event.Event
    :members:
    :special-members:

.. autoclass:: hunter.tracer.Tracer
    :members:
    :special-members: __call__, __enter__, __exit__
