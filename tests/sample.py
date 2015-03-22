if __name__ == "__main__":
    import os
    a = os.path.join('a', 'b')
    def foo():
        return os.path.join('a', 'b')

    foo()
