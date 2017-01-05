from charmhelpers.core import hookenv
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class HttpProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:http}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.available')

    @hook('{provides:http}-relation-{broken,departed}')
    def broken(self):
        self.remove_state('{relation_name}.available')

    def configure(self, port, private_address=None, hostname=None):
        if not hostname:
            hostname = hookenv.unit_get('private-address')
        if not private_address:
            private_address = hookenv.unit_get('private-address')
        relation_info = {
            'hostname': hostname,
            'private-address': private_address,
            'port': port,
        }
        self.set_remote(**relation_info)
