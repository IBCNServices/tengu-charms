#python3 pylint:disable=c0111
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes



class OozieRequires(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:opened-ports}-relation-{joined,changed}')
    def changed(self):
        conv = self.conversation()
        if conv.get_remote('private-address'):
            # TODO: Implement new relationship protocol that indicates when oozie is ready
            conv.set_state('{relation_name}.available')


    @hook('{requires:opened-ports}-relation-{departed,broken}')
    def broken(self):
        conv = self.conversation()
        conv.remove_state('{relation_name}.available')


    @property
    def port(self):
        """ Return Oozie port"""
        conv = self.conversation()
        # TODO: implement new relationship protocol that sends port number
        return conv.get_remote('port', str(11000))

    @property
    def private_address(self):
        """ return Oozie private address """
        conv = self.conversation()
        return conv.get_remote('private-address')
