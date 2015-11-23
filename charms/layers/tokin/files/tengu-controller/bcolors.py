"""Helper module for pretty console output"""
class Bcolors(object):
    """Helper class for colored console output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

    @staticmethod
    def cfail(string):
        """print given string in FAIL color"""
        return Bcolors.FAIL + str(string) + Bcolors.ENDC

    @staticmethod
    def cok(string):
        """print given string in OK color"""
        return Bcolors.OKBLUE + str(string) + Bcolors.ENDC
