# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import subprocess
from glob import glob


def pre_install():
    """
    Do any setup required before the install hook.
    """
    install_pip()
    install_bundled_resources()


def install_pip():
    subprocess.check_call(['apt-get', 'install', '-yq', 'python-pip', 'bzr'])


def install_bundled_resources():
    """
    Install the bundled resources libraries.
    """
    archives = glob('resources/python/*')
    subprocess.check_call(['pip', 'install'] + archives)
