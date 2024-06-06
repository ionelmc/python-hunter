#!/usr/bin/env python

testdata = """
stdlib=False
~Q(kind="line"),~Q(module_in=["six","pkg_resources"]),~Q(filename=""),stdlib=False
stdlib=False,Q(filename_contains='venv')
"""


class ParamParser:
    """
    Splits a param string into list of strings.

    The logic is basically to split by commas, ignoring commas inside parens.
    """
    def parse(self, string):
        # make object variables for debugging
        self.raw = string
        self.parsed = []
        if not self.raw:
            pass  # print("empty param string")
            return self.parsed

        self.parsed = []
        self.current = ''
        self.embrace = False  # True if parsing inside parens
        # scan for either comma or brace
        for i in self.raw:
            if self.embrace:
                self.current += i
                if i == ')':
                    self.embrace = False
                continue

            # from here we are not in parens (yet)
            if i == '(':
                self.current += i
                self.embrace = True
            elif i == ',':
                if not self.current:
                    pass  # print("hey, that's a missing param between commas")
                else:
                    self.parsed.append(self.current)
                    self.current = ''
            else:  # i is not ( or ,
                self.current += i

        else:
            if not self.current:
                pass  # print("empty param after last comma")
            else:
                self.parsed.append(self.current)
                self.current = ''
        return self.parsed


if __name__ == '__main__':
    for line in testdata.splitlines():
        print(line)
        params = ParamParser().parse(line)
        if not params:
            print("  %s" % params)
        else:
            for param in params:
                print("  %s" % param)
