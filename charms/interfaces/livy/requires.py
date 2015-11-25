from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class LivyRequires(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['host', 'port']

    @hook('{requires:livy}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('port'):
            conv.set_state('{relation_name}.available')


    @hook('{requires:livy}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')


    @property
    def private_address(self):
        for conv in self.conversations():
            host = conv.get_remote('private-address')
            if host:
                return host


    @property
    def port(self):
        for conv in self.conversations():
            host = conv.get_remote('port')
            if host:
                return host
