import yaml
import base64
from os.path import expanduser


home = expanduser("~")
with open('{}/.local/share/juju/controllers.yaml'.format(home), 'r') as f:
    b64controllers = base64.b64encode(f.read())
with open('{}/.local/share/juju/credentials.yaml'.format(home), 'r') as f:
    b64credentials = base64.b64encode(f.read())
with open('{}/.local/share/juju/clouds.yaml'.format(home),'r') as f:
    b64clouds = base64.b64encode(f.read())
content = {'juju2-client': {
                'controllers_yaml': b64controllers,
                'credentials_yaml': b64credentials,
                'clouds_yaml': b64clouds }}
with open('config_values.yaml', 'w') as outfile:
    yaml.dump(content, outfile, default_flow_style=False)
