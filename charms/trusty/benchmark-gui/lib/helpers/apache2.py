import os


APACHE2_CONF_DIR = '/etc/apache2'
APACHE2_SITES_AVAIL = os.path.join(APACHE2_CONF_DIR, 'sites-available')
APACHE2_SITES_ENABLED = os.path.join(APACHE2_CONF_DIR, 'sites-enabled')


def enable_site(site):
    if not os.path.isfile(os.path.join(APACHE2_SITES_AVAIL, site)):
        if os.path.isfile(os.path.join(APACHE2_SITES_AVAIL, '%s.conf' % site)):
            site = '%s.conf' % site
        else:
            raise IOError('%s is not an available site' % site)

    src = os.path.join(APACHE2_SITES_AVAIL, site)
    dst = os.path.join(APACHE2_SITES_ENABLED, site)
    if os.path.exists(dst):
        if not os.path.realpath(dst) == src:
            raise IOError('%s already exists, but is not %s' % (dst, src))
        return

    return os.symlink(src, dst)


def disable_site(site):
    if not os.path.isfile(os.path.join(APACHE2_SITES_ENABLED, site)):
        if os.path.isfile(os.path.join(APACHE2_SITES_ENABLED, '%s.conf' % site)):
            site = '%s.conf' % site
        else:
            raise IOError('%s is not enabled' % site)
    site_path = os.path.join(APACHE2_SITES_ENABLED, site)

    return os.unlink(site_path)
