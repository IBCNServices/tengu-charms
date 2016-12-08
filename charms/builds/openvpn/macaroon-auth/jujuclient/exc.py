import pprint

# py 2 and py 3 compat
try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


class EnvironmentNotBootstrapped(Exception):

    def __init__(self, environment):
        self.environment = environment

    def __str__(self):
        return "Environment %s is not bootstrapped" % self.environment


class AlreadyConnected(Exception):
    pass


class LoginRequired(Exception):
    pass


class TimeoutError(StopIteration):
    pass


class UnitErrors(Exception):

    def __init__(self, errors):
        self.errors = errors


class EnvError(Exception):

    def __init__(self, error):
        self.error = error
        self.message = error.get('Error') or error.get('error')
        # Call the base class initializer so that this exception can be pickled
        # (see http://bugs.python.org/issue1692335).
        super(EnvError, self).__init__(error)

    def __str__(self):
        stream = StringIO()
        pprint.pprint(self.error, stream, indent=4)
        return "<Env Error - Details:\n %s >" % (
            stream.getvalue())
