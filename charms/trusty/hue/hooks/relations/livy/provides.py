
from charms.reactive import hook
from charms.reactive import RelationBase
from charms.reactive import scopes


class LivyProvides(RelationBase):
    scope = scopes.GLOBAL

    @hook('{provides:livy}-relation-{joined,changed}')
    def changed(self):
        self.set_state('{relation_name}.available')

    @hook('{provides:livy}-relation-{broken,departed}')
    def broken(self):
        self.remove_state('{relation_name}.available')

    def configure(self, port):
        relation_info = {
            'port': port,
        }
        for info in relation_info:
            self.set_remote(info)
