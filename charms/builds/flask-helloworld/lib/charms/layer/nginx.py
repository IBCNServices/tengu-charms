from charmhelpers.core.templating import render
from charmhelpers.core import hookenv
from charmhelpers.core import host

import toml
import os


def load_site():
    if not os.path.isfile('site.toml'):
        return {}

    with open('site.toml') as fp:
        conf = toml.loads(fp.read())

    return conf


def get_app_path():
    site = load_site()
    if 'app_path' in site:
        return site['app_path']
    return '/srv/app'


def configure_site(site, template, **kwargs):
    """ configures vhost

    Arguments:
    site: Site name
    template: template to process in templates/<template.conf>
    **kwargs: additional dict items to append to template variables exposed
              through the site.toml
    """
    hookenv.status_set('maintenance', 'Configuring site {}'.format(site))

    config = hookenv.config()
    context = load_site()
    context['host'] = config['host']
    context['port'] = config['port']
    context.update(**kwargs)
    conf_path = '/etc/nginx/sites-enabled/{}'.format(site)
    if os.path.exists(conf_path):
        os.remove(conf_path)
    render(source=template,
           target=conf_path,
           context=context)
    hookenv.log('Wrote vhost config {} to {}'.format(context, template),
                'info')

    host.service_reload('nginx')
