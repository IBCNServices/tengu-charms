# pylint: disable=c0111,c0103

import base64
from os.path import expanduser
import yaml


home = expanduser("~")
content = {'sojobo-api': {}}
with open('{}/.local/share/juju/controllers.yaml'.format(home), 'r') as f:
    content['sojobo-api']['controllers_yaml'] = base64.b64encode(bytes(f.read(), "utf-8"))
with open('{}/.local/share/juju/credentials.yaml'.format(home), 'r') as f:
    content['sojobo-api']['credentials_yaml'] = base64.b64encode(bytes(f.read(), "utf-8"))
with open('{}/.local/share/juju/clouds.yaml'.format(home), 'r') as f:
    content['sojobo-api']['clouds_yaml'] = base64.b64encode(bytes(f.read(), "utf-8"))
content['sojobo-api']['juju-controller'] = input('What JuJu controller are you using?: ')
content['sojobo-api']['controller-type'] = input('What type of controller is it?: ')
content['sojobo-api']['juju-username'] = input('What is the juju username?: ')
content['sojobo-api']['juju-password'] = input('And the password?: ')
correct_controller_type = False
while not correct_controller_type:
    if content['sojobo-api']['controller-type'] == 'maas':
        content['sojobo-api']['maas-user'] = input('What is your MAAS username?: ')
        content['sojobo-api']['maas-password'] = input('And the password?: ')
        content['sojobo-api']['maas-api-key'] = input('And the corresponding API-key?: ')
        content['sojobo-api']['maas-url'] = input('What is your MAAS url/endpoint?: ')
        correct_controller_type = True
    elif content['sojobo-api']['controller-type'] == 'aws':
        content['sojobo-api']['aws-access-key-id'] = input('What is your Amazon Web Service access key?: ')
        content['sojobo-api']['aws-secret-access-key'] = input('And the corresponding secret key?: ')
        content['sojobo-api']['aws-url'] = input('What is your AWS url?: ')
        correct_controller_type = True
    else:
        content['sojobo-api']['controller-type'] = input('Incorrect controller value. Options are maas or aws')
with open('config_values.yaml', 'w') as outfile:
    yaml.dump(content, outfile, default_flow_style=False)
