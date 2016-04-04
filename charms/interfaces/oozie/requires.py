#python3 pylint:disable=c0111
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class OozieRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:oozie}-relation-{joined,changed}')
    def changed(self):
        if self.get_remote('private-address'):
            conv = self.conversation()
            # TODO: Implement new relationship protocol that indicates when oozie is ready
            conv.remove_state('{relation_name}.joined')
            conv.set_state('{relation_name}.ready')


    @hook('{requires:oozie}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.ready')
        conv.remove_state('{relation_name}.joined')


    @property
    def port(self):
        """ Return Oozie port"""
        # TODO: implement new relationship protocol that sends port number
        conv = self.conversation()
        return conv.get_remote('port', str(11000))


    @property
    def private_address(self):
        """ return Oozie private address """
        conv = self.conversation()
        return conv.get_remote('private-address')
