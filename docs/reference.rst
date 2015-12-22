Reference
=========

.. automodule:: hunter

    .. rubric:: Functions

    .. autosummary::
        :nosignatures:

        hunter.trace
        hunter.stop
        hunter.Q

    .. rubric:: Predicates

    .. autosummary::
        :nosignatures:

        hunter.Query
        hunter.When
        hunter.And
        hunter.Or

    .. rubric:: Actions

    .. autosummary::
        :nosignatures:

        hunter.CodePrinter
        hunter.Debugger
        hunter.VarsPrinter

    .. rubric:: Objects

    .. autosummary::
        :nosignatures:

        hunter.event.Event

.. autofunction:: hunter.trace(*predicates, clear_env_var=False, action=CodePrinter, actions=[])

.. autofunction:: hunter.stop()

.. autofunction:: hunter.Q

.. autoclass:: hunter.Query
    :members:
    :special-members:

.. autoclass:: hunter.When
    :members:
    :special-members:

.. autoclass:: hunter.And
    :members:
    :special-members:

.. autoclass:: hunter.Or
    :members:
    :special-members:

.. autoclass:: hunter.CodePrinter
    :members:
    :special-members:

.. autoclass:: hunter.Debugger
    :members:
    :special-members:

.. autoclass:: hunter.VarsPrinter
    :members:
    :special-members:

.. autoclass:: hunter.event.Event
    :members:


