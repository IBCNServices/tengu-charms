from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class HdfsRequires(RelationBase):
    scope = scopes.GLOBAL
    auto_accessors = ['host', 'port']

    @hook('{requires:dfs}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('private-address'):
            conv.set_state('hdfs.available')


    @hook('{requires:dfs}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('hdfs.available')


    @property
    def private_address(self):
        for conv in self.conversations():
            host = conv.get_remote('private-address')
            if host:
                return host
