from jujubigdata.utils import DistConfig
from charms import layer


def get_dist_config():
    return DistConfig(data=layer.options('hadoop-client'))
