import docker
from docker import APIError
import redis
import bgtunnel
from bgtunnel import SSHTunnelError
import sys
from requests.exceptions import ConnectionError


class DockerDaemon:
    host = ""
    connection = {}

    def __init__(self, host, ssh=True):
        self.host_name, self.host_port = host.split('//')[1].split(":")
        self.host = host

        if ssh:
            forwarder = self.connect_channel(self.host_name, self.host_port)
            entrypoint = "http://{}".format(forwarder.bind_string)
        else:
            entrypoint = "http://{}:{}".format(self.host_name, self.host_port)    

        print entrypoint
        self.connection = docker.Client(base_url=entrypoint, version="1.7")

    def connect_channel(self, host, port):
        try:
            forwarder = bgtunnel.open(ssh_user="docker",
                                      ssh_address=host,
                                      host_port=port)
        except SSHTunnelError as ex:
            sys.exit(ex)

        return forwarder


class Hipache:
    def __init__(self, host, port):
        self.connection = redis.StrictRedis(host=host, port=port, db=0)


class Container:

    daemon = None
    config = None

    def __init__(self, config, daemon):
        self.config = config
        self.daemon = daemon

    @property
    def details(self):
        try:
            details = self.daemon.connection.inspect_container(self.config['release_name'])
            return details
        except APIError as ex:
            print ex
            return None
        except ConnectionError as ex:
            print "Failed to connect to daemon ", ex
            sys.exit(1)

    @property
    def status(self):
        try:
            running = self.details['State']['Running']
            if running:
                status = "running"
            else:
                status = "stopped"
        except Exception:
            status = "doesnotexist"
        return status

    def pull(self):
        repository = self.config['image']
        print "trying to pull {} on {}".format(repository, self.daemon.host_name)

        try:
            results = self.daemon.connection.pull(repository, tag=None)
            print results
            return results
        except APIError as ex:
            print ex
            return None

    def get_image(self):
        return self.daemon.connection.images(name=self.config['image'])

    def create(self):
        print "creating container on {}".format(self.daemon.host_name)
        try:
            self.daemon.connection.create_container(self.config['image'],
                                                self.config['command'],
                                                volumes=self.config['vols'],
                                                ports=self.config['c_ports'],
                                                environment=self.config['env'],
                                                detach=True,
                                                name=self.config['release_name'])
        except APIError as ex:
            print "failed to create container: ", ex
            return 1, "Failed to create container", ex


    def start(self):
        """
        starts one of the containers of this application
        """
        print "starting container on {}".format(self.daemon.host_name)
        if not self.details['State']['Running'] is True:
            result = self.daemon.connection.start(self.config['release_name'],
                                                  port_bindings=self.config['s_ports'],
                                                  binds=self.config['binds'])
            return result
        else:
            return None

    def stop(self):
        print "stopping container on {}".format(self.daemon.host_name)
        if not self.details['State']['Running'] is False:
            result = self.daemon.connection.stop(self.config['release_name'])
            return result
        else:
            return None


class Application:

    config = {}
    container = {}
    containers = {}
    results = []

    def __init__(self, name, config, settings, cluster="default"):
        self.name = name
        self.config = config
        self.settings = settings
        
        use_ssh = settings[cluster].get('use_ssh', True)
        self.daemons = self.connect_daemons(self.settings[cluster]['daemons'], ssh=use_ssh)

        release_name = self.config.get('release_name', None)
        if not release_name:
            print "error, release name not set, check your yml file"


    def connect_daemons(self, daemon_list, ssh):
        daemons = []
        for host in daemon_list:
            daemons.append(DockerDaemon(host, ssh))
        return daemons

    def get_containers(self):
        """
        get containers from the existing container dictionary index by daemon hostname
        or create new containers and add them to this dictionary
        """
        for daemon in self.daemons:
            try:
                container = self.containers[daemon.host]
            except KeyError:
                container = Container(self.config, daemon)
                self.containers[daemon.host] = container
        return self.containers

    def create_containers(self):
        """
        creates the container specified in the configuration
        :param daemon: the daemon to connect to
        """
        status = []
        for key, container in self.containers.items():
            result = container.create()
            status.append(result)

        return status

    def pull_image(self):
        for key, container in self.containers.items():
            container.pull()

    def start_containers(self):
        """
        starts container on all hosts
        """
        for key, container in self.containers.items():
            container.start()
        return "success"

    def stop_containers(self):
        """
        starts container on all hosts
        """
        for key, container in self.containers.items():
            container.stop()
        return "success"

    def get_details(self, container):
        """
        get the container details
        """
        container['details'] = container['daemon'].connection.inspect_container(self.config['release_name'])
        return container

    def get_status(self):
        status = []
        for key, container in self.containers.items():
            print "container {release_name} on host {daemon}, Running={status}" \
                .format(release_name=container.config['release_name'],
                        daemon=container.daemon.host_name,
                        status=container.status)
            status.append(container.status)
        return status

    def register(self):
        """
        registers the container to a specified frontend
        """

        backend_port = self.config['c_ports'].keys()[0]
        frontend = "{}.{}".format(self.name, self.settings['default']['base_domain'][0])
        front = "frontend:{}".format(frontend)

        for name, container in self.containers.items():
            port = container.details[u'NetworkSettings'][u'Ports'][backend_port][0][u'HostPort']
            print port

            # backend_address = container.details['host'].split('//')[1].split(":")[0]
            backend_address = container.daemon.host_name
            backend = "http://{}:{}".format(backend_address, port)

            self.write(front, backend)

    def write(self, front, backend):

        for hipache_config in self.settings['default']['hipaches']:
            hipache_host, hipache_port = hipache_config.split(':')
            hipache = Hipache(hipache_host, int(hipache_port))

            # check length
            length = hipache.connection.llen(front)
            if not length > 0:
                hipache.connection.rpush(front, self.name)

            hipache.connection.rpush(front, backend)

            hipache_config = hipache.connection.lrange(front, 0, -1)
            print hipache_config

    def unregister(self, frontend):
        """
        unregisters the container from a specified frontend
        """
