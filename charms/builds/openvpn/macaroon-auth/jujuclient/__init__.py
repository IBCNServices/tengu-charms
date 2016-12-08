"""
Juju Client
-----------

A simple synchronous python client for the juju-core websocket api.

Supports python 2.7 & 3.4+.

See README for example usage.
"""
# License: LGPLv3
# Author: Kapil Thangavelu <kapil.foss@gmail.com>

import logging
import websocket

# Import juju1 Enviroment into top-level namespace for back-compat
from .juju1.environment import Environment  # noqa


# There are two pypi modules with the name websocket (python-websocket
# and websocket) We utilize python-websocket, sniff and error if we
# find the wrong one.
try:
    websocket.create_connection
except AttributeError:
    raise RuntimeError(
        "Expected 'python-websocket' egg "
        "found incompatible gevent 'websocket' egg")


websocket.logger = logging.getLogger("websocket")
log = logging.getLogger("jujuclient")
