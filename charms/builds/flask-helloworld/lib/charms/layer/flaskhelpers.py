import os

from charms.reactive import (
    set_state,
)

from charmhelpers.core import hookenv
from charmhelpers.core import host
from subprocess import call, Popen

config = hookenv.config()

def install_dependencies(pathWheelhouse, pathRequirements):
	call(["pip", "install", "--no-index", "--find-links=" + pathWheelhouse, "-r", pathRequirements])

# Should be used by the layer including the flask layer
def start_api(path, app, port):
	if os.path.exists("/home/ubuntu/flask-config"):
		file = open("/home/ubuntu/flask-config", "w")
		file.write(path + " " + app)
		file.close()
		start(path, app, port)

# Used by the flask layer to restart when flask-port changes
def restart_api(port):
	if os.path.exists("/home/ubuntu/flask-config"):
		file = open("/home/ubuntu/flask-config", "r")
		line = file.readline()
		if line != "":
			path, app = line.split()
			start(path, app, port)

def start(path, app, port):
	if config["nginx"]:
		start_api_gunicorn(path, app, port)
	else:		
		path = path.rstrip('/')
		Popen(["python3", path])	
		set_state('flask.running')

def start_api_gunicorn(path, app, port):
	saveWdir = os.getcwd()
	path = path.rstrip('/')
	#info[0] = path to project
	#info[1] = main
	info = path.rsplit('/', 1)
	#remove .py from main
	main = info[1].split('.', 1)[0] 

	file = open(info[0] + "/wsgi.py", "w")
	file.write("from " + main + " import " + app + "\n")
	file.write('if __name__ == "__main__":' + "\n")
	file.write('    ' + app + '.run()')
	file.close()

	os.chdir(info[0])
	Popen(["gunicorn", "--bind", "0.0.0.0:" + str(port), "wsgi:" + app])
	os.chdir(saveWdir)
	set_state('flask.running')