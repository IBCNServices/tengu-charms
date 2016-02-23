from jujubigdata.utils import DistConfig
from jujubigdata.handlers import HadoopBase
from charms import layer


def get_dist_config(required_keys=None):
    required_keys = required_keys or [
        'vendor', 'hadoop_version', 'packages',
        'groups', 'users', 'dirs', 'ports']
    dist = DistConfig(filename='dist.yaml',
                      required_keys=required_keys)
    opts = layer.options('hadoop-base')
    for key in ('hadoop_version',):
        if key in opts:
            dist.dist_config[key] = opts[key]
    for key in ('packages', 'groups'):
        if key in opts:
            dist.dist_config[key] = list(set(dist.dist_config[key]) | set(opts[key]))
    for key in ('users', 'dirs', 'ports'):
        if key in opts:
            dist.dist_config[key].update(opts[key])
    return dist


def get_hadoop_base():
    return HadoopBase(get_dist_config())
