#!/usr/bin/env python

__author__ = 'thatcher'
import sys
from docker_container_runner import utils
from docker_container_runner.manager import Application, DockerDaemon, Hipache



try:
    stream = open(sys.argv[1])
except:
    print \
    """
    usage:

    dcr.py [configfile.yml]
    """
    sys.exit()

settings = utils.read_settings('settings.yml')
directives = utils.read_appconfig(sys.argv[1])


print directives

def create_applications():
    applications = []
    for key, value in directives.items():
        application = Application(key)
        application.set_configuration(value)
        applications.append(application)

    print applications

    return applications

def connect_daemons(settings):

    daemons = []

    for host in settings:
        daemons.append(DockerDaemon(host))

    return daemons


def main(application):
    """
    start it
    """
    # connect to the docker daemon
    # daemon = DockerDaemon(DAEMON_HOST, DAEMON_PORT)

    target = 'default'
    daemons = connect_daemons(settings[target]['daemons'])
    daemon = daemons[0]

    # create the container on the daemon
    containers = application.create_all(daemons)

    # start the container
    results = application.start_all(containers)

    for container in containers:

        # inspect the container
        container = application.get_details(container)

        # register the container to the frontend
        backend_port = application.config['c_ports'].keys()[0]
        frontend = "{}.{}".format(application.name, settings['default']['base_domain'][0])

        for hipache_config in settings['default']['hipaches']:
            hipache_host, hipache_port = hipache_config.split(':')

            hipache = Hipache(hipache_host, int(hipache_port))

            application.register(hipache, frontend, backend_port=backend_port, container=container)




# setup the application from the config file
applications = create_applications()

main(applications[0])

