# Copyright 2014-2015 Canonical Limited.
#
# This file is part of jujubigdata.
#
# jujubigdata is free software: you can redistribute it and/or modify
# it under the terms of the Apache License version 2.0.
#
# jujubigdata is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Apache License for more details.

from . import utils  # noqa
from . import handlers  # noqa

# relations doesn't work with stock charmhelpers and is being phased out in the
# layered charms, so this makes it conditional
try:
    from charmhelpers.core import charmframework  # noqa
except ImportError:
    pass
else:
    from . import relations  # noqa
