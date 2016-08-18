import os, fnmatch, logging
from charmhelpers.core import templating, hookenv, host
from charms.reactive import hook, when, when_all, when_any, when_not, when_none, set_state, remove_state


@when('apache.available')
def setup_tengu_ui():
    settings_path = '/var/www/web-ui/scripts/'

    conf = hookenv.config()
    settings_file = find('*.settings.js', settings_path)
    templating.render(
        source='settings.template',
        target=settings_file,
        perms=420,
        context=conf,
        templates_dir=settings_path
    )

    set_state('apache.start')
    hookenv.status_set('maintenance', 'Starting Apache')

def find(pattern, path):
    for root, dirs, files in os.walk(path):
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                return os.path.join(root, name)
    return None

@when('apache.started')
def started():
    hookenv.status_set('active', 'Ready')
