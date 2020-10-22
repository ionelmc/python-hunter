from inspect import CO_VARKEYWORDS


def foo(a, (b,), (c, d), (e, (f, g), h)):
    print(a, b, c, d, e, f, g , h)

if __name__ == "__main__":
    foo(1, (2, ), (3, 4), (5, (6, 7), 8))

    import dis
    dis.dis(foo)

    asdf
    def _get_unpacked_arguments(co_code, co_cellvars, position):
        op = ord(co_code[position])
        op_name = dis.opname[op]
        if op_name == 'UNPACK_SEQUENCE':
            value = ord(co_code[position]) + ord(co_code[position + 1]) * 256
        print(op_name, value)

    class get_arguments(object):
        def __init__(self, code):
            self.co_varnames = code.co_varnames
            self.co_argcount = code.co_argcount
            self.co_code = code.co_code
            self.co_flags = code.co_flags
            self.position = 0

        def _get_op_arg(self):
            value = ord(self.co_code[self.position]) + ord(self.co_code[self.position + 1]) * 256
            self.position += 2
            return value

        def _get_op(self):
            op = dis.opname[ord(self.co_code[self.position])]
            self.position += 1
            return op

        def _get_unpacked_arguments(self):
            value = self._get_op_arg()
            for _ in range(value):
                op = self._get_op()
                if op == 'STORE_FAST':
                    value = self._get_op_arg()
                    yield self.co_varnames[value]
                elif op == 'UNPACK_SEQUENCE':
                    yield list(self._get_unpacked_arguments())

        def _clean_name(self, name):
            if isinstance(name, str):
                return name
            elif len(name) > 1:
                return '(%s)' % ', '.join(self._clean_name(i) for i in name)
            else:
                return '(%s,)' % ', '.join(self._clean_name(i) for i in name)

        def __iter__(self):
            for arg in self.co_varnames[:self.co_argcount]:
                names = None
                if arg.startswith('.'):
                    while self.position + 3 < len(self.co_code):
                        op = self._get_op()
                        value = self._get_op_arg()
                        if op == 'LOAD_FAST' and self.co_varnames[value] == arg:
                            op = self._get_op()
                            if op == 'UNPACK_SEQUENCE':
                                names = list(self._get_unpacked_arguments())
                                break
                if names is None:
                    yield '', arg, arg
                else:
                    yield '', arg, self._clean_name(names)
            if self.co_flags & CO_VARKEYWORDS:
                arg = self.co_varnames[self.co_argcount]
                yield '**', arg, arg


    print(list(get_arguments(foo.func_code)))
