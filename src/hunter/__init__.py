try:
    from ._cython_impl import Q, When, And, Or, CodePrinter, Debugger, VarsPrinter, trace, stop
except ImportError:
    from ._python_impl import Q, When, And, Or, CodePrinter, Debugger, VarsPrinter, trace, stop

__version__ = "0.6.0"
__all__ = 'Q', 'When', 'And', 'Or', 'CodePrinter', 'Debugger', 'VarsPrinter', 'trace', 'stop'
