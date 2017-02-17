from charmhelpers.core import hookenv
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class InfluxdbApi(RelationBase):
    # We expect multiple, separate services to be related, but all units of a
    # given service will share the same database name and connection info.
    # Thus, we use SERVICE scope and will have one converstaion per service.
    scope = scopes.SERVICE

    @hook('{provides:influxdb-api}-relation-{joined,changed}')
    def changed(self):
        for conversation in self.conversations():
            hookenv.log("Setting api.available for conversation: {}"
                        .format(conversation))
            conversation.set_state('{relation_name}.api.available')

    @hook('{provides:influxdb-api}-relation-{departed,broken}')
    def gone(self):
        for conversation in self.conversations():
            hookenv.log("Removing api.available for conversation: {}"
                        .format(conversation))
            conversation.remove_state('{relation_name}.api.available')

    def configure(self, port, username, password):
        hookenv.log('setting up influx')
        config = {
            'hostname': hookenv.unit_get('private-address'),
            'port': port,
            'user': username,
            'password': password,
        }
        for conversation in self.conversations():
            hookenv.log("Setting up influx for conversation: {}"
                        .format(conversation))
            conversation.set_remote(**config)
