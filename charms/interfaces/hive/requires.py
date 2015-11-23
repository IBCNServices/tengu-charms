from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class HiveRequires(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['host', 'port']

    @hook('{requires:hive}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('private-address'):
            # this unit's conversation has a port, so
            # it is part of the set of available units
            conv.set_state('hadoop.hive.available')


    @hook('{requires:hive}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('hadoop.hive.available')

    @property
    def private_address(self):
        for conv in self.conversations():
            host = conv.get_remote('private-address')
            if host:
                return host
