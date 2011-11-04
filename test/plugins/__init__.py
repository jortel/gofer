
class BadException(Exception):
    def __init__(self):
        self.cat = Cat()

class MyError(Exception):
    def __init__(self, a, b):
        Exception.__init__(self, a)
        self.b = b