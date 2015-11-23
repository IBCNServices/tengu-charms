"""Helper module for pretty console output"""
#pylint: disable=c0111
HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

def debug(text):
    print 'DEBUG: {}'.format(text)

def okblue(text):
    print OKBLUE + str(text) + ENDC

def okgreen(text):
    print OKGREEN + str(text) + ENDC

def okwhite(text):
    print str(text)

def warn(text):
    print OKGREEN + str(text) + ENDC

def fail(reason, exception=None):
    if exception:
        print str(exception)
    print '{}ERROR: {}{}'.format(FAIL, reason, ENDC)
    exit(1)
