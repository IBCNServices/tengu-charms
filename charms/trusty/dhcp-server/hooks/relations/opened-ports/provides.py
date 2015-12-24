#pylint:disable=c0111
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes

import subprocess

class OpenedPortsProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{requires:opened-ports}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.available')
        self.configure()


    @hook('{requires:opened-ports}-relation-{departed,broken}')
    def broken(self):
        self.remove_state('{relation_name}.available')

    def configure(self):
        self.set_remote(
            'opened-ports', subprocess.check_output(['opened-ports'])
        )
