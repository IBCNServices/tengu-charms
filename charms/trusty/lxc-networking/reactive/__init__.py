try:
  proc = subprocess.Popen([self._filepath, '--test'], stdout=subprocess.PIPE, env=os.environ)
except OSError as oserr:
  if oserr.errno == errno.ENOEXEC:
    raise BrokenHandlerException("Failed to execute external handler at '{}'."
                                 " Either the shebang is wrong or a non-handler is marked as executable.".format(self._filepath) )
