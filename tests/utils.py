from hunter import CallPrinter


class DebugCallPrinter(CallPrinter):
    def __init__(self, suffix='', **kwargs):
        self.suffix = suffix
        super(DebugCallPrinter, self).__init__(**kwargs)

    def __call__(self, event):
        self.output("depth={} calls={:<4}", event.depth, event.calls)
        super(DebugCallPrinter, self).__call__(event)

    def output(self, format_str, *args, **kwargs):
        format_str = format_str.replace('\n', '%s\n' % self.suffix)
        super(DebugCallPrinter, self).output(format_str, *args, **kwargs)
