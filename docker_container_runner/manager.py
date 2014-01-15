import docker
from docker import APIError
import redis

import sys
from requests.exceptions import ConnectionError
import re
from utils import create_tunnel


class DockerDaemon:
    host = ""
    connection = {}

    def __init__(self, host, registry_login, ssh_user, ssh=True):
        try:
            protocol, hostname = host.split('//')
        except ValueError:
            hostname = host

        self.host_name, self.host_port = hostname.split(":")
        self.host = host
        self.registry_login = registry_login
        self.ssh_user = ssh_user

        if ssh:
            forwarder = create_tunnel(self.host_name, self.host_port, ssh_user)
            entrypoint = "http://{}".format(forwarder.bind_string)
        else:
            entrypoint = "http://{}:{}".format(self.host_name, self.host_port)    

        self.connection = docker.Client(base_url=entrypoint, version="1.7")

    def login(self):
        """
        Logs in to the registry
        """
        try:
            username, password, email = self.registry_login.split(":")
        except BaseException as ex:
            sys.exit("error parsing registry_settings: {}".format(ex))

        print "trying to login to the public index using user {}".format(username)

        result = self.connection.login(username=username, password=password, email=email)

        # print result
        return result


class Hipache:
    def __init__(self, host, redis_port, ssh_user, use_ssh=True):
        """
        Setup the hipache connection
        """

        if use_ssh:
            forwarder = create_tunnel(host=host, port=redis_port, ssh_user=ssh_user)
            self.connection = redis.StrictRedis(host=forwarder.bind_address, port=forwarder.bind_port, db=0)
        else:
            self.connection = redis.StrictRedis(host=host, port=redis_port, db=0)


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
        print "starting to pull {} on {}".format(repository, self.daemon.host_name)

        try:
            self.daemon.login()
            result = self.daemon.connection.pull(repository, tag=None)
            print result
            return result
        except APIError as ex:
            print ex
            return ex

        print "pull complete"

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
        if self.details is None:
            return None
        if not self.details['State']['Running'] is True:
            result = self.daemon.connection.start(self.config['release_name'],
                                                  port_bindings=self.config['s_ports'],
                                                  binds=self.config['binds'],
                                                  links=self.config['links'])
            return result
        else:
            return None

    def stop(self):
        print "stopping container on {}".format(self.daemon.host_name)
        if self.details is None:
            return 1, "container does not exist"
        if not self.details['State']['Running'] is False:
            result = self.daemon.connection.stop(self.config['release_name'])
            return result
        else:
            return None  # container was not running in the first place

    def remove(self):
        """
        starts one of the containers of this application
        """
        print "removing container on {}".format(self.daemon.host_name)
        if self.details is None:
            return 1, "container does not exist"
        elif self.details['State']['Running'] is False:
            result = self.daemon.connection.remove_container(self.config['release_name'])
            return result
        else:
            return 1, "Failed to remove container"


class Application:

    # config = {}
    # container = {}
    # containers = {}
    # results = []
    # daemons = []
    # hipaches = []

    def __init__(self, name, config, settings, cluster="default"):
        self.name = name
        self.config = config
        self.settings = settings
        self.containers = {}
        self.daemons = []
        self.hipaches = []

        ssh_user = settings[cluster].get('ssh_user', None)
        use_ssh = settings[cluster].get('use_ssh', True)
        registry_login = settings[cluster].get('registry_login', None)

        # setup daemons
        for host in self.settings[cluster]['daemons']:
            self.daemons.append(DockerDaemon(host,
                                             registry_login=registry_login,
                                             ssh_user=ssh_user,
                                             ssh=use_ssh))

    def connect_gateways(self, cluster="default"):
        # setup hipaches

        use_ssh = self.settings[cluster]['use_ssh']

        ssh_user = self.settings[cluster].get('ssh_user', None)
        for hipache_config in self.settings['default']['hipaches']:
            hipache_host, hipache_port = hipache_config.split(':')
            self.hipaches.append(Hipache(hipache_host, int(hipache_port), ssh_user=ssh_user, use_ssh=use_ssh))

        release_name = self.config.get('release_name', None)
        if not release_name:
            print "error, release name not set, check your yml file"

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
        """
        status = []
        for key, container in self.containers.items():
            result = container.create()
            status.append(result)

        return status

    def pull_image(self):
        """
        pulls image on all hosts
        """
        status = []
        for key, container in self.containers.items():
            result = container.pull()
            status.append(result)
        return status

    def start_containers(self):
        """
        starts container on all hosts
        """
        status = []
        for key, container in self.containers.items():
            result = container.start()
            status.append(result)
        return status

    def stop_containers(self):
        """
        starts container on all hosts
        """
        status = []
        for key, container in self.containers.items():
            result = container.stop()
            status.append(result)
        return status

    def remove_containers(self):
        """
        starts container on all hosts
        """
        status = []
        for key, container in self.containers.items():
            result = container.remove()
            status.append(result)
        return status

    def get_details(self):
        """
        get the container details
        """
        status = []
        for key, container in self.containers.items():
            container.details = container.daemon.connection.inspect_container(self.config['release_name'])
            status.append(container.details)
        return status

    def get_status(self):
        status = []
        for key, container in self.containers.items():
            print "container {release_name} on host {daemon}, Running={status}" \
                .format(release_name=container.config['release_name'],
                        daemon=container.daemon.host_name,
                        status=container.status)
            status.append(container.status)
        return status

    def get_frontend_uri(self, domain):

        if not domain:
            frontend = "{}.{}".format(self.name, self.settings['default']['base_domain'][0])
        else:
            match = re.match("^[0-9A-Za-z\.\-]*$", domain)
            if not match:
                sys.exit("given domain not in simple format")
            frontend = domain

        return frontend

    def get_backend_uris(self):

        results = []
        backend_port = "{}/tcp".format(self.config['register'])
        for name, container in self.containers.items():
            try:
                port = container.details[u'NetworkSettings'][u'Ports'][backend_port][0][u'HostPort']
            except TypeError as err:
                port = None
                print "Warning! container not running"
                return None
            print port

            # backend_address = container.details['host'].split('//')[1].split(":")[0]
            backend_address = container.daemon.host_name
            backend = "http://{}:{}".format(backend_address, port)

            results.append(backend)
        return results

    def register(self, domain=None, cluster='default'):

        self.connect_gateways()

        backend_uris = self.get_backend_uris()
        frontend = "frontend:{}".format(self.get_frontend_uri(domain))

        for hipache in self.hipaches:

            # check length
            length = hipache.connection.llen(frontend)
            if not length > 0:
                hipache.connection.rpush(frontend, self.name)

            for backend_uri in backend_uris or []:
                # when the container is not running the backend_uri will be None
                if backend_uri:
                    # does it already have this backend registered?
                    stored_backends = hipache.connection.lrange(frontend, 0, -1)
                    if not backend_uri in stored_backends:
                        hipache.connection.rpush(frontend, backend_uri)


            hipache_config = hipache.connection.lrange(frontend, 0, -1)
            print hipache_config

    def unregister(self, domain, hard=False):
        """
        unregisters the container from a specified frontend
        """

        self.connect_gateways()

        backend_uris = self.get_backend_uris()
        frontend = "frontend:{}".format(self.get_frontend_uri(domain))
        results = []

        for hipache in self.hipaches:
            # check length
            length = hipache.connection.llen(frontend)

            print "setting was", hipache.connection.lrange(frontend, 0, -1)

            if not length > 0:
                sys.exit("no backends in redis with this domain")
            elif length == 1:
                print hipache.connection.lrange(frontend, 0, -1)
                sys.exit("domain known, but no backends present")
            else:
                if hard is False:
                    for backend_uri in backend_uris:
                        hipache.connection.lrem(frontend, 0, backend_uri)  # remove all occurrences of this backend
                else:
                    hipache.connection.ltrim(frontend, 0, 0)  # remove all backends from this domain

            stored_backends = hipache.connection.lrange(frontend, 0, -1)
            print "setting now", stored_backends
            results.append(stored_backends)

        return results

    def unregister_all(self, domain):
        self.unregister(domain, hard=True)

    def switch_backends(self, domain):
        self.unregister(domain, hard=True)
        self.register(domain)

    def redis_status(self, domain):
        print "getting status for gateways"
        result = []
        frontend = "frontend:{}".format(self.get_frontend_uri(domain))
        for hipache in self.hipaches:
            result = "hipache {}".format(hipache.connection.lrange(frontend, 0, -1))
            print result
            return result

    def login_registry(self):
        """
        Login to the public registry
        """
        status = []
        for name, container in self.containers.items():
            result = container.daemon.login()
            status.append(result)
        return status

