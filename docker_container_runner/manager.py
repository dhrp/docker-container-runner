import docker
import redis


class DockerDaemon:
    host = ""
    connection = {}

    def __init__(self, host):
        self.host = host
        self.connection = docker.Client(base_url=host, version="1.7", timeout=60)


class Hipache:

    def __init__(self, host, port):
        self.connection = redis.StrictRedis(host=host, port=port, db=0)


class Container:

    host = ""
    port = ""
    container_id = ""


class Application:

    config = {}
    container = {}
    containers = []
    results = []

    def __init__(self, name):
        self.name = name

    def set_configuration(self, configuration):
        self.config = configuration

    # def containers(self):
    #     """
    #     holds the list of created containers
    #     """

    def create(self, daemon):
        """
        creates the container specified in the configuration
        :param daemons: the daemon to connect to
        """

        # TODO: make this something real and usefull
        # see if the container already exists
        try:
            existing_container = daemon.connection.inspect_container('insane_turingss')
        except Exception as ex:
            pass

        container = daemon.connection.create_container(self.config['image'],
                                                   self.config['command'],
                                                   volumes=self.config['vols'],
                                                   ports=self.config['c_ports'],
                                                   environment=self.config['env'],
                                                   detach=True)
        container['daemon'] = daemon
        return container

    def create_all(self, daemons):
        for daemon in daemons:
            container = self.create(daemon)
            self.containers.append(container)

        # self.container = self.containers[0]
        return self.containers

    def start(self, container):
        """
        starts one of the containers of this application
        """
        result = container['daemon'].connection.start(container,
                                         port_bindings=self.config['s_ports'],
                                         binds=self.config['binds'])
        return result

    def start_all(self, containers):
        """
        starts container on all hosts
        """

        for container in containers:
            result = self.start(container)
            self.results.append(result)

        return self.results

    def get_details(self, container):
        """
        get the container details
        """
        container['details'] = container['daemon'].connection.inspect_container(container)
        return container

    def register(self, hipache, frontend, backend_port, container):
        """
        registers the container to a specified frontend
        """

        port = container['details'][u'NetworkSettings'][u'Ports'][backend_port][0][u'HostPort']
        print port

        front = "frontend:{}".format(frontend)
        backend_address = container['daemon'].host.split('//')[1].split(":")[0]

        backend = "http://{}:{}".format(backend_address, port)

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
